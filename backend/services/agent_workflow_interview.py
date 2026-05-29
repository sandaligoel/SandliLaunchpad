"""Spec-first agent workflow interview (cursor-agent-prompt style)."""

from __future__ import annotations

import json
import logging
import re
from typing import Optional

from openai import AzureOpenAI

from config import Settings
from pipeline.spec_loader import CatalogLoadResult
from schemas.agent_record import AgentRecord, slugify
from schemas.agent_workflow import (
    AgentSetupQuestionItem,
    AgentWorkflowState,
    MatchedAgentSummary,
    WorkflowPhase,
)
from schemas.architecture_spec import (
    ChatMessage,
    InterviewQuestion,
    InterviewSession,
)
from services.catalog_interview_context import (
    _agent_by_id,
    _hint_from_agent,
    _keyword_score,
    _load_catalog,
    _load_spec_agents,
    format_catalog_brief_for_interview,
)
from services.agent_input_chips import (
    build_agent_input_chips,
    human_input_label,
)
from services.catalog_interview_context import build_catalog_hints_for_interview
from services.agent_input_chips import (
    catalog_values_for_input,
    interview_uses_fast_chips,
)
from services.catalog_chip_suggestions import contextual_chips_from_conversation
from services.chip_quality import merge_and_gate_chips, pick_suggested_chip
from services.llm import call_llm, load_prompt, make_client, strip_json_fences

logger = logging.getLogger(__name__)

_ALLOWED_PHASE_TRANSITIONS: dict[WorkflowPhase, set[WorkflowPhase]] = {
    "start": {"interview", "completion_check"},
    "interview": {"completion_check", "handover"},
    "completion_check": {"handover", "interview"},
    "handover": set(),
}


def _set_phase(
    state: AgentWorkflowState,
    new_phase: WorkflowPhase,
    *,
    context: str,
) -> bool:
    old_phase = state.current_phase
    if old_phase == new_phase:
        return True
    allowed = _ALLOWED_PHASE_TRANSITIONS.get(old_phase, set())
    if new_phase not in allowed:
        logger.warning(
            "Ignored invalid phase transition: %s -> %s (%s)",
            old_phase,
            new_phase,
            context,
        )
        return False
    state.current_phase = new_phase
    logger.info("Phase transition: %s -> %s (%s)", old_phase, new_phase, context)
    return True

AGENT_INPUT_PREFIX = "agent_input:"
MAX_AGENT_QUESTIONS_SAFETY = 18
MAX_QUESTIONS_PER_AGENT = 3
OTHER_CHIP = "Other / describe in chat"
EXPLICIT_FINISH_KEYWORDS = (
    "ready",
    "finish",
    "complete",
    "generate",
    "done",
    "proceed",
)

# Wired automatically from upstream agents — do not ask the business user.
_SKIP_INPUT_SUBSTRINGS = (
    "extracted json",
    "from entity extraction",
    "source document text",
    "document bytes",
    "candidate entity names",
    "missing_item_explanations",
    "extracted_policy_fields",
    "source_doc",
    "reason string",
)


def _normalize_input_name(name: str) -> str:
    return re.sub(r"\s+", " ", (name or "").lower().strip())


def _topic_aligned_chip(input_name: str) -> str:
    """A direct quick option matching the exact current topic/input."""
    low = _normalize_input_name(input_name)
    if "filename" in low:
        return "Use the uploaded file name as identifier"
    if "project_id" in low or "client_summary" in low:
        return "Use the existing customer or case identifier"
    if "policy json" in low or "ingestion policy" in low:
        return "Use our current policy file"
    if "riskfactorscores" in low or "geography_score" in low:
        return "Use our default section scoring method"
    return f"Configure: {input_name.strip()}"


def _question_fingerprint(q: AgentSetupQuestionItem) -> str:
    return _normalize_input_name(
        f"{q.agent_id}|{q.input_name}|{q.question}"
    )


def _should_skip_input(input_name: str, query: str) -> bool:
    if _input_satisfied_by_query(input_name, query):
        return True
    low = _normalize_input_name(input_name)
    return any(part in low for part in _SKIP_INPUT_SUBSTRINGS)


def _input_priority(input_name: str) -> int:
    low = _normalize_input_name(input_name)
    if any(x in low for x in ("pdf", "docx", "txt", "document", "format", "client", "filename")):
        return 0
    if any(x in low for x in ("policy", "blocking", "missing", "threshold", "score")):
        return 1
    if any(x in low for x in ("search", "mode", "image", "photo")):
        return 2
    return 3


def _cluster_for_input(input_name: str) -> str:
    low = _normalize_input_name(input_name)
    if any(x in low for x in ("policy", "compliance", "override", "blocking", "sanction", "pep")):
        return "Security & Compliance"
    if any(x in low for x in ("score", "threshold", "tier", "riskfactor")):
        return "Risk Scoring Configuration"
    if any(x in low for x in ("project_id", "client", "filename", "source_document_id")):
        return "Identity & Tracking"
    if any(x in low for x in ("image", "photo", "vision", "layout", "planogram")):
        return "Vision Inputs"
    if any(x in low for x in ("search", "query", "method")):
        return "Retrieval & Search"
    return "General Configuration"


def _score_components(input_name: str, chips: list[str]) -> tuple[int, int, int, int]:
    """
    Scores are 0..100. Combined rank uses 40/30/20/10 weighting.
    """
    low = _normalize_input_name(input_name)
    impact = 50
    dependency = 45
    uncertainty = 35
    criticality = 40

    if any(x in low for x in ("policy", "override", "blocking", "sanction", "pep")):
        impact, criticality = 92, 94
        dependency = 78
    elif any(x in low for x in ("riskfactor", "score", "threshold", "tier")):
        impact, criticality = 86, 88
        dependency = 72
    elif any(x in low for x in ("project_id", "client", "identifier")):
        impact, dependency, criticality = 76, 81, 74
    elif any(x in low for x in ("document", "format", "filename", "source_document_id")):
        impact, dependency, criticality = 70, 68, 64
    elif any(x in low for x in ("image", "layout", "planogram")):
        impact, dependency, criticality = 74, 66, 70

    if len(chips) <= 2:
        uncertainty = 76
    elif any("default" in c.lower() for c in chips):
        uncertainty = 62
    else:
        uncertainty = 42

    return impact, dependency, uncertainty, criticality


def _rank_score(impact: int, dependency: int, uncertainty: int, criticality: int) -> float:
    return (
        0.40 * impact
        + 0.30 * dependency
        + 0.20 * uncertainty
        + 0.10 * criticality
    )


def _dedupe_question_queue(
    questions: list[AgentSetupQuestionItem],
) -> list[AgentSetupQuestionItem]:
    out: list[AgentSetupQuestionItem] = []
    seen_keys: set[str] = set()
    seen_semantic: set[tuple[str, str]] = set()
    seen_text: set[str] = set()
    for q in questions:
        if q.field_key in seen_keys:
            continue
        sem = (q.agent_id, _normalize_input_name(q.input_name))
        if sem in seen_semantic:
            continue
        fp = _question_fingerprint(q)
        if fp in seen_text:
            continue
        seen_keys.add(q.field_key)
        seen_semantic.add(sem)
        seen_text.add(fp)
        out.append(q)
    return out


def _cap_per_agent(questions: list[AgentSetupQuestionItem]) -> list[AgentSetupQuestionItem]:
    counts: dict[str, int] = {}
    out: list[AgentSetupQuestionItem] = []
    ranked = sorted(questions, key=lambda q: _input_priority(q.input_name))
    for q in ranked:
        n = counts.get(q.agent_id, 0)
        if n >= MAX_QUESTIONS_PER_AGENT:
            continue
        counts[q.agent_id] = n + 1
        out.append(q)
        if len(out) >= MAX_AGENT_QUESTIONS_SAFETY:
            break
    return out


def _finalize_question_queue(
    questions: list[AgentSetupQuestionItem],
    query: str,
) -> list[AgentSetupQuestionItem]:
    filtered = [
        q
        for q in questions
        if not _should_skip_input(q.input_name, query)
    ]
    return _cap_per_agent(_dedupe_question_queue(filtered))


def _dependency_rank_boost(
    q: AgentSetupQuestionItem,
    state: AgentWorkflowState,
) -> float:
    """Prefer prerequisites on the same agent (e.g. policy before scores)."""
    answered = {k for k, v in state.answers.items() if str(v).strip()}
    boost = 0.0
    low = _normalize_input_name(q.input_name)
    for other in state.questions:
        if other.agent_id != q.agent_id or other.field_key in answered:
            continue
        if other.field_key == q.field_key:
            continue
        other_low = _normalize_input_name(other.input_name)
        if any(x in low for x in ("score", "threshold", "tier", "riskfactor")):
            if any(x in other_low for x in ("policy", "document", "client", "project")):
                boost += 18.0
        if "override" in low and "policy" in other_low:
            boost += 14.0
    return boost


def _pending_questions(state: AgentWorkflowState) -> list[AgentSetupQuestionItem]:
    answered = {k for k, v in state.answers.items() if str(v).strip()}
    pending = [q for q in state.questions if q.field_key not in answered]
    return sorted(
        pending,
        key=lambda q: (
            -(q.rank_score + _dependency_rank_boost(q, state)),
            -q.impact_score,
            -q.dependency_score,
            q.input_name,
        ),
    )


def _compute_required_input_count(
    agents: list[AgentRecord],
    query: str,
) -> int:
    count = 0
    for agent in agents:
        for input_name in agent.inputs:
            if _should_skip_input(input_name, query):
                continue
            count += 1
    return count


def _prior_context_block(session: InterviewSession) -> str:
    parts: list[str] = []
    if session.spec.transcript_summary:
        parts.append(
            "CLARIFYING / PRIOR SUMMARY:\n" + session.spec.transcript_summary.strip()
        )
    if session.clarifying_answers:
        parts.append(
            "CLARIFYING ANSWERS:\n"
            + json.dumps(session.clarifying_answers, indent=2, ensure_ascii=False)
        )
    if session.agent_workflow and session.agent_workflow.answers:
        parts.append(
            "AGENT INPUT ANSWERS:\n"
            + json.dumps(session.agent_workflow.answers, indent=2, ensure_ascii=False)
        )
    return "\n\n".join(parts) if parts else "(none)"


def _polish_question_text(
    question: str,
    agent_name: str,
    input_name: str,
) -> str:
    text = " ".join((question or "").split())
    if not text:
        text = (
            f"How should {agent_name} handle {human_input_label(input_name)} "
            f"in this workflow?"
        )
    if "?" not in text:
        text = text.rstrip(".") + "?"
    if text.count("?") > 1:
        text = text.split("?")[0].strip() + "?"
    label = human_input_label(input_name)
    if len(label) < 48 and label.lower() not in text.lower():
        text = text[:-1] + f" (for {label})?"
    if len(text) > 240:
        text = text[:237].rsplit(" ", 1)[0] + "?"
    return text


def _refresh_metrics(state: AgentWorkflowState) -> None:
    pending = _pending_questions(state)
    total = max(state.required_input_count or len(state.questions), 1)
    answered_count = sum(
        1
        for q in state.questions
        if str(state.answers.get(q.field_key, "")).strip()
    )
    state.coverage_score = round((answered_count / total) * 100, 1)
    state.critical_items = [
        f"{q.agent_name} — {q.input_name}"
        for q in pending
        if q.impact_score > 65
    ][:8]
    # Risk is high when high-impact items remain unanswered.
    state.risk_score = round(
        min(
            10.0,
            (sum(q.impact_score for q in pending) / max(len(pending), 1)) / 10.0,
        ),
        1,
    ) if pending else 0.0


def _explicit_finish_requested(user_answer: str | None) -> bool:
    if not user_answer:
        return False
    low = user_answer.lower()
    return any(k in low for k in EXPLICIT_FINISH_KEYWORDS)


def _completion_gate(
    state: AgentWorkflowState,
    *,
    user_answer: str | None = None,
) -> tuple[bool, str | None]:
    pending = _pending_questions(state)
    high_impact_left = [q for q in pending if q.impact_score > 65]

    if not high_impact_left:
        return True, "no_high_impact_inputs_remaining"
    if state.question_count >= min(state.question_budget, state.hard_cap):
        return True, "question_budget_reached"
    if _explicit_finish_requested(user_answer):
        return True, "user_requested_finish"
    return False, None


def _workflow_is_complete(
    state: AgentWorkflowState,
    *,
    user_answer: str | None = None,
) -> bool:
    done, reason = _completion_gate(state, user_answer=user_answer)
    if done:
        state.completion_reason = reason
        return True
    return len(_pending_questions(state)) == 0


def _record_answer(state: AgentWorkflowState, field_key: str, answer: str) -> None:
    text = answer.strip()
    if not text or not field_key:
        return
    state.answers[field_key] = text
    # Also mark same agent+input duplicates as answered so they never resurface.
    sem: tuple[str, str] | None = None
    for q in state.questions:
        if q.field_key == field_key:
            sem = (q.agent_id, _normalize_input_name(q.input_name))
            break
    if sem:
        for q in state.questions:
            if (q.agent_id, _normalize_input_name(q.input_name)) == sem:
                state.answers.setdefault(q.field_key, text)
    answered_count = len([k for k in state.answers if state.answers[k].strip()])
    state.next_index = answered_count
    state.question_count = max(state.question_count, answered_count)
    _refresh_metrics(state)


def is_agent_input_field_key(field_key: str | None) -> bool:
    return bool(field_key and field_key.startswith(AGENT_INPUT_PREFIX))


def agent_input_field_key(agent_id: str, input_name: str) -> str:
    return f"{AGENT_INPUT_PREFIX}{agent_id}:{slugify(input_name)}"


def _detect_vertical(query: str) -> str | None:
    q = query.lower()
    if any(
        w in q
        for w in (
            "kyc",
            "ubo",
            "onboarding",
            "compliance",
            "sanction",
            "corporate client",
            "jpmc",
            "finance",
        )
    ):
        return "Finance"
    if any(
        w in q
        for w in (
            "shelf",
            "planogram",
            "mars",
            "cpg",
            "retail",
            "store",
            "facings",
            "vto",
            "fashion",
        )
    ):
        return "Retail"
    if "cpg" in q or "consumer packaged" in q:
        return "CPG"
    return None


def _match_agents(query: str, catalog: CatalogLoadResult, *, limit: int = 3) -> list[AgentRecord]:
    vertical = _detect_vertical(query)
    scored: list[tuple[float, AgentRecord]] = []
    for agent in catalog.agents:
        score = _keyword_score(query, agent)
        if vertical and agent.vertical not in (vertical, "Other"):
            score *= 0.35
        if score <= 0.05:
            continue
        scored.append((score, agent))
    scored.sort(key=lambda x: x[0], reverse=True)
    seen: set[str] = set()
    out: list[AgentRecord] = []
    for _, agent in scored:
        if agent.id in seen:
            continue
        seen.add(agent.id)
        out.append(agent)
        if len(out) >= limit:
            break
    return out


def _input_satisfied_by_query(input_name: str, query: str) -> bool:
    """Skip asking when the problem statement already implies this input."""
    low_q = query.lower()
    low_i = input_name.lower()
    if "pdf" in low_i or "docx" in low_i or "document" in low_i:
        if any(w in low_q for w in ("pdf", "upload", "document", "filing", "docx")):
            return True
    if "client_name" in low_i.replace(" ", "_") and "client" in low_q:
        return True
    if "filename" in low_i and ("file" in low_q or "upload" in low_q):
        return True
    return False


def _chips_for_input(agent: AgentRecord, input_name: str) -> list[str]:
    low = input_name.lower()
    notes = (agent.notes or "").lower()
    chips: list[str] = []

    if any(w in low for w in ("pdf", "docx", "txt", "document", "text")):
        chips = ["PDF", "DOCX", "TXT"]
    elif "project_id" in low or "client_summary" in low:
        chips = [
            "Use the customer legal name + onboarding case ID",
            "Use internal CRM account ID + opportunity ID",
            "Use existing KYC profile ID from your database",
        ]
    elif "overrideflags" in low or ("override" in low and "flag" in low):
        chips = [
            "Use strict overrides (sanctions/FATF/PEP force High risk)",
            "Use compliance overrides only for sanctions and blacklist",
            "Use advisory overrides (flag issues, keep computed score)",
        ]
    elif "riskfactorscores" in low or "geography_score" in low:
        chips = [
            "Analyst enters the four section scores manually",
            "Auto-calculate section scores from extracted KYC data",
            "Hybrid: auto-calculate then analyst adjusts before final score",
        ]
    elif "threshold" in low or "score" in low or "tier" in low:
        chips = ["0–33 (Low)", "34–66 (Medium)", "67–100 (High)"]
    elif "policy json" in low or "ingestion policy" in low:
        chips = [
            "Use your current KYC policy JSON file",
            "Start with a standard corporate KYC policy template",
            "Create a stricter policy for high-risk onboarding only",
        ]
    elif "search" in low and ("local" in notes or "global" in notes or "drift" in notes):
        chips = ["local", "global", "drift", "basic"]
    elif "blocking" in low or "is_blocking" in low:
        chips = [
            "Block pipeline and draft follow-up email",
            "Flag and continue with partial score",
            "Escalate to compliance team",
        ]
    elif "boolean" in notes or "true" in low or "false" in low:
        chips = ["Yes — required", "No — not applicable"]
    elif "email" in low or "smtp" in low:
        chips = [
            "Send automatically after validation",
            "Draft only — analyst sends manually",
            "Do not send email for this workflow",
        ]
    elif "image" in low or "photo" in low or "vision" in low:
        chips = [
            "Shelf photo (JPEG/PNG)",
            "Planogram reference image",
            "No image — document only",
        ]
    elif "promotion" in low or "discount" in low:
        chips = ["10% discount", "20% discount", "No promotion"]
    elif "entity" in low and "type" in low:
        chips = ["Corporation", "LLC", "Trust", "SPV"]
    elif "compliance" in low or "placement" in low or "facing" in low:
        chips = [
            "Product placement and position",
            "Facing count vs planogram",
            "Price tag accuracy",
            "Agreement clause adherence",
        ]
    else:
        if agent.inputs and len(agent.inputs) <= 6:
            chips = [inp for inp in agent.inputs if inp != input_name][:3]
        chips = chips or [
            f"Use default from {agent.name}",
            "Configure per case",
        ]

    chips = [c for c in chips if c and c.lower() != OTHER_CHIP.lower()]
    return chips[:4] + [OTHER_CHIP]


def _question_for_input(agent: AgentRecord, input_name: str, query: str) -> str:
    hook = query.strip()
    if len(hook) > 60:
        hook = hook[:60].rsplit(" ", 1)[0]
    templates = {
        "document": f"What format is the document for **{agent.name}**?",
        "pdf": f"What document format should **{agent.name}** accept?",
        "json": f"What JSON payload does **{agent.name}** receive?",
        "policy": f"Which policy or rules should **{agent.name}** apply?",
        "client": f"What client identifier should **{agent.name}** use?",
        "missing": f"When fields are missing, how should **{agent.name}** behave?",
        "image": f"What image input does **{agent.name}** need?",
        "search": f"Which search mode should **{agent.name}** use?",
    }
    low = input_name.lower()
    if "project_id" in low or "client_summary" in low:
        return f"What customer or case identifier should {agent.name} use for this risk assessment?"
    if "overrideflags" in low or ("override" in low and "flag" in low):
        return f"Which override policy should {agent.name} apply when high-risk signals appear?"
    if "riskfactorscores" in low or "geography_score" in low:
        return f"How should {agent.name} get the four section scores before calculating final risk?"
    if "policy json" in low or "ingestion policy" in low:
        return f"Which KYC policy should {agent.name} use to validate required fields?"
    for key, tmpl in templates.items():
        if key in low:
            return tmpl.replace("**", "")
    return f"For {hook}, what should **{agent.name}** use for `{input_name}`?".replace(
        "**", ""
    )


def _build_questions_deterministic(
    agents: list[AgentRecord],
    query: str,
) -> list[AgentSetupQuestionItem]:
    items: list[AgentSetupQuestionItem] = []
    for agent in agents:
        for input_name in agent.inputs:
            if len(items) >= MAX_AGENT_QUESTIONS_SAFETY:
                logger.warning(
                    "Agent workflow question list hit safety cap (%d)",
                    MAX_AGENT_QUESTIONS_SAFETY,
                )
                return items
            if _should_skip_input(input_name, query):
                continue
            field_key = agent_input_field_key(agent.id, input_name)
            base_chips = _chips_for_input(agent, input_name)
            impact, dependency, uncertainty, criticality = _score_components(
                input_name, base_chips
            )
            items.append(
                AgentSetupQuestionItem(
                    field_key=field_key,
                    agent_id=agent.id,
                    agent_name=agent.name,
                    input_name=input_name,
                    question=_question_for_input(agent, input_name, query),
                    chips=base_chips,
                    cluster=_cluster_for_input(input_name),
                    impact_score=impact,
                    dependency_score=dependency,
                    uncertainty_score=uncertainty,
                    business_criticality_score=criticality,
                    rank_score=_rank_score(
                        impact, dependency, uncertainty, criticality
                    ),
                )
            )
    return items


def _parse_llm_workflow(
    raw: str,
    catalog: CatalogLoadResult,
    query: str,
) -> AgentWorkflowState | None:
    try:
        parsed = json.loads(strip_json_fences(raw))
    except json.JSONDecodeError:
        return None
    by_id = {a.id: a for a in catalog.agents}
    by_id.update({slugify(a.name): a for a in catalog.agents})

    matched: list[MatchedAgentSummary] = []
    for row in parsed.get("matched_agents") or []:
        if not isinstance(row, dict):
            continue
        aid = str(row.get("agent_id") or "").strip()
        agent = by_id.get(aid) or by_id.get(slugify(str(row.get("name") or "")))
        if not agent:
            continue
        matched.append(
            MatchedAgentSummary(
                agent_id=agent.id,
                name=agent.name,
                reason=str(row.get("reason") or agent.function_summary[:120]),
            )
        )

    questions: list[AgentSetupQuestionItem] = []
    for row in parsed.get("questions") or []:
        if not isinstance(row, dict) or len(questions) >= MAX_AGENT_QUESTIONS_SAFETY:
            break
        aid = str(row.get("agent_id") or "").strip()
        agent = by_id.get(aid)
        if not agent:
            continue
        input_name = str(row.get("input_name") or "").strip()
        if not input_name:
            continue
        qtext = str(row.get("question") or "").strip()
        raw_chips = [str(c).strip() for c in (row.get("chips") or []) if str(c).strip()]
        if not qtext:
            qtext = _question_for_input(agent, input_name, query)
        det = _chips_for_input(agent, input_name)
        chips = merge_and_gate_chips(
            deterministic=det,
            llm=raw_chips,
            input_name=input_name,
            agent_summary=agent.function_summary or "",
        )
        impact, dependency, uncertainty, criticality = _score_components(
            input_name, chips
        )
        questions.append(
            AgentSetupQuestionItem(
                field_key=agent_input_field_key(agent.id, input_name),
                agent_id=agent.id,
                agent_name=agent.name,
                input_name=input_name,
                question=qtext,
                chips=chips,
                cluster=_cluster_for_input(input_name),
                impact_score=impact,
                dependency_score=dependency,
                uncertainty_score=uncertainty,
                business_criticality_score=criticality,
                rank_score=_rank_score(
                    impact, dependency, uncertainty, criticality
                ),
            )
        )

    return AgentWorkflowState(
        query_understood=str(parsed.get("query_understood") or query[:200]),
        matched_agents=matched,
        questions=_dedupe_question_queue(questions),
        next_index=0,
    )


def _merge_question_queues(
    primary: list[AgentSetupQuestionItem],
    supplemental: list[AgentSetupQuestionItem],
    query: str,
) -> list[AgentSetupQuestionItem]:
    """Keep LLM wording first; add any unknown inputs the model skipped."""
    merged = list(primary)
    seen = {q.field_key for q in primary}
    for q in supplemental:
        if q.field_key in seen:
            continue
        merged.append(q)
        seen.add(q.field_key)
        if len(merged) >= MAX_AGENT_QUESTIONS_SAFETY:
            break
    return _finalize_question_queue(merged, query)


def _sync_answers_from_messages(
    state: AgentWorkflowState,
    messages: list[ChatMessage],
) -> None:
    """Rebuild answers from chat history so we never re-ask after refresh."""
    from services.answer_utils import is_custom_describe_placeholder

    for msg in messages:
        if msg.role != "user" or not msg.field_key:
            continue
        if not is_agent_input_field_key(msg.field_key):
            continue
        text = msg.content.strip()
        if text and not is_custom_describe_placeholder(text):
            _record_answer(state, msg.field_key, text)


def _agents_for_matched(
    matched: list[MatchedAgentSummary],
    catalog: CatalogLoadResult,
) -> list[AgentRecord]:
    by_id = {a.id: a for a in catalog.agents}
    by_id.update({slugify(a.name): a for a in catalog.agents})
    out: list[AgentRecord] = []
    seen: set[str] = set()
    for m in matched:
        agent = by_id.get(m.agent_id)
        if agent and agent.id not in seen:
            seen.add(agent.id)
            out.append(agent)
    return out


def _init_workflow_state(
    session: InterviewSession,
    settings: Settings,
    client: AzureOpenAI,
) -> AgentWorkflowState:
    query = session.spec.problem_statement
    catalog = _load_catalog(settings)
    agents = _match_agents(query, catalog)
    if not agents:
        agents = _load_spec_agents(settings)[:3]

    brief = format_catalog_brief_for_interview(query, settings, top_projects=2)
    prior = _prior_context_block(session)
    answered = json.dumps(
        session.agent_workflow.answers if session.agent_workflow else {},
        indent=2,
        ensure_ascii=False,
    )
    if prior and prior != "(none)":
        answered = f"{prior}\n\n{answered}"
    history = "\n".join(
        f"{m.role}: {m.content[:300]}"
        for m in session.messages[-8:]
    )

    system = (
        load_prompt("agent_workflow_interview.txt")
        .replace("{catalog_brief}", brief)
        .replace("{problem_statement}", query)
        .replace("{history}", history or "(none)")
        .replace("{answered}", answered or "(none)")
    )
    try:
        raw = call_llm(
            client,
            settings,
            system,
            "Return the JSON object for agent matching and setup questions.",
            json_mode=True,
            temperature=0.2,
        )
        state = _parse_llm_workflow(raw, catalog, query)
        if state and (state.matched_agents or state.questions):
            if not state.matched_agents and agents:
                state.matched_agents = [
                    MatchedAgentSummary(
                        agent_id=a.id,
                        name=a.name,
                        reason=(a.function_summary or "")[:140],
                    )
                    for a in agents
                ]
            matched_records = _agents_for_matched(state.matched_agents, catalog) or agents
            full_queue = _build_questions_deterministic(matched_records, query)
            state.questions = _merge_question_queues(
                state.questions, full_queue, query
            )
            state.required_input_count = _compute_required_input_count(
                matched_records, query
            )
            _set_phase(state, "interview", context="_init_workflow_state:llm_success")
            _refresh_metrics(state)
            return state
    except Exception as exc:
        logger.warning("Agent workflow LLM init failed: %s", exc)

    matched = [
        MatchedAgentSummary(
            agent_id=a.id,
            name=a.name,
            reason=(a.function_summary or "")[:140],
        )
        for a in agents
    ]
    state = AgentWorkflowState(
        query_understood=query[:200],
        matched_agents=matched,
        questions=_finalize_question_queue(
            _build_questions_deterministic(agents, query),
            query,
        ),
        next_index=0,
        required_input_count=_compute_required_input_count(agents, query),
    )
    _set_phase(state, "interview", context="_init_workflow_state:fallback")
    _refresh_metrics(state)
    return state


def format_workflow_intro(state: AgentWorkflowState) -> str:
    return ""


def _format_progress_summary(state: AgentWorkflowState) -> str:
    pending = _pending_questions(state)
    return (
        f"Progress: Coverage {state.coverage_score:.1f}% · "
        f"Risk {state.risk_score:.1f}/10 · "
        f"Pending {len(pending)}"
    )


def _format_readiness_report(state: AgentWorkflowState) -> str:
    critical = (
        "\n".join(f"- {c}" for c in state.critical_items)
        if state.critical_items
        else "- None"
    )
    return (
        "Readiness Report:\n"
        f"- Coverage Score: {state.coverage_score:.1f}%\n"
        f"- Risk Score: {state.risk_score:.1f}/10\n"
        f"- Completion Reason: {state.completion_reason or 'n/a'}\n"
        f"- Critical Items:\n{critical}"
    )


def format_workflow_configured(state: AgentWorkflowState, settings: Settings) -> str:
    catalog = _load_catalog(settings)
    by_id = {a.id: a for a in catalog.agents}
    lines = [
        "Workflow configured:",
        "",
        f"Agents: {', '.join(a.name for a in state.matched_agents)}",
        "Inputs:",
    ]
    for q in state.questions:
        val = state.answers.get(q.field_key, "—")
        lines.append(f"  - {q.agent_name} / {q.input_name}: {val}")
    lines.append("")
    for a in state.matched_agents:
        agent = by_id.get(a.agent_id)
        if agent:
            lines.append(f"Tech stack ({a.name}): {', '.join(agent.tech_stack[:6])}")
            lines.append(
                f"Integrations ({a.name}): {', '.join(agent.integrations[:6])}"
            )
    lines.append("")
    lines.append("Ready to scaffold architecture in the workflow builder.")
    return "\n".join(lines)


def _question_item_to_interview(
    q: AgentSetupQuestionItem,
    settings: Settings | None = None,
    session: InterviewSession | None = None,
    client: AzureOpenAI | None = None,
) -> InterviewQuestion:
    agent: AgentRecord | None = None
    if settings:
        for row in _load_spec_agents(settings):
            if row.id == q.agent_id:
                agent = row
                break

    deterministic = (
        _chips_for_input(agent, q.input_name) if agent else list(q.chips)
    )
    direct = _topic_aligned_chip(q.input_name)
    if direct and all(c.lower().strip() != direct.lower() for c in deterministic):
        non_other = [
            c for c in deterministic if c.lower().strip() != OTHER_CHIP.lower()
        ]
        deterministic = [direct, *non_other[:5], OTHER_CHIP]

    query = session.spec.problem_statement if session else ""
    llm_core = [c for c in q.chips if c.lower().strip() != OTHER_CHIP.lower()]

    if agent and settings:
        catalog = _load_catalog(settings)
        catalog_patterns = (
            catalog_values_for_input(catalog, agent, q.input_name)
            if interview_uses_fast_chips()
            else []
        )
        contextual: list[str] = []
        if session and interview_uses_fast_chips():
            contextual = contextual_chips_from_conversation(
                f"agent_input:{q.input_name}",
                session.spec,
                session.messages,
            )

        if interview_uses_fast_chips():
            chips = merge_and_gate_chips(
                deterministic=deterministic,
                catalog=catalog_patterns[:6],
                contextual=contextual,
                llm=llm_core,
                input_name=q.input_name,
                agent_summary=agent.function_summary or "",
            )
            suggested = pick_suggested_chip(
                chips, query=query, rank_hint=q.rank_score
            )
            if deterministic:
                first_det = next(
                    (c for c in deterministic if c != OTHER_CHIP), None
                )
                if first_det and first_det in chips:
                    suggested = first_det
            reason = (
                f"Grounded in catalog input `{q.input_name}` for {agent.name} "
                "(catalog-backed suggestions)."
            )
        else:
            if client is None:
                client = make_client(settings)
            chips, suggested, reason = build_agent_input_chips(
                agent,
                q.input_name,
                query,
                settings,
                deterministic=deterministic,
                spec=session.spec if session else None,
                messages=session.messages if session else None,
                llm_chips=llm_core,
                turn_index=len(session.messages) if session else 0,
                client=client,
                question_text=q.question,
            )
    else:
        chips = merge_and_gate_chips(
            deterministic=deterministic,
            llm=llm_core,
            input_name=q.input_name,
            agent_summary=q.agent_name,
        )
        suggested = pick_suggested_chip(chips, query=query, rank_hint=q.rank_score)
        reason = f"Maps to spec.json input: {q.input_name}."

    if not suggested:
        suggested = pick_suggested_chip(chips, query=query, rank_hint=q.rank_score)

    topic = q.cluster or q.agent_name
    why = (
        f"Configures {human_input_label(q.input_name)} for **{q.agent_name}** "
        f"so the workflow can run end-to-end."
    ).replace("**", "")

    return InterviewQuestion(
        field_key=q.field_key,
        topic_label=topic,
        question=_polish_question_text(q.question, q.agent_name, q.input_name),
        chips=chips,
        why_it_matters=why,
        suggested_chip=suggested,
        catalog_reference=q.agent_name,
        suggestion_reason=reason,
    )


def _append_assistant_turn(
    session: InterviewSession,
    content: str,
    question: InterviewQuestion | None,
) -> None:
    session.messages.append(
        ChatMessage(
            role="assistant",
            content=content,
            field_key=question.field_key if question else None,
        )
    )


def _catalog_hints_for_workflow(
    session: InterviewSession,
    state: AgentWorkflowState,
    settings: Settings,
):
    """Catalog context for the interview — matched agents only when fast mode is on."""
    if interview_uses_fast_chips():
        catalog = _load_catalog(settings)
        by_id = _agent_by_id(catalog.agents)
        hints = []
        for m in state.matched_agents:
            agent = by_id.get(m.agent_id)
            if agent:
                hints.append(_hint_from_agent(agent, 0.9))
        return hints[:8]

    from services.catalog_interview_context import build_catalog_hints_for_interview

    hint_ids = [a.agent_id for a in state.matched_agents]
    return build_catalog_hints_for_interview(
        session.spec.problem_statement,
        settings,
        top_k=8,
        preferred_agent_ids=hint_ids,
    )


def begin_agent_workflow_interview(
    session: InterviewSession,
    settings: Settings,
    client: AzureOpenAI,
) -> InterviewSession:
    session.agent_workflow = _init_workflow_state(session, settings, client)
    state = session.agent_workflow
    state.current_phase = "start"
    _sync_answers_from_messages(state, session.messages)
    _refresh_metrics(state)

    session.spec.catalog_hints = _catalog_hints_for_workflow(session, state, settings)

    pending = _pending_questions(state)
    if not pending:
        from services.interview import _finalize_session

        _set_phase(state, "completion_check", context="begin:no_pending")
        session.spec.transcript_summary = format_workflow_configured(state, settings)
        session.spec.status = "ready"
        session.messages.append(
            ChatMessage(
                role="assistant",
                content=(
                    _format_readiness_report(state)
                    + "\n\n"
                    + session.spec.transcript_summary
                ),
            )
        )
        _set_phase(state, "handover", context="begin:finalize_no_pending")
        return _finalize_session(session, settings, client)

    _set_phase(state, "interview", context="begin:first_question")
    q = pending[0]
    interview_q = _question_item_to_interview(q, settings, session, client)
    session.pending_question = interview_q
    state.current_cluster = q.cluster
    _append_assistant_turn(session, interview_q.question, interview_q)
    return session


def advance_agent_workflow_turn(
    session: InterviewSession,
    settings: Settings,
    user_answer: str | None,
    client: AzureOpenAI,
    *,
    answered_field_key: str | None = None,
) -> InterviewSession:
    if session.agent_workflow is None:
        return begin_agent_workflow_interview(session, settings, client)

    state = session.agent_workflow
    _sync_answers_from_messages(state, session.messages)
    _refresh_metrics(state)

    if user_answer is not None:
        answer = user_answer.strip()
        field_key = answered_field_key or (
            session.pending_question.field_key if session.pending_question else None
        )
        if not field_key:
            logger.warning("Agent workflow answer without field_key — ignored")
        else:
            _record_answer(state, field_key, answer)
        session.pending_question = None

    if _workflow_is_complete(state, user_answer=user_answer):
        _set_phase(state, "completion_check", context="advance:completion_gate")
        session.spec.transcript_summary = format_workflow_configured(state, settings)
        from services.interview import _finalize_session, update_spec

        session.spec = update_spec(
            session.spec,
            session.messages,
            settings,
            client=client,
        )
        session.messages.append(
            ChatMessage(
                role="assistant",
                content=(
                    _format_readiness_report(state)
                    + "\n\n"
                    + format_workflow_configured(state, settings)
                ),
            )
        )
        session.spec.status = "ready"
        _set_phase(state, "handover", context="advance:finalize_after_completion")
        return _finalize_session(session, settings, client)

    pending = _pending_questions(state)
    if not pending:
        session.spec.status = "ready"
        from services.interview import _finalize_session

        _set_phase(state, "handover", context="advance:no_pending")
        return _finalize_session(session, settings, client)

    _set_phase(state, "interview", context="advance:next_question")
    q = pending[0]
    interview_q = _question_item_to_interview(q, settings, session, client)
    session.pending_question = interview_q
    state.current_cluster = q.cluster
    _append_assistant_turn(session, interview_q.question, interview_q)
    return session
