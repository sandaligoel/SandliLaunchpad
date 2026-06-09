"""Suggest interview answer chips from the closest spec.json project and agents."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Optional

from config import Settings
from pipeline.spec_loader import CatalogLoadResult
from schemas.agent_record import AgentRecord, ProjectRecord
from schemas.architecture_spec import USER_INTERVIEW_FIELD_KEYS

if TYPE_CHECKING:
    from schemas.architecture_spec import ArchitectureSpec, ChatMessage
from services.catalog_interview_context import (
    _load_catalog,
    _project_score,
)

OTHER_CHIP = "Other / describe in chat"

_INTEGRATION_LABELS: list[tuple[str, str]] = [
    ("azure blob storage", "Files from cloud document storage"),
    ("azure sql server", "Corporate database records"),
    ("smtp", "Email for notifications and follow-ups"),
    ("azure ai search", "Search over indexed documents"),
    ("azure ai vision", "Photos and image uploads"),
    ("google gemini", "Google document AI"),
    ("google ai studio", "Google document AI"),
    ("roboflow", "Shelf or field image detection"),
    ("azure openai", "AI processing (included in platform)"),
]

_HITL_FROM_NOTES: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(r"analyst reviews?/edits", re.I),
        "Analyst reviews and edits before anything is sent",
    ),
    (
        re.compile(r"human-in-the-loop", re.I),
        "A person reviews key results before they go out",
    ),
    (
        re.compile(r"analyst queue", re.I),
        "Analysts work from a prioritized review queue",
    ),
    (
        re.compile(r"blocks? risk", re.I),
        "Automatic checks first, person only on exceptions",
    ),
]


def _normalize_chip(text: str) -> str:
    """Keep full chip text — options must be complete, readable answers."""
    return re.sub(r"\s+", " ", (text or "").strip())


def _humanize_integration(raw: str) -> str:
    lowered = raw.lower()
    for needle, label in _INTEGRATION_LABELS:
        if needle in lowered:
            return label
    cleaned = re.sub(r"\bazure\b", "", raw, flags=re.I).strip(" -/")
    cleaned = re.sub(r"\s+", " ", cleaned)
    return _normalize_chip(cleaned or raw)


def _score_chip(query: str, chip: str) -> float:
    q = set(re.findall(r"[a-z0-9]{3,}", query.lower()))
    c = set(re.findall(r"[a-z0-9]{3,}", chip.lower()))
    if not q or not c:
        return 0.0
    return len(q & c) / max(len(q), 1)


def _dedupe_chips(chips: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for chip in chips:
        key = chip.lower().strip()
        if not key or key == OTHER_CHIP.lower():
            continue
        if key in seen:
            continue
        seen.add(key)
        out.append(_normalize_chip(chip))
    return [c for c in out if c]


def _rank_chips(
    query: str,
    chips: list[str],
    *,
    field_key: str = "",
    turn_index: int = 0,
) -> list[str]:
    """Stable ranking: relevance score, then alphabetical (same query → same order)."""
    del turn_index
    deduped = _dedupe_chips(chips)
    return sorted(
        deduped,
        key=lambda c: (-_score_chip(query, c), c.lower()),
    )


def _interview_turn_index(messages: list["ChatMessage"]) -> int:
    return sum(
        1
        for m in messages
        if m.role == "user" and m.content.strip()
    )


def _known_interview_values(spec: "ArchitectureSpec") -> dict[str, str]:
    out: dict[str, str] = {}
    for key in USER_INTERVIEW_FIELD_KEYS:
        field = spec.fields.get(key)
        if field and field.value and str(field.value).strip():
            out[key] = str(field.value).strip()
    return out


def _latest_user_answer(
    messages: list["ChatMessage"],
) -> tuple[str | None, str | None]:
    for msg in reversed(messages):
        if msg.role != "user" or not msg.content.strip():
            continue
        return msg.field_key, msg.content.strip()
    return None, None


def contextual_chips_from_conversation(
    field_key: str,
    spec: "ArchitectureSpec",
    messages: list["ChatMessage"],
) -> list[str]:
    """Answer options derived from this session — change as the interview progresses."""
    chips: list[str] = []
    known = _known_interview_values(spec)
    last_field, last_answer = _latest_user_answer(messages)
    problem = spec.problem_statement.strip()
    blob = f"{problem} {spec.transcript_summary or ''}".lower()

    if field_key == "hitl_behavior":
        if any(w in blob for w in ("review", "approve", "analyst", "manual")):
            chips.append("A person reviews before anything is finalized")
        if "exception" in blob or "flag" in blob:
            chips.append("Only flagged or high-risk cases need a person")
        if last_field == "integrations" and last_answer:
            chips.append(
                f"Review outputs before they are sent to {last_answer[:90]}"
            )

    elif field_key == "integrations":
        if "email" in blob:
            chips.append("Email is the main way work arrives and results go out")
        if any(w in blob for w in ("upload", "document", "pdf", "file")):
            chips.append("Uploaded documents are the main input")
        if any(w in blob for w in ("crm", "case", "ticket", "database")):
            chips.append("Pull from and write back to our case or CRM system")
        if last_answer and last_field == "hitl_behavior":
            chips.append(
                f"Systems that support this review rule: {last_answer[:100]}"
            )

    elif field_key == "architectural_flow":
        if known.get("integrations"):
            chips.append(
                f"Flow starting from: {known['integrations'][:120]}"
            )
        if known.get("hitl_behavior"):
            chips.append(
                f"Include a review step where: {known['hitl_behavior'][:100]}"
            )
        if last_answer and last_field != "architectural_flow":
            chips.append(f"Order that fits: {last_answer[:130]}")

    elif field_key == "data_flow":
        if known.get("architectural_flow"):
            flow = known["architectural_flow"]
            chips.append(f"Hand off along this path step by step: {flow[:140]}")
            chips.append(
                "One shared record updated at each step in that path"
            )
        elif last_answer:
            chips.append(f"Move data the way we described: {last_answer[:130]}")

    elif field_key == "core_components":
        if known.get("architectural_flow"):
            steps = re.split(r"\s*→\s*|,\s*|\band\b", known["architectural_flow"])
            parts = [s.strip() for s in steps if len(s.strip()) > 2][:5]
            if len(parts) >= 2:
                chips.append("Main parts: " + " → ".join(parts))
        if known.get("integrations"):
            chips.append(
                f"Include connection to: {known['integrations'][:90]}"
            )

    elif field_key == "orchestration_model":
        if known.get("architectural_flow"):
            chips.append(
                "Run that full path automatically once the first item arrives"
            )
        if known.get("hitl_behavior") and "review" in known["hitl_behavior"].lower():
            chips.append(
                "Pause the chain until a person completes their review step"
            )
        if last_answer:
            chips.append(f"Timing that matches: {last_answer[:120]}")

    if (
        last_answer
        and last_field
        and last_field != field_key
        and len(last_answer) > 12
        and len(last_answer) <= 200
    ):
        chips.append(f"Aligned with what I said earlier: {last_answer}")

    if problem and field_key == "architectural_flow" and len(problem) > 30:
        hook = problem if len(problem) <= 120 else problem[:120].rsplit(" ", 1)[0]
        chips.append(f"Process for this case: {hook}")

    return _dedupe_chips(chips)[:5]


# Higher = preferred first topic for practitioner interviews.
_FIELD_EASE_SCORE: dict[str, float] = {
    "integrations": 3.0,
    "hitl_behavior": 2.6,
    "architectural_flow": 2.3,
    "core_components": 1.4,
    "data_flow": 0.7,
    "orchestration_model": 0.4,
}


def recommend_first_interview_field(
    spec: "ArchitectureSpec",
    settings: Settings,
    open_gaps: list[str] | None = None,
) -> str:
    """
    Easiest interview topic that best matches the problem and closest catalog project.
    """
    gaps = [g for g in (open_gaps or list(USER_INTERVIEW_FIELD_KEYS)) if g in USER_INTERVIEW_FIELD_KEYS]
    if not gaps:
        return "integrations"

    query = spec.problem_statement
    project, agents, fit = _top_project_context(query, settings)
    blob = query.lower()

    scores: dict[str, float] = {g: _FIELD_EASE_SCORE.get(g, 1.0) for g in gaps}

    if any(w in blob for w in ("email", "upload", "file", "document", "pdf", "crm", "database")):
        scores["integrations"] = scores.get("integrations", 0) + 2.5
    if any(w in blob for w in ("review", "approve", "analyst", "manual", "human")):
        scores["hitl_behavior"] = scores.get("hitl_behavior", 0) + 2.2
    if any(w in blob for w in ("step", "process", "workflow", "order", "pipeline")):
        scores["architectural_flow"] = scores.get("architectural_flow", 0) + 2.0

    if project:
        summary = f"{project.solution_summary or ''} {project.outcomes or ''}".lower()
        boost = 0.8 + min(fit, 1.0)
        if any(w in summary for w in ("upload", "email", "extract", "document")):
            scores["integrations"] = scores.get("integrations", 0) + boost
        if any(w in summary for w in ("review", "analyst", "queue", "approve")):
            scores["hitl_behavior"] = scores.get("hitl_behavior", 0) + boost
        if len(_flow_steps_from_agents(agents)) >= 3:
            scores["architectural_flow"] = scores.get("architectural_flow", 0) + boost + 0.3

    return max(scores, key=lambda k: (scores[k], k))


def easy_question_for_project(
    spec: "ArchitectureSpec",
    field_key: str,
    settings: Settings,
) -> str:
    """First interview question grounded in the closest catalog delivery pattern."""
    hook = spec.problem_statement.strip()
    if len(hook) > 72:
        hook = hook[:72].rsplit(" ", 1)[0]

    project, agents, _fit = _top_project_context(spec.problem_statement, settings)
    vertical = (project.vertical or "").strip() if project else ""

    if field_key == "integrations":
        if project and vertical:
            return _normalize_chip(
                f"For ({hook}), which integrations match your {vertical} reference pattern — "
                f"file ingest, API, email, or case management system?"
            )
        return _normalize_chip(
            f"For ({hook}), which source and sink integrations are required (API, files, CRM, warehouse)?"
        )

    if field_key == "hitl_behavior":
        if project and "review" in (project.solution_summary or "").lower():
            return _normalize_chip(
                f"For ({hook}), is a human approval gate required before downstream systems consume outputs?"
            )
        return _normalize_chip(
            f"For ({hook}), what HITL policy applies — always-on review, threshold-based, or exception-only?"
        )

    if field_key == "architectural_flow":
        steps = _flow_steps_from_agents(agents)
        if len(steps) >= 3:
            chain = " → ".join(_normalize_chip(s) for s in steps[:4])
            return _normalize_chip(
                f"For ({hook}), does your target pipeline align with: {chain}?"
            )
        return _normalize_chip(
            f"For ({hook}), what is the end-to-end sequence from trigger through completion?"
        )

    if field_key == "core_components":
        return _normalize_chip(
            f"For ({hook}), which logical components are required (ingestion, scoring, HITL, reporting)?"
        )

    if field_key == "data_flow":
        return _normalize_chip(
            f"For ({hook}), should stages use direct handoffs or a shared operational datastore?"
        )

    if field_key == "orchestration_model":
        return _normalize_chip(
            f"For ({hook}), should orchestration be sequential, parallel, event-driven, or manual?"
        )

    label = field_key.replace("_", " ")
    return _normalize_chip(f"For this work ({hook}), what should we know about {label}?")


def pick_suggested_chip(
    chips: list[str],
    messages: list["ChatMessage"],
) -> str | None:
    """Highlight the chip that best matches the latest user message (not always first)."""
    other = OTHER_CHIP.lower()
    candidates = [c for c in chips if c.lower().strip() != other]
    if not candidates:
        return None
    _, latest = _latest_user_answer(messages)
    if not latest:
        return candidates[0]
    query = latest.lower()
    return max(candidates, key=lambda c: _score_chip(query, c))


def _top_project_context(
    query: str,
    settings: Settings,
    preferred_agent_ids: list[str] | None = None,
) -> tuple[Optional[ProjectRecord], list[AgentRecord], float]:
    catalog = _load_catalog(settings)
    if not catalog.projects:
        return None, catalog.agents[:8], 0.0

    preferred = set(preferred_agent_ids or [])
    agents_by_project: dict[str, list[AgentRecord]] = {}
    for agent in catalog.agents:
        agents_by_project.setdefault(agent.origin_project or "unknown", []).append(agent)

    best: tuple[Optional[ProjectRecord], list[AgentRecord], float] = (None, [], 0.0)
    for project in catalog.projects:
        project_agents = agents_by_project.get(project.name, [])[:10]
        if not project_agents:
            continue
        score = _project_score(query, project, project_agents)
        if preferred:
            score += 0.12 * sum(1 for a in project_agents if a.id in preferred)
        if score > best[2]:
            best = (project, project_agents, score)

    return best


def _flow_steps_from_agents(agents: list[AgentRecord]) -> list[str]:
    steps: list[str] = []
    for agent in agents:
        label = agent.name.replace(" Agent", "").strip()
        if label:
            steps.append(label)
    return steps[:7]


def _flow_steps_from_summary(project: ProjectRecord) -> list[str]:
    summary = project.solution_summary or ""
    if not summary:
        return []
    parts = re.split(r",\s+(?=[A-Z])|\s+and\s+", summary)
    steps: list[str] = []
    for part in parts[:7]:
        part = part.strip()
        if len(part) < 12:
            continue
        steps.append(_normalize_chip(part))
    return steps


def _hitl_chips_from_catalog(
    project: Optional[ProjectRecord],
    agents: list[AgentRecord],
) -> list[str]:
    chips: list[str] = []
    blob = ""
    if project:
        blob += f"{project.solution_summary} {project.outcomes or ''}"
    for agent in agents:
        blob += f" {agent.notes or ''} {agent.function_summary}"

    for pattern, label in _HITL_FROM_NOTES:
        if pattern.search(blob):
            chips.append(label)

    low = blob.lower()
    if "analyst" in low and "review" in low:
        chips.append("Analyst reviews items in a work queue")
    if "upload" in low and "extract" in low:
        chips.append("Fully automatic until a policy check fails")
    if "draft" in low and "email" in low:
        chips.append("Review drafted emails before they go to clients")

    chips.extend(
        [
            "A person checks every output before it is final",
            "Only low-confidence or high-risk cases go to a person",
            "No regular human review — fully automatic",
        ]
    )
    return chips


def _integration_chips_from_catalog(agents: list[AgentRecord]) -> list[str]:
    raw_ints: list[str] = []
    for agent in agents:
        for item in agent.integrations:
            if item and item.strip():
                raw_ints.append(item.strip())

    humanized = [_humanize_integration(x) for x in raw_ints]
    humanized = _dedupe_chips(humanized)

    combos: list[str] = []
    if len(humanized) >= 2:
        combos.append(f"{humanized[0]} and {humanized[1].lower()}")
    if len(humanized) >= 3:
        combos.append(
            f"{humanized[0]}, {humanized[1].lower()}, and {humanized[2].lower()}"
        )

    singles = humanized[:5]
    chips = combos + singles
    chips.extend(
        [
            "Uploaded documents only — no other systems yet",
            "Email plus internal database",
            "Spreadsheets or shared files for now",
        ]
    )
    return chips


def _flow_chips_from_catalog(
    project: Optional[ProjectRecord],
    agents: list[AgentRecord],
    draft_flow: list[str] | None = None,
) -> list[str]:
    steps = list(draft_flow or [])
    agent_steps = _flow_steps_from_agents(agents)
    if len(agent_steps) >= 3:
        steps = agent_steps
    elif len(steps) < 3 and project:
        steps = _flow_steps_from_summary(project)
    if len(steps) < 3:
        steps = agent_steps

    chips: list[str] = []
    if len(steps) >= 3:
        chain = " → ".join(_normalize_chip(s) for s in steps[:5])
        chips.append(_normalize_chip(f"Yes — use this order: {chain}"))
        chips.append("Close — same steps with small changes")
        partial = " → ".join(_normalize_chip(s) for s in steps[:3])
        chips.append(
            _normalize_chip(f"Partly — start like {partial}, then different steps")
        )
    chips.extend(
        [
            "Different order — intake and review happen elsewhere",
            "Fewer steps — skip automated checks",
            "More steps — extra approval before final output",
        ]
    )
    return chips


def _component_chips_from_catalog(agents: list[AgentRecord]) -> list[str]:
    chips: list[str] = []
    for agent in agents[:6]:
        summary = (agent.function_summary or "").strip()
        if not summary:
            continue
        first = summary.split(".")[0].strip()
        if len(first) > 8:
            chips.append(_normalize_chip(first))
        else:
            chips.append(_normalize_chip(agent.name.replace(" Agent", "")))

    if len(chips) >= 2:
        chain = " → ".join(_normalize_chip(c) for c in chips[:4])
        chips.insert(0, _normalize_chip(f"Main blocks in order: {chain}"))

    chips.extend(
        [
            "Intake, automated checks, human review, final report",
            "Collect data, analyze, publish to a dashboard",
            "Mostly automatic with one approval step",
        ]
    )
    return chips


def _data_flow_chips_from_catalog(
    project: Optional[ProjectRecord],
    agents: list[AgentRecord],
) -> list[str]:
    chips = [
        "Each step passes results directly to the next step",
        "One shared case or record that every step updates",
        "Intake writes to storage, later steps read when ready",
        "Results go to email or a dashboard at the end only",
    ]
    blob = ""
    if project:
        blob = f"{project.solution_summary} {project.outcomes or ''}"
    for agent in agents[:4]:
        blob += f" {agent.function_summary or ''}"
    low = blob.lower()
    if "queue" in low or "analyst" in low:
        chips.insert(
            0,
            "Automated steps first, then a person picks up from a work queue",
        )
    if "email" in low:
        chips.insert(1, "Documents in, summary or notification out by email")
    return chips


def _orchestration_chips_from_catalog(
    project: Optional[ProjectRecord],
    agents: list[AgentRecord],
) -> list[str]:
    steps = _flow_steps_from_agents(agents)
    chips = [
        "Strict sequence — step two only after step one completes",
        "Parallel where possible — independent checks run together",
        "Manual trigger — a person starts the next major phase",
        "Fully automatic chain once the first file arrives",
    ]
    if len(steps) >= 4:
        chain = " → ".join(_normalize_chip(s) for s in steps[:4])
        chips.insert(
            0,
            _normalize_chip(f"Automatic pipeline in this order: {chain}"),
        )
    if project and "review" in (project.solution_summary or "").lower():
        chips.insert(
            1,
            "Automatic until review, then paused until a person approves",
        )
    return chips


def suggest_chips_for_field(
    field_key: str,
    query: str,
    settings: Settings,
    *,
    preferred_agent_ids: list[str] | None = None,
    draft_flow: list[str] | None = None,
    limit: int = 5,
    spec: Optional["ArchitectureSpec"] = None,
    messages: Optional[list["ChatMessage"]] = None,
    llm_chips: list[str] | None = None,
) -> list[str]:
    """Chips for one topic: conversation context + catalog patterns (varies each turn)."""
    msgs = messages or []
    turn_index = _interview_turn_index(msgs)
    project, agents, _score = _top_project_context(
        query, settings, preferred_agent_ids=preferred_agent_ids
    )

    if field_key == "hitl_behavior":
        raw = _hitl_chips_from_catalog(project, agents)
    elif field_key == "integrations":
        raw = _integration_chips_from_catalog(agents)
    elif field_key == "architectural_flow":
        raw = _flow_chips_from_catalog(project, agents, draft_flow=draft_flow)
    elif field_key == "core_components":
        raw = _component_chips_from_catalog(agents)
    elif field_key == "data_flow":
        raw = _data_flow_chips_from_catalog(project, agents)
    elif field_key == "orchestration_model":
        raw = _orchestration_chips_from_catalog(project, agents)
    else:
        raw = []

    ranked_catalog = _rank_chips(
        query,
        raw,
        field_key=field_key,
        turn_index=turn_index,
    )[: max(limit - 1, 3)]

    context: list[str] = []
    # Only add session-context chips after the user has answered at least one interview turn.
    if (
        spec is not None
        and messages is not None
        and turn_index >= 1
    ):
        context = contextual_chips_from_conversation(field_key, spec, messages)

    llm = llm_chips if llm_chips is not None else []
    return merge_catalog_chips(
        field_key,
        llm,
        ranked_catalog,
        context_chips=context,
    )


def build_chip_query_context(
    spec: "ArchitectureSpec",
    messages: list["ChatMessage"],
    target_field: str | None,
) -> str:
    """Query text for ranking catalog chips — includes answers so far and field focus."""
    parts: list[str] = [spec.problem_statement]
    if spec.transcript_summary:
        parts.append(spec.transcript_summary)
    for key in USER_INTERVIEW_FIELD_KEYS:
        field = spec.fields.get(key)
        if field and field.value and str(field.value).strip():
            parts.append(f"{key}: {str(field.value).strip()}")
    recent_user = [
        m.content.strip()
        for m in messages[-10:]
        if m.role == "user" and m.content.strip()
    ]
    if recent_user:
        parts.append("Recent answers: " + " | ".join(recent_user[-4:]))
    if target_field:
        field = spec.fields.get(target_field)
        label = field.label if field else target_field
        parts.append(f"Focus: {target_field} ({label})")
        draft_val = field.value if field and field.value else ""
        if field and field.notes:
            draft_val = f"{draft_val} {field.notes}".strip()
        if draft_val:
            parts.append(f"Current draft: {draft_val}")
    return "\n".join(p for p in parts if p).strip()


def suggest_all_field_chips(
    query: str,
    settings: Settings,
    *,
    preferred_agent_ids: list[str] | None = None,
    draft_flow: list[str] | None = None,
    spec: Optional["ArchitectureSpec"] = None,
    messages: Optional[list["ChatMessage"]] = None,
    only_fields: list[str] | None = None,
) -> dict[str, list[str]]:
    """Chips per field — each list built for that topic and current conversation."""
    fields = only_fields or [
        "hitl_behavior",
        "integrations",
        "architectural_flow",
        "data_flow",
        "core_components",
        "orchestration_model",
    ]
    out: dict[str, list[str]] = {}
    for key in fields:
        field_query = query
        if spec is not None and messages is not None:
            field_query = build_chip_query_context(spec, messages, target_field=key)
        out[key] = suggest_chips_for_field(
            key,
            field_query,
            settings,
            preferred_agent_ids=preferred_agent_ids,
            draft_flow=draft_flow if key == "architectural_flow" else None,
            spec=spec,
            messages=messages,
        )
    return out


def merge_catalog_chips(
    field_key: str,
    llm_chips: list[str],
    catalog_chips: list[str],
    *,
    context_chips: list[str] | None = None,
    input_name: str = "",
    agent_summary: str = "",
) -> list[str]:
    """Session-specific + model chips first; catalog templates fill gaps; quality gate."""
    from services.chip_quality import merge_and_gate_chips

    catalog_core = [_normalize_chip(c) for c in catalog_chips if c != OTHER_CHIP]
    llm_core = [_normalize_chip(c) for c in llm_chips if c and c.lower() != OTHER_CHIP.lower()]
    context_core = [
        _normalize_chip(c)
        for c in (context_chips or [])
        if c and c.lower() != OTHER_CHIP.lower()
    ]

    return merge_and_gate_chips(
        deterministic=[],
        catalog=catalog_core,
        contextual=context_core,
        llm=llm_core,
        input_name=input_name or field_key,
        agent_summary=agent_summary,
    )


def suggest_clarifying_chips(
    query: str,
    settings: Settings,
    *,
    preferred_agent_ids: list[str] | None = None,
    limit: int = 4,
) -> list[str]:
    """Scope chips for pre-interview clarifying questions from the top catalog project."""
    project, agents, _score = _top_project_context(
        query, settings, preferred_agent_ids=preferred_agent_ids
    )
    chips: list[str] = []
    if project:
        chips.append(
            _normalize_chip(
                f"Same scope as {project.name.split('(')[0].strip()}"
            )
        )
        if project.vertical and project.vertical != "Other":
            chips.append(
                _normalize_chip(f"Same industry pattern ({project.vertical})")
            )
        first_sentence = (project.business_problem or "").split(".")[0].strip()
        if len(first_sentence) > 20:
            chips.append(_normalize_chip(first_sentence))

    chips.extend(_integration_chips_from_catalog(agents)[:2])
    chips.extend(_hitl_chips_from_catalog(project, agents)[:2])
    chips.extend(
        [
            "Broader scope than similar past projects",
            "Narrower — one team or document type only",
        ]
    )
    return _rank_chips(query, chips)[: max(limit - 1, 3)] + [OTHER_CHIP]


def catalog_suggestion_context(
    query: str,
    settings: Settings,
    preferred_agent_ids: list[str] | None = None,
) -> tuple[str, str]:
    """Reference project label and one-line reason for why_it_matters."""
    project, agents, score = _top_project_context(
        query, settings, preferred_agent_ids=preferred_agent_ids
    )
    if not project:
        return "", ""
    name = project.name
    reason = (
        f"Top match from our catalog ({name}, fit {score:.0%}) — "
        "first option is the closest pattern from spec.json."
    )
    if agents:
        reason += f" Based on {len(agents)} agents from that delivery."
    return name, reason


def suggestion_reason_for_field(
    field_key: str,
    query: str,
    settings: Settings,
    *,
    preferred_agent_ids: list[str] | None = None,
) -> str:
    """Short user-facing reason explaining why the suggestion helps."""
    project, agents, _score = _top_project_context(
        query, settings, preferred_agent_ids=preferred_agent_ids
    )
    if not project:
        return ""
    if field_key == "integrations":
        ints: list[str] = []
        for a in agents[:4]:
            ints.extend(a.integrations[:2])
        ints = [i for i in ints if i]
        if ints:
            return (
                f"Suggested from {project.name}: similar solutions connect to "
                f"{', '.join(ints[:3])}."
            )
    if field_key == "hitl_behavior":
        return (
            f"Suggested from {project.name}: similar workflows keep a human review "
            "step when confidence is low."
        )
    if field_key == "architectural_flow":
        return (
            f"Suggested from {project.name}: this follows the closest delivery flow "
            "seen in spec.json."
        )
    if field_key == "core_components":
        comps = [a.name.replace(" Agent", "") for a in agents[:3]]
        if comps:
            return (
                f"Suggested from {project.name}: common building blocks are "
                f"{', '.join(comps)}."
            )
    return f"Suggested from {project.name} as the closest matching catalog pattern."
