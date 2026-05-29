"""Phase 2 smart interview: requirements + architectural flow feedback → blueprint."""

from __future__ import annotations

import json
import logging
import os
import re
import uuid
from typing import Optional

from openai import AzureOpenAI

from config import Settings
from schemas.architecture_spec import (
    ARCHITECTURE_FIELD_ORDER,
    FIELD_GROUPS,
    USER_INTERVIEW_ARCHITECTURE_KEYS,
    USER_INTERVIEW_FIELD_KEYS,
    USER_INTERVIEW_REQUIREMENT_KEYS,
    ArchitectureSpec,
    CatalogHint,
    ChatMessage,
    FieldStatus,
    GraphDraft,
    ClarifyingQuestionItem,
    InterviewQuestion,
    InterviewSession,
)
from services.answer_utils import is_custom_describe_placeholder
from services.catalog_interview_context import (
    build_catalog_hints_for_interview,
    format_catalog_for_interview_prompt,
)
from services.clarifying_questions import (
    clarifying_field_key,
    format_clarifying_summary,
    generate_clarifying_questions,
    is_clarifying_field_key,
    pending_clarifying_question,
)
from services.llm import call_llm, load_prompt, make_client, strip_json_fences
from services.spec_validators import apply_validators

logger = logging.getLogger(__name__)

RECENT_MESSAGE_LIMIT = 6
DETAILED_FLOW_MIN_CHARS = 80
FAST_INTERVIEW_MODE = os.getenv("INTERVIEW_FAST_MODE", "1").strip().lower() in (
    "1",
    "true",
    "yes",
    "on",
)

# Plain-language chip fallbacks when the model returns few options.
_DEFAULT_CHIPS: dict[str, list[str]] = {
    "hitl_behavior": [
        "Person reviews every result",
        "Only when unsure",
        "Fully automatic",
        "Other / describe in chat",
    ],
    "integrations": [
        "Email and documents",
        "CRM or case system",
        "Database or files",
        "Standalone for now",
        "Other / describe in chat",
    ],
    "architectural_flow": [
        "Yes, that sounds right",
        "Close — small changes",
        "No — different steps",
        "Other / describe in chat",
    ],
    "architectural_flow_feedback": [
        "Matches what I want",
        "Mostly right",
        "Needs a different flow",
        "Other / describe in chat",
    ],
    "core_components": [
        "Intake → checks → human review → report",
        "Collect data → analyze → send to dashboard",
        "Mostly automatic with one review step",
        "Other / describe in chat",
    ],
}

_FORBIDDEN_QUESTION_PHRASES = re.compile(
    r"\b(affine|catalog agent|built agent|our agent|agentic|llm|rag|vector|"
    r"orchestrat|deployment|hitl\b|api\b|mcp\b)\b",
    re.I,
)


def _catalog_agent_names(spec: ArchitectureSpec) -> list[str]:
    hints = spec.catalog_hints or []
    return [h.name for h in hints if h.name]


def _sanitize_user_facing_text(text: str, spec: ArchitectureSpec) -> str:
    """Remove internal catalog / vendor references from questions and chips."""
    out = text
    for name in _catalog_agent_names(spec):
        if name:
            out = re.sub(re.escape(name), "", out, flags=re.I)
    out = _FORBIDDEN_QUESTION_PHRASES.sub("", out)
    out = re.sub(r"\s{2,}", " ", out).strip(" ,—-")
    return out or text


def _fallback_question_for_field(
    spec: ArchitectureSpec,
    field_key: str,
) -> tuple[str, list[str]]:
    """Concrete, domain-agnostic fallbacks tied to the user's problem statement."""
    hook = spec.problem_statement.strip()
    if len(hook) > 100:
        hook = hook[:100].rsplit(" ", 1)[0] + "…"

    questions: dict[str, str] = {
        "hitl_behavior": (
            f"For this work ({hook}), who should review results before anything "
            "is finalized — and is that every time or only in some cases?"
        ),
        "integrations": (
            f"For this work ({hook}), where should data come from and where "
            "should results be saved (email, files, CRM, database, or other)?"
        ),
        "architectural_flow": (
            f"For this work ({hook}), what is the order of steps from when "
            "work starts until it is finished?"
        ),
        "core_components": (
            f"For this work ({hook}), what are the main parts you need "
            "(for example intake, checks, review, final output)?"
        ),
    }
    q = questions.get(
        field_key,
        f"For this work ({hook}), what should we know about "
        f"{spec.fields[field_key].label.lower()}?",
    )
    return q, list(_DEFAULT_CHIPS.get(field_key, _DEFAULT_CHIPS["hitl_behavior"]))


def _ensure_chips(field_key: str, chips: list[str]) -> list[str]:
    """Keep chips simple; ensure 'Other / describe in chat' is last."""
    cleaned = [str(c).strip() for c in chips if str(c).strip()]
    other = "Other / describe in chat"
    cleaned = [c for c in cleaned if c.lower() != other.lower()]
    if len(cleaned) < 3:
        cleaned = list(_DEFAULT_CHIPS.get(field_key, _DEFAULT_CHIPS["use_case"]))
        cleaned = [c for c in cleaned if c.lower() != other.lower()]
    if not cleaned:
        cleaned = ["Option A", "Option B", "Option C"]
    return cleaned + [other]


def _format_transcript(messages: list[ChatMessage], limit: int | None = None) -> str:
    """Format messages for prompts; optional tail limit."""
    subset = messages[-limit:] if limit else messages
    if not subset:
        return "(no messages yet)"
    lines = []
    for msg in subset:
        role = "User" if msg.role == "user" else "Assistant"
        suffix = f" [re: {msg.field_key}]" if msg.field_key else ""
        lines.append(f"{role}{suffix}: {msg.content}")
    return "\n".join(lines)


def _user_answered_fields(messages: list[ChatMessage]) -> set[str]:
    """Field keys the user explicitly answered after an assistant question."""
    out: set[str] = set()
    for m in messages:
        if m.role != "user" or not m.field_key:
            continue
        text = m.content.strip()
        if text and not is_custom_describe_placeholder(text):
            out.add(m.field_key)
    return out


def _apply_direct_answer(
    spec: ArchitectureSpec,
    field_key: str,
    answer: str,
) -> None:
    """
    Immediately record the user's answer on the targeted slot.

    Reduces missed fills and avoids re-asking in a separate LLM pass.
    """
    if field_key not in spec.fields:
        return
    text = answer.strip()
    if not text:
        return
    field = spec.fields[field_key]
    field.value = text
    field.status = FieldStatus.KNOWN
    field.source = "user_answer"
    field.confidence = 1.0


def _maybe_auto_fill_flow_feedback(spec: ArchitectureSpec) -> None:
    """Skip redundant flow feedback when the user already gave a detailed flow."""
    flow = spec.fields.get("architectural_flow")
    feedback = spec.fields.get("architectural_flow_feedback")
    if not flow or not feedback or feedback.is_known:
        return
    if (
        flow.is_known
        and flow.source == "user_answer"
        and flow.value
        and len(flow.value) >= DETAILED_FLOW_MIN_CHARS
    ):
        feedback.value = flow.value
        feedback.status = FieldStatus.KNOWN
        feedback.source = flow.source or "user_answer"
        feedback.confidence = flow.confidence or 0.9
        logger.info("Auto-filled architectural_flow_feedback from detailed flow")


def _filter_spec_field_updates(
    updates: dict[str, dict],
    spec: ArchitectureSpec,
    *,
    fields_just_set: set[str],
    messages: list[ChatMessage],
) -> dict[str, dict]:
    """Only allow marking fields known when the user answered; never undo prior answers."""
    answered_ever = _user_answered_fields(messages) | fields_just_set
    filtered: dict[str, dict] = {}
    for key, patch in updates.items():
        p = dict(patch)
        if key in answered_ever:
            p.pop("status", None)
        elif p.get("status") in ("known", FieldStatus.KNOWN) and key not in fields_just_set:
            p["status"] = "pending"
            if "value" in p:
                draft = str(p.pop("value", "")).strip()
                if draft:
                    existing = str(p.get("notes") or "").strip()
                    p["notes"] = f"{existing} | {draft}".strip(" |") if existing else draft
        if p.get("notes"):
            p["notes"] = _sanitize_user_facing_text(str(p["notes"]), spec)
        filtered[key] = p
    return filtered


def _confirm_user_answered_fields(
    spec: ArchitectureSpec,
    messages: list[ChatMessage],
) -> None:
    """Keep every chip/chat answer marked known so we never re-ask the same question."""
    for key in USER_INTERVIEW_FIELD_KEYS:
        for msg in reversed(messages):
            if msg.role != "user" or msg.field_key != key:
                continue
            ans = msg.content.strip()
            if not ans or is_custom_describe_placeholder(ans):
                continue
            _apply_direct_answer(spec, key, ans)
            break
        field = spec.fields.get(key)
        if field and field.notes:
            field.notes = _sanitize_user_facing_text(field.notes, spec)
    spec.recompute_status()


def _enforce_architecture_confirmation_gate(
    spec: ArchitectureSpec,
    messages: list[ChatMessage],
    *,
    fields_just_set: set[str],
) -> None:
    """
    Keep user-facing architecture fields pending until the user answers.

    Inferred architecture slots may stay known from the LLM without a dedicated question.
    """
    confirmed = _user_answered_fields(messages) | fields_just_set
    for key in USER_INTERVIEW_ARCHITECTURE_KEYS:
        if key in fields_just_set:
            continue
        field = spec.fields[key]
        if field.is_known and key not in confirmed:
            if field.value:
                draft = f"Draft (unconfirmed): {field.value}"
                field.notes = (
                    f"{field.notes} | {draft}" if field.notes else draft
                )
                field.value = None
            field.status = FieldStatus.PENDING
            field.source = None
            field.confidence = None
    spec.recompute_status()


def _user_field_complete(
    spec: ArchitectureSpec,
    messages: list[ChatMessage],
    key: str,
) -> bool:
    if key not in spec.fields:
        return True
    if spec.fields[key].is_known:
        return True
    return key in _user_answered_fields(messages)


def _pick_next_field_key(
    spec: ArchitectureSpec,
    messages: list[ChatMessage],
    last_answered_field: Optional[str],
) -> str:
    """
    Ask only user-facing fields (no latency, accuracy, volume, model, deployment).
    """
    del last_answered_field

    for key in USER_INTERVIEW_REQUIREMENT_KEYS:
        if key in spec.fields and not _user_field_complete(spec, messages, key):
            return key

    for key in USER_INTERVIEW_ARCHITECTURE_KEYS:
        if key in spec.fields and not _user_field_complete(spec, messages, key):
            return key

    pending = spec.pending_user_interview_keys()
    if pending:
        return pending[0]
    return None


def _draft_for_field(spec: ArchitectureSpec, field_key: str) -> str:
    field = spec.fields.get(field_key)
    if not field:
        return ""
    parts = []
    if field.value:
        parts.append(field.value)
    if field.notes:
        parts.append(field.notes)
    return " | ".join(parts) if parts else "(none yet — ask the user; do not assume)"


def _format_catalog_hints(hints: list[CatalogHint]) -> str:
    return format_catalog_for_interview_prompt(hints)


def _build_spec_update_user_payload(
    spec: ArchitectureSpec,
    messages: list[ChatMessage],
    *,
    fields_just_set: set[str],
) -> str:
    """Compact user payload for spec_update (summary + recent turns, not full history)."""
    return (
        f"PROBLEM STATEMENT:\n{spec.problem_statement}\n\n"
        f"TRANSCRIPT SUMMARY:\n{spec.transcript_summary or '(none yet)'}\n\n"
        f"RECENT MESSAGES:\n{_format_transcript(messages, RECENT_MESSAGE_LIMIT)}\n\n"
        f"USER-CONFIRMED FIELD KEYS: "
        f"{', '.join(sorted(_user_answered_fields(messages))) or 'none'}\n\n"
        f"FIELDS JUST SET BY USER: {', '.join(sorted(fields_just_set)) or 'none'}\n\n"
        f"AFFINE BUILT AGENTS (spec.json):\n{_format_catalog_hints(spec.catalog_hints)}\n\n"
        f"CURRENT SPEC JSON:\n{spec.model_dump_json(indent=2)}"
    )


def _build_question_user_payload(
    spec: ArchitectureSpec,
    target_field: str,
) -> str:
    """Payload for question generation — catalog is internal notes only."""
    return (
        f"TARGET FIELD (mandatory): {target_field}\n"
        f"WHAT TO ASK ABOUT (plain label): {spec.fields[target_field].label}\n\n"
        f"PROBLEM STATEMENT (use their words in the question):\n"
        f"{spec.problem_statement}\n\n"
        f"WHAT THEY SAID SO FAR (summary):\n"
        f"{spec.transcript_summary or '(none)'}\n\n"
        f"ALREADY ANSWERED (do not repeat these topics):\n"
        f"{json.dumps(spec.compact_known_json(), indent=2)}\n\n"
        f"INTERNAL NOTES (for chip ideas only — never quote in the question):\n"
        f"{_format_catalog_hints(spec.catalog_hints) or '(none)'}"
    )


def _user_interview_answer_count(messages: list[ChatMessage]) -> int:
    """User turns that answered an interview question (not the initial problem only)."""
    return sum(
        1
        for m in messages
        if m.role == "user"
        and m.field_key
        and m.field_key in USER_INTERVIEW_FIELD_KEYS
        and m.content.strip()
        and not is_custom_describe_placeholder(m.content)
    )


def _build_dynamic_question_payload(
    spec: ArchitectureSpec,
    messages: list[ChatMessage],
) -> str:
    """Payload for LLM-driven next question / early completion."""
    pending = spec.pending_user_interview_keys()
    covered = {
        key
        for key in USER_INTERVIEW_FIELD_KEYS
        if key in _user_answered_fields(messages) or spec.fields[key].is_known
    }
    still_open = [k for k in USER_INTERVIEW_FIELD_KEYS if k not in covered]
    return (
        f"PROBLEM STATEMENT:\n{spec.problem_statement}\n\n"
        f"TRANSCRIPT SUMMARY:\n{spec.transcript_summary or '(none)'}\n\n"
        f"USER_ANSWER_COUNT (interview Q&A after problem): "
        f"{_user_interview_answer_count(messages)}\n\n"
        f"RECENT MESSAGES:\n{_format_transcript(messages, RECENT_MESSAGE_LIMIT)}\n\n"
        f"TOPICS ALREADY COVERED:\n"
        f"{json.dumps({k: spec.fields[k].value for k in covered if spec.fields.get(k)}, indent=2)}\n\n"
        f"TOPICS STILL OPEN:\n{', '.join(still_open) or '(none — consider ready=true)'}\n\n"
        f"PENDING USER FIELDS (spec): {', '.join(pending) or 'none'}\n\n"
        f"INTERNAL NOTES (chips only):\n"
        f"{_format_catalog_hints(spec.catalog_hints) or '(none)'}"
    )


def _infer_interview_fields_on_complete(
    spec: ArchitectureSpec,
    messages: list[ChatMessage],
    settings: Settings,
    client: AzureOpenAI,
) -> ArchitectureSpec:
    """Fill remaining spec slots from the full conversation when the interview ends."""
    system = load_prompt("spec_infer_interview_complete.txt")
    user = (
        f"PROBLEM STATEMENT:\n{spec.problem_statement}\n\n"
        f"TRANSCRIPT SUMMARY:\n{spec.transcript_summary or '(none)'}\n\n"
        f"FULL CONVERSATION:\n{_format_transcript(messages)}\n\n"
        f"CURRENT SPEC JSON:\n{spec.model_dump_json(indent=2)}"
    )
    raw = call_llm(client, settings, system, user, json_mode=True, temperature=0.15)
    parsed = json.loads(strip_json_fences(raw))
    updates = parsed.get("field_updates") or {}
    if updates:
        spec.apply_field_updates(updates)
    if parsed.get("transcript_summary"):
        spec.transcript_summary = str(parsed["transcript_summary"]).strip()[:1200]
    _maybe_auto_fill_flow_feedback(spec)
    _confirm_user_answered_fields(spec, messages)
    apply_validators(spec)
    spec.recompute_status()
    return spec


def update_spec(
    spec: ArchitectureSpec,
    messages: list[ChatMessage],
    settings: Settings,
    client: AzureOpenAI | None = None,
    *,
    fields_just_set: Optional[set[str]] = None,
) -> ArchitectureSpec:
    """Merge problem statement and conversation into the spec (step 1 of each turn)."""
    if client is None:
        client = make_client(settings)

    just_set = fields_just_set or set()
    system = load_prompt("spec_update.txt")
    user = _build_spec_update_user_payload(spec, messages, fields_just_set=just_set)

    raw = call_llm(client, settings, system, user, json_mode=True)
    parsed = json.loads(strip_json_fences(raw))
    updates = parsed.get("field_updates") or {}
    if updates:
        spec.apply_field_updates(
            _filter_spec_field_updates(
                updates,
                spec,
                fields_just_set=just_set,
                messages=messages,
            )
        )
    if parsed.get("transcript_summary"):
        spec.transcript_summary = str(parsed["transcript_summary"]).strip()[:1200]

    _maybe_auto_fill_flow_feedback(spec)
    _enforce_architecture_confirmation_gate(spec, messages, fields_just_set=just_set)
    _confirm_user_answered_fields(spec, messages)
    apply_validators(spec)
    spec.recompute_status()
    logger.info(
        "Spec updated: %d/%d known (%d arch pending), status=%s — %s",
        spec.known_count(),
        spec.total_required(),
        len(spec.pending_architecture_keys()),
        spec.status,
        parsed.get("summary", ""),
    )
    return spec


def _question_from_parsed(
    spec: ArchitectureSpec,
    field_key: str,
    parsed: dict,
) -> InterviewQuestion:
    """Build InterviewQuestion from LLM JSON with sanitization and chip defaults."""
    fallback_q, fallback_chips = _fallback_question_for_field(spec, field_key)
    question = _sanitize_user_facing_text(
        (parsed.get("question") or "").strip(),
        spec,
    )
    chips = [
        _sanitize_user_facing_text(str(c).strip(), spec)
        for c in (parsed.get("chips") or [])
        if str(c).strip()
    ]

    if not question or len(question) < 12:
        question = fallback_q
        chips = fallback_chips
    elif _FORBIDDEN_QUESTION_PHRASES.search(question):
        question = fallback_q

    other_chip = "Other / describe in chat"

    def _clean_chip(label: str) -> str:
        s = label.strip()
        if s.lower() == other_chip.lower():
            return other_chip
        return _sanitize_user_facing_text(s, spec) or s

    chips = [_clean_chip(c) for c in chips if str(c).strip()]
    chips = _ensure_chips(field_key, chips)
    chips = [_clean_chip(c) for c in chips]

    return InterviewQuestion(
        field_key=field_key,
        question=question,
        chips=chips,
        why_it_matters=(parsed.get("why_it_matters") or None),
    )


def next_question(
    spec: ArchitectureSpec,
    settings: Settings,
    last_answered_field: Optional[str] = None,
    client: AzureOpenAI | None = None,
    messages: list[ChatMessage] | None = None,
) -> Optional[InterviewQuestion]:
    """Ask the next question when needed, or end when the model has enough context."""
    msgs = messages or []
    if msgs:
        _confirm_user_answered_fields(spec, msgs)
    spec.recompute_status()
    if spec.status == "ready":
        return None

    # Fast mode: avoid per-turn LLM routing; ask deterministic field questions.
    if FAST_INTERVIEW_MODE:
        field_key = _pick_next_field_key(spec, msgs, last_answered_field)
        if not field_key:
            return None
        return _question_from_parsed(spec, field_key, {"question": "", "chips": []})

    if client is None:
        client = make_client(settings)

    system = load_prompt("dynamic_next_question.txt")
    user = _build_dynamic_question_payload(spec, msgs)
    raw = call_llm(client, settings, system, user, json_mode=True, temperature=0.25)
    parsed = json.loads(strip_json_fences(raw))

    if parsed.get("ready") is True:
        if _user_interview_answer_count(msgs) >= 1:
            spec = _infer_interview_fields_on_complete(spec, msgs, settings, client)
            if spec.status == "ready":
                return None
        else:
            logger.info("Model requested ready before any Q&A — asking first question")

    field_key = str(parsed.get("field_key") or "").strip()
    if field_key not in USER_INTERVIEW_FIELD_KEYS:
        field_key = _pick_next_field_key(spec, msgs, last_answered_field)
    if not field_key:
        spec = _infer_interview_fields_on_complete(spec, msgs, settings, client)
        if spec.status == "ready":
            return None
        field_key = _pick_next_field_key(spec, msgs, last_answered_field)
        if not field_key:
            return None

    # If dynamic JSON lacked a usable question, fall back to per-field prompts.
    question_text = (parsed.get("question") or "").strip()
    if not question_text or len(question_text) < 12:
        is_architecture = field_key in FIELD_GROUPS["architecture"]
        field_prompt = (
            "architecture_feedback_question.txt"
            if is_architecture
            else "requirements_question.txt"
        )
        field_raw = call_llm(
            client,
            settings,
            load_prompt(field_prompt),
            _build_question_user_payload(spec, field_key),
            json_mode=True,
        )
        parsed = json.loads(strip_json_fences(field_raw))

    return _question_from_parsed(spec, field_key, parsed)


def synthesize_architecture_blueprint(
    spec: ArchitectureSpec,
    messages: list[ChatMessage],
    settings: Settings,
    client: AzureOpenAI | None = None,
) -> tuple[str, GraphDraft | None]:
    """
    Produce markdown blueprint and structured graph draft for Phase 3.

    Returns:
        (blueprint_markdown, graph_draft or None)
    """
    if client is None:
        client = make_client(settings)

    system = load_prompt("architecture_synthesis.txt")
    user = (
        f"PROBLEM STATEMENT:\n{spec.problem_statement}\n\n"
        f"COMPLETED SPEC JSON:\n{spec.model_dump_json(indent=2)}\n\n"
        f"TRANSCRIPT SUMMARY:\n{spec.transcript_summary}\n\n"
        f"CATALOG HINTS:\n{_format_catalog_hints(spec.catalog_hints)}\n\n"
        f"RECENT CONVERSATION:\n{_format_transcript(messages, RECENT_MESSAGE_LIMIT)}"
    )

    raw = call_llm(client, settings, system, user, temperature=0.2, json_mode=True)
    parsed = json.loads(strip_json_fences(raw))
    markdown = (parsed.get("blueprint_markdown") or "").strip()
    graph: GraphDraft | None = None
    if parsed.get("graph_draft"):
        try:
            from services.graph_sanitizer import sanitize_graph

            graph = sanitize_graph(
                GraphDraft.model_validate(parsed["graph_draft"])
            )
        except Exception as exc:
            logger.warning("graph_draft validation failed: %s", exc)

    if not markdown:
        markdown = raw.strip()

    logger.info(
        "Architecture package synthesized (%d chars markdown, %d nodes)",
        len(markdown),
        len(graph.nodes) if graph else 0,
    )
    return markdown, graph


def _finalize_session(
    session: InterviewSession,
    settings: Settings,
    client: AzureOpenAI,
) -> InterviewSession:
    session.spec.status = "ready"
    session.pending_question = None
    # Fast mode: avoid expensive blueprint synthesis on interview turn completion.
    # Architecture generation remains available in Phase 3 endpoints.
    if not FAST_INTERVIEW_MODE:
        markdown, graph = synthesize_architecture_blueprint(
            session.spec, session.messages, settings, client=client
        )
        session.spec.architecture_blueprint = markdown
        session.spec.graph_draft = graph
    session.messages.append(
        ChatMessage(
            role="assistant",
            content=(
                "Requirements and architectural flow are confirmed. "
                "Ready for Phase 3 architecture generation."
            ),
        )
    )
    return session


def _assistant_message_for_question(question: InterviewQuestion) -> str:
    """Plain chat text — no technical prefixes."""
    if is_clarifying_field_key(question.field_key):
        return question.question
    return question.question


def _clarifying_to_interview_question(
    item: ClarifyingQuestionItem,
) -> InterviewQuestion:
    return InterviewQuestion(
        field_key=clarifying_field_key(item.id),
        question=item.question,
        chips=[],
        why_it_matters=item.why_it_matters or None,
    )


def _begin_main_interview(
    session: InterviewSession,
    settings: Settings,
    client: AzureOpenAI,
) -> InterviewSession:
    """Load catalog hints and start the choice-based interview."""
    if session.clarifying_answers:
        session.spec.transcript_summary = format_clarifying_summary(
            session.clarifying_questions,
            session.clarifying_answers,
        )
    else:
        session.spec.transcript_summary = session.spec.problem_statement[:800]
    enriched_query = (
        f"{session.spec.problem_statement}\n\n{session.spec.transcript_summary}"
    )
    session.spec.catalog_hints = build_catalog_hints_for_interview(
        enriched_query, settings, top_k=8
    )
    # Fast mode skips expensive spec-update LLM pass at start.
    if FAST_INTERVIEW_MODE:
        _confirm_user_answered_fields(session.spec, session.messages)
        apply_validators(session.spec)
        session.spec.recompute_status()
    else:
        session.spec = update_spec(session.spec, session.messages, settings, client=client)

    if session.spec.status == "ready":
        return _finalize_session(session, settings, client)

    question = next_question(
        session.spec,
        settings,
        last_answered_field=None,
        client=client,
        messages=session.messages,
    )
    if question is None:
        if session.spec.status == "ready":
            return _finalize_session(session, settings, client)
        logger.warning(
            "No first question for session %s after start — using fallback field",
            session.id,
        )
        field_key = _pick_next_field_key(session.spec, session.messages, None)
        if not field_key:
            return session
        question = _question_from_parsed(
            session.spec,
            field_key,
            {"question": "", "chips": []},
        )

    session.pending_question = question
    intro = (
        "Thanks — I'll ask a few focused questions about how you want this to work. "
        "Pick the closest option or describe in your own words. "
        "We can stop once I have enough detail.\n\n"
    )

    session.messages.append(
        ChatMessage(
            role="assistant",
            content=f"{intro}{_assistant_message_for_question(question)}",
            field_key=question.field_key,
        )
    )
    return session


def run_interview_turn(
    session: InterviewSession,
    settings: Settings,
    user_answer: str | None = None,
    client: AzureOpenAI | None = None,
) -> InterviewSession:
    if client is None:
        client = make_client(settings)

    fields_just_set: set[str] = set()

    if user_answer is not None:
        answer = user_answer.strip()
        if not answer:
            raise ValueError("Answer cannot be empty")
        if is_custom_describe_placeholder(answer):
            raise ValueError(
                "Please describe your answer in the text box instead of selecting "
                "'Other / describe' alone."
            )
        field_key = (
            session.pending_question.field_key if session.pending_question else None
        )
        session.messages.append(
            ChatMessage(role="user", content=answer, field_key=field_key)
        )
        session.pending_question = None

        if field_key and is_clarifying_field_key(field_key):
            qid = field_key.split(":", 1)[1]
            session.clarifying_answers[qid] = answer
            next_cq = pending_clarifying_question(
                session.clarifying_questions,
                session.clarifying_answers,
            )
            if next_cq:
                q = _clarifying_to_interview_question(next_cq)
                session.pending_question = q
                session.messages.append(
                    ChatMessage(
                        role="assistant",
                        content=_assistant_message_for_question(q),
                        field_key=q.field_key,
                    )
                )
                return session
            return _begin_main_interview(session, settings, client)

        if field_key:
            session.last_answered_field = field_key
            _apply_direct_answer(session.spec, field_key, answer)
            fields_just_set.add(field_key)

    if FAST_INTERVIEW_MODE:
        # Keep this path snappy: trust direct field write, re-validate locally.
        _confirm_user_answered_fields(session.spec, session.messages)
        _maybe_auto_fill_flow_feedback(session.spec)
        _enforce_architecture_confirmation_gate(
            session.spec,
            session.messages,
            fields_just_set=fields_just_set,
        )
        apply_validators(session.spec)
        session.spec.recompute_status()
    else:
        session.spec = update_spec(
            session.spec,
            session.messages,
            settings,
            client=client,
            fields_just_set=fields_just_set,
        )

        refresh_query = (
            f"{session.spec.problem_statement}\n\n{session.spec.transcript_summary}"
        )
        session.spec.catalog_hints = build_catalog_hints_for_interview(
            refresh_query, settings, top_k=8
        )

    if session.spec.status == "ready":
        return _finalize_session(session, settings, client)

    question = next_question(
        session.spec,
        settings,
        last_answered_field=session.last_answered_field,
        client=client,
        messages=session.messages,
    )
    if question is None:
        if session.spec.status == "ready":
            return _finalize_session(session, settings, client)
        logger.warning(
            "Interview ended without ready status for session %s — inferring fields",
            session.id,
        )
        session.spec = _infer_interview_fields_on_complete(
            session.spec,
            session.messages,
            settings,
            client,
        )
        if session.spec.status == "ready":
            return _finalize_session(session, settings, client)
        return session

    session.pending_question = question
    session.messages.append(
        ChatMessage(
            role="assistant",
            content=_assistant_message_for_question(question),
            field_key=question.field_key,
        )
    )
    return session


def start_session(problem_statement: str, settings: Settings) -> InterviewSession:
    statement = problem_statement.strip()
    if not statement:
        raise ValueError("Problem statement is required")

    session = InterviewSession(
        id=str(uuid.uuid4()),
        spec=ArchitectureSpec.empty(statement),
    )
    session.messages.append(
        ChatMessage(role="user", content=statement, field_key=None)
    )

    client = make_client(settings)
    session.clarifying_questions = []
    session.clarifying_answers = {}

    return _begin_main_interview(session, settings, client)
