"""Phase 2 smart interview: requirements + architectural flow feedback → blueprint."""

from __future__ import annotations

import json
import logging
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
    USER_INTERVIEW_FIELD_LABELS,
    USER_INTERVIEW_REQUIREMENT_KEYS,
    ArchitectureSpec,
    CatalogHint,
    ChatMessage,
    FieldStatus,
    GraphDraft,
    GraphEdge,
    GraphNode,
    ClarifyingQuestionItem,
    InterviewQuestion,
    InterviewSession,
)
from services.answer_utils import is_custom_describe_placeholder
from services.agent_workflow_interview import (
    advance_agent_workflow_turn,
    begin_agent_workflow_interview,
    is_agent_input_field_key,
)
from services.catalog_chip_suggestions import (
    _FIELD_EASE_SCORE,
    build_chip_query_context,
    catalog_suggestion_context,
    easy_question_for_project,
    merge_catalog_chips,
    pick_suggested_chip,
    recommend_first_interview_field,
    suggestion_reason_for_field,
    suggest_all_field_chips,
    suggest_chips_for_field,
    suggest_clarifying_chips,
)
from services.catalog_interview_context import (
    build_catalog_hints_for_interview,
    format_catalog_brief_for_interview,
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
CATALOG_HINT_REFRESH_USER_TURN_EVERY = 3

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
    "data_flow": [
        "Each step passes results directly to the next",
        "One shared place every step reads and updates",
        "Mix of handoffs and a central case record",
        "Other / describe in chat",
    ],
    "orchestration_model": [
        "Strict order — one step finishes before the next starts",
        "Some steps can run in parallel when data is ready",
        "A person starts each major step manually",
        "Other / describe in chat",
    ],
}

# Internal branding only — allow HITL, API, orchestration, RAG in practitioner-facing text.
_FORBIDDEN_QUESTION_PHRASES = re.compile(
    r"\b(affine analytics|affine launchpad|catalog agent|built agent|our agent|"
    r"agentic launchpad|from our catalog|spec\.json)\b",
    re.I,
)

# One-line scope per topic (prompt + validation). Not a fixed question script.
_TOPIC_FOCUS: dict[str, str] = {
    "hitl_behavior": (
        "hitl_behavior — HITL gates: roles, approval policy (always vs threshold vs exception-only)."
    ),
    "integrations": (
        "integrations — Source/destination systems, APIs, files, and event channels."
    ),
    "architectural_flow": (
        "architectural_flow — End-to-end pipeline sequence, triggers, and branches."
    ),
    "data_flow": (
        "data_flow — Data handoffs vs shared store (case record, lake, operational DB)."
    ),
    "core_components": (
        "core_components — Logical services/modules (ingestion, scoring, HITL queue, reporting)."
    ),
    "orchestration_model": (
        "orchestration_model — Sequential, parallel, event-driven, or manual step triggers."
    ),
}

_OTHER_TOPIC_CUES: dict[str, tuple[str, ...]] = {
    "hitl_behavior": ("review", "approve", "analyst", "human", "sign-off", "sign off"),
    "integrations": ("email", "crm", "database", "sharepoint", "salesforce", "upload"),
    "architectural_flow": ("step order", "first", "then", "sequence", "pipeline", "end to end"),
    "data_flow": ("handoff", "shared record", "passes to", "central store", "hand off"),
    "core_components": ("main parts", "building blocks", "modules", "intake", "dashboard"),
    "orchestration_model": ("parallel", "automatically", "manual trigger", "one by one"),
}


def _catalog_agent_names(spec: ArchitectureSpec) -> list[str]:
    hints = spec.catalog_hints or []
    return [h.name for h in hints if h.name]


def _sanitize_user_facing_text(text: str, spec: ArchitectureSpec) -> str:
    """Strip internal product branding from questions and chips (keep technical terms)."""
    del spec
    out = _FORBIDDEN_QUESTION_PHRASES.sub("", text)
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
            f"For ({hook}), what HITL approval policy applies — mandatory review, "
            "threshold-based, or exception-only?"
        ),
        "integrations": (
            f"For ({hook}), which systems should ingest data and which should "
            "receive outputs (API, files, CRM, warehouse, email)?"
        ),
        "architectural_flow": (
            f"For ({hook}), what is the end-to-end pipeline sequence from trigger "
            "through completion, including key branches?"
        ),
        "core_components": (
            f"For ({hook}), which logical components are required "
            "(e.g. ingestion, rules engine, HITL queue, reporting API)?"
        ),
        "data_flow": (
            f"For ({hook}), should steps hand off payloads directly or read/write "
            "a shared case record or operational datastore?"
        ),
        "orchestration_model": (
            f"For ({hook}), should orchestration be sequential, parallel where "
            "possible, event-driven, or manually triggered per stage?"
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
        cleaned = list(_DEFAULT_CHIPS.get(field_key, _DEFAULT_CHIPS["hitl_behavior"]))
        cleaned = [c for c in cleaned if c.lower() != other.lower()]
    if not cleaned:
        cleaned = ["Option A", "Option B", "Option C"]
    return cleaned + [other]


def _extract_question_options(question: str) -> list[str]:
    """
    Parse inline options from question text so UI can always show clickable chips.

    Example:
    "What invoice sources...: emailed PDFs/scans, ERP-exported, vendor portal, or a mix?"
    """
    text = (question or "").strip()
    if not text:
        return []

    tail = text[:-1] if text.endswith("?") else text
    match = re.search(r"[:\-\u2014]\s*([^?]+)$", tail)
    if not match:
        return []

    option_blob = match.group(1).strip()
    if not option_blob:
        return []

    option_blob = re.split(
        r"\s*[\u2014\-]\s*and\s+",
        option_blob,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0].strip()
    option_blob = re.split(
        r"\s+and\s+(?:do|does|did|should|can|will|would)\b",
        option_blob,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0].strip()
    normalized = re.sub(r"\s+or\s+", ", ", option_blob, flags=re.IGNORECASE)
    parts = [p.strip(" `\"'") for p in normalized.split(",")]
    options = [p for p in parts if 2 <= len(p) <= 40]
    deduped: list[str] = []
    seen: set[str] = set()
    for opt in options:
        key = opt.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(opt)
    return deduped[:4]


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


def _topic_label(field_key: str) -> str:
    return USER_INTERVIEW_FIELD_LABELS.get(
        field_key,
        field_key.replace("_", " ").strip(),
    )


def _open_interview_gaps(
    spec: ArchitectureSpec,
    messages: list[ChatMessage],
) -> list[str]:
    """Interview topics still missing a user answer (not a fixed script queue)."""
    return [
        key
        for key in USER_INTERVIEW_FIELD_KEYS
        if key in spec.fields and not _user_field_complete(spec, messages, key)
    ]


def _gap_context_score(
    key: str,
    spec: ArchitectureSpec,
    messages: list[ChatMessage],
) -> float:
    """Rank which open gap is most useful next — context-based, not fixed order."""
    blob = f"{spec.problem_statement} {spec.transcript_summary or ''}".lower()
    for msg in reversed(messages):
        if msg.role == "user" and msg.content.strip():
            blob = f"{blob} {msg.content.lower()}"
            break
    score = 1.0
    cues = {
        "hitl_behavior": ("review", "approve", "analyst", "manual", "human"),
        "integrations": ("email", "crm", "database", "upload", "system", "file"),
        "architectural_flow": ("step", "order", "process", "workflow", "first", "then"),
        "data_flow": ("handoff", "transfer", "record", "store", "shared"),
        "core_components": ("part", "block", "intake", "module", "dashboard"),
        "orchestration_model": ("parallel", "automatic", "trigger", "batch", "wait"),
    }
    for term in cues.get(key, ()):
        if term in blob:
            score += 1.25
    score += _FIELD_EASE_SCORE.get(key, 1.0) * 0.35
    if key in ("data_flow", "orchestration_model") and not _user_field_complete(
        spec, messages, "architectural_flow"
    ):
        score -= 4.0
    if key in _user_answered_fields(messages):
        score -= 20.0
    return score


def _rank_open_gaps(
    open_gaps: list[str],
    spec: ArchitectureSpec,
    messages: list[ChatMessage],
) -> list[str]:
    return sorted(
        open_gaps,
        key=lambda k: _gap_context_score(k, spec, messages),
        reverse=True,
    )


def _pick_next_field_key(
    spec: ArchitectureSpec,
    messages: list[ChatMessage],
    last_answered_field: Optional[str],
    settings: Settings | None = None,
) -> Optional[str]:
    """Fallback when the model omits or hallucinates field_key — best open gap only."""
    del last_answered_field
    gaps = _open_interview_gaps(spec, messages)
    if not gaps:
        return None
    if _user_interview_answer_count(messages) == 0 and settings is not None:
        return recommend_first_interview_field(spec, settings, gaps)
    ranked = _rank_open_gaps(gaps, spec, messages)
    return ranked[0] if ranked else None


def _resolve_field_key_for_turn(
    parsed_field: str,
    open_gaps: list[str],
    spec: ArchitectureSpec,
    messages: list[ChatMessage],
    fallback_key: Optional[str],
) -> Optional[str]:
    """Accept model field_key only if it is an open gap; never invent topics."""
    key = (parsed_field or "").strip()
    if key in open_gaps:
        return key
    if fallback_key and fallback_key in open_gaps:
        return fallback_key
    ranked = _rank_open_gaps(open_gaps, spec, messages)
    return ranked[0] if ranked else None


def _question_scope_ok(question: str, field_key: str) -> bool:
    """Reject questions that clearly ask about a different open topic."""
    q = question.lower()
    current_cues = _OTHER_TOPIC_CUES.get(field_key, ())
    current_hits = sum(1 for c in current_cues if c in q)
    for other_key, cues in _OTHER_TOPIC_CUES.items():
        if other_key == field_key:
            continue
        other_hits = sum(1 for c in cues if c in q)
        if other_hits >= 2 and other_hits > current_hits:
            return False
    return True


def _topic_focus_for_prompt(open_gaps: list[str]) -> str:
    lines = [_TOPIC_FOCUS[k] for k in open_gaps if k in _TOPIC_FOCUS]
    return "\n".join(lines) if lines else "(none)"


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
    settings: Settings | None = None,
    messages: list[ChatMessage] | None = None,
) -> str:
    """Payload for question generation — catalog is internal notes only."""
    chip_block = ""
    if settings:
        hint_ids = [h.agent_id for h in (spec.catalog_hints or []) if h.agent_id]
        chip_query = _chip_query_context(spec, messages or [], target_field=target_field)
        catalog_chips = suggest_chips_for_field(
            target_field,
            chip_query,
            settings,
            preferred_agent_ids=hint_ids,
            spec=spec,
            messages=messages or [],
        )
        chip_block = (
            f"\nSUGGESTED CHIPS FROM SPEC.JSON (use these; closest first):\n"
            f"{json.dumps(catalog_chips, indent=2)}\n"
        )
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
        f"{chip_block}"
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


def _build_catalog_pattern_prompt(
    spec: ArchitectureSpec,
    messages: list[ChatMessage],
    settings: Settings,
) -> str:
    """Filled catalog_pattern_interview.txt for one LLM turn."""
    still_open = _open_interview_gaps(spec, messages)
    covered = [k for k in USER_INTERVIEW_FIELD_KEYS if k not in still_open]
    transcript_parts: list[str] = []
    if spec.transcript_summary:
        transcript_parts.append(spec.transcript_summary)
    recent = _format_transcript(messages, RECENT_MESSAGE_LIMIT)
    if recent != "(no messages yet)":
        transcript_parts.append(recent)
    transcript = "\n\n".join(transcript_parts) if transcript_parts else "(none)"

    hint_ids = [h.agent_id for h in (spec.catalog_hints or []) if h.agent_id]
    draft_flow: list[str] | None = None
    flow_notes = spec.fields.get("architectural_flow")
    if flow_notes and flow_notes.notes and "Catalog draft flow:" in flow_notes.notes:
        part = flow_notes.notes.split("Catalog draft flow:", 1)[-1].strip()
        draft_flow = [s.strip() for s in part.split("→") if s.strip()]

    all_chips = suggest_all_field_chips(
        spec.problem_statement,
        settings,
        preferred_agent_ids=hint_ids,
        draft_flow=draft_flow,
        spec=spec,
        messages=messages,
        only_fields=still_open,
    )
    chips_for_open = all_chips
    suggested_chips_text = json.dumps(chips_for_open, indent=2)

    latest_message = "(none)"
    for msg in reversed(messages):
        if msg.role == "user" and msg.content.strip():
            latest_message = msg.content.strip()
            break

    return (
        load_prompt("catalog_pattern_interview.txt")
        .replace("{problem_statement}", spec.problem_statement)
        .replace("{history}", transcript)
        .replace("{message}", latest_message)
        .replace(
            "{topics_covered}",
            json.dumps(
                {
                    k: spec.fields[k].value
                    for k in covered
                    if spec.fields.get(k) and spec.fields[k].value
                },
                indent=2,
            ),
        )
        .replace("{open_gaps}", ", ".join(still_open) or "(none)")
        .replace("{topic_focus}", _topic_focus_for_prompt(still_open))
        .replace("{suggested_chips}", suggested_chips_text)
        .replace(
            "{preferred_first_topic}",
            (
                recommend_first_interview_field(spec, settings, still_open)
                if _user_interview_answer_count(messages) == 0 and still_open
                else "(not first turn)"
            ),
        )
    )


def _chip_query_context(
    spec: ArchitectureSpec,
    messages: list[ChatMessage],
    target_field: str | None,
) -> str:
    return build_chip_query_context(spec, messages, target_field)


def _apply_pattern_internal_notes(spec: ArchitectureSpec, parsed: dict) -> None:
    """Log reuse/draft_flow from catalog-pattern JSON; seed flow notes when pending."""
    internal = parsed.get("internal")
    if not isinstance(internal, dict):
        return
    logger.info(
        "Catalog pattern: project=%s agents=%d draft_steps=%d",
        internal.get("reference_project", ""),
        len(internal.get("candidate_agents") or []),
        len(internal.get("draft_flow") or []),
    )
    draft = internal.get("draft_flow")
    flow_field = spec.fields.get("architectural_flow")
    if (
        flow_field
        and not flow_field.is_known
        and isinstance(draft, list)
        and draft
    ):
        steps = " → ".join(str(s).strip() for s in draft[:7] if str(s).strip())
        if steps:
            note = f"Catalog draft flow: {steps}"
            flow_field.notes = (
                f"{flow_field.notes} | {note}" if flow_field.notes else note
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
    settings: Settings | None = None,
    messages: list[ChatMessage] | None = None,
) -> InterviewQuestion:
    """Build InterviewQuestion from LLM JSON with catalog chip merge."""
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
    question = _polish_interview_question(question)
    if _should_use_user_only_question(question) or not _question_scope_ok(
        question, field_key
    ):
        question = _user_only_question_for_field(spec, field_key)

    other_chip = "Other / describe in chat"
    catalog_ref = ""
    draft_flow: list[str] | None = None
    internal = parsed.get("internal")
    if isinstance(internal, dict) and isinstance(internal.get("draft_flow"), list):
        draft_flow = [str(s).strip() for s in internal["draft_flow"] if str(s).strip()]

    chip_query = ""
    hint_ids: list[str] = []
    if settings:
        hint_ids = [h.agent_id for h in (spec.catalog_hints or []) if h.agent_id]
        chip_query = _chip_query_context(spec, messages or [], target_field=field_key)
        catalog_ref, _catalog_why = catalog_suggestion_context(
            chip_query,
            settings,
            preferred_agent_ids=hint_ids,
        )
        suggestion_reason = suggestion_reason_for_field(
            field_key,
            chip_query,
            settings,
            preferred_agent_ids=hint_ids,
        )
    else:
        suggestion_reason = ""

    def _clean_chip(label: str) -> str:
        s = label.strip()
        if s.lower() == other_chip.lower():
            return other_chip
        return _sanitize_user_facing_text(s, spec) or s

    llm_chip_list = [_clean_chip(c) for c in chips if str(c).strip()]
    if settings:
        chips = suggest_chips_for_field(
            field_key,
            chip_query,
            settings,
            preferred_agent_ids=hint_ids,
            draft_flow=draft_flow,
            spec=spec,
            messages=messages or [],
            llm_chips=llm_chip_list,
        )
    elif llm_chip_list:
        chips = _ensure_chips(field_key, llm_chip_list)
    else:
        chips = _ensure_chips(field_key, [])
    chips = [_clean_chip(c) for c in chips]

    suggested = pick_suggested_chip(chips, messages or []) if chips else None
    if suggested and suggested.lower() == other_chip.lower():
        suggested = None

    return InterviewQuestion(
        field_key=field_key,
        topic_label=_topic_label(field_key),
        question=question,
        chips=chips,
        why_it_matters=None,
        suggested_chip=suggested,
        catalog_reference=catalog_ref or None,
        suggestion_reason=suggestion_reason or None,
    )


def _polish_interview_question(question: str, *, max_words: int = 48) -> str:
    """Light polish for practitioner-facing questions — keep technical vocabulary."""
    q = re.sub(r"\s+", " ", question.strip())
    q = re.sub(
        r"\b(closest match|top match|from our catalog|spec\.json|affine launchpad)\b",
        "",
        q,
        flags=re.I,
    )
    q = re.sub(r"\s{2,}", " ", q).strip(" ,.;:-")
    q = re.sub(r"[\u2014:\-]\s*[^?]*\b(?:or|and/or)\b[^?]*\??$", "", q, flags=re.I).strip(
        " ,.;:-"
    )
    words = q.split()
    if len(words) > max_words:
        q = " ".join(words[:max_words]).rstrip(",.;:")
    if not q.endswith("?"):
        q = q.rstrip(".") + "?"
    return q


def _build_catalog_backed_question(
    spec: ArchitectureSpec,
    field_key: str,
    settings: Settings,
    messages: list[ChatMessage],
) -> InterviewQuestion:
    """
    Deterministic question + dynamic catalog suggestions.

    This avoids hard-to-understand LLM wording while keeping chips dynamic from spec.json.
    """
    if _user_interview_answer_count(messages) == 0:
        question = _polish_interview_question(
            easy_question_for_project(spec, field_key, settings)
        )
    else:
        question = _user_only_question_for_field(spec, field_key)
    hint_ids = [h.agent_id for h in (spec.catalog_hints or []) if h.agent_id]
    chip_query = _chip_query_context(spec, messages, target_field=field_key)
    chips = suggest_chips_for_field(
        field_key,
        chip_query,
        settings,
        preferred_agent_ids=hint_ids,
        spec=spec,
        messages=messages,
    )
    catalog_ref, _catalog_why = catalog_suggestion_context(
        chip_query,
        settings,
        preferred_agent_ids=hint_ids,
    )
    suggestion_reason = suggestion_reason_for_field(
        field_key,
        chip_query,
        settings,
        preferred_agent_ids=hint_ids,
    )
    other = "Other / describe in chat"
    suggested = pick_suggested_chip(chips, messages)
    if suggested and suggested.lower() == other.lower():
        suggested = None
    return InterviewQuestion(
        field_key=field_key,
        topic_label=_topic_label(field_key),
        question=question,
        chips=chips,
        why_it_matters=None,
        suggested_chip=suggested,
        catalog_reference=catalog_ref or None,
        suggestion_reason=suggestion_reason or None,
    )


def _user_only_question_for_field(spec: ArchitectureSpec, field_key: str) -> str:
    """Deterministic non-catalog question text for clarity."""
    hook = spec.problem_statement.strip()
    if len(hook) > 70:
        hook = hook[:70].rsplit(" ", 1)[0] + "…"
    prompts = {
        "hitl_behavior": (
            f"For ({hook}), what HITL policy applies — always-on review, "
            "confidence threshold, or exception-only?"
        ),
        "integrations": (
            f"For ({hook}), which source and destination integrations are required "
            "(API, batch files, CRM, warehouse)?"
        ),
        "architectural_flow": (
            f"For ({hook}), define the pipeline sequence from trigger to completion."
        ),
        "core_components": (
            f"For ({hook}), which services/modules are required in the architecture?"
        ),
        "data_flow": (
            f"For ({hook}), use step-to-step handoffs or a shared operational datastore?"
        ),
        "orchestration_model": (
            f"For ({hook}), prefer sequential, parallel, event-driven, or manual triggers?"
        ),
    }
    return _polish_interview_question(
        prompts.get(field_key, f"What configuration is required for {field_key}?")
    )


def _should_use_user_only_question(question: str) -> bool:
    text = (question or "").strip()
    if not text:
        return True
    if len(text.split()) > 52:
        return True
    if _FORBIDDEN_QUESTION_PHRASES.search(text):
        return True
    if re.search(r"\b(spec\.json|from our catalog|catalog agent)\b", text, flags=re.I):
        return True
    return False


def next_question(
    spec: ArchitectureSpec,
    settings: Settings,
    last_answered_field: Optional[str] = None,
    client: AzureOpenAI | None = None,
    messages: list[ChatMessage] | None = None,
) -> Optional[InterviewQuestion]:
    """Hybrid mode: prompt-driven question first, deterministic fallback."""
    msgs = messages or []
    if msgs:
        _confirm_user_answered_fields(spec, msgs)
    spec.recompute_status()
    if spec.status == "ready":
        return None

    if client is None:
        client = make_client(settings)

    open_gaps = _open_interview_gaps(spec, msgs)
    if not open_gaps:
        spec = _infer_interview_fields_on_complete(spec, msgs, settings, client)
        if spec.status == "ready":
            return None
        open_gaps = _open_interview_gaps(spec, msgs)
        if not open_gaps:
            return None

    fallback_key = _pick_next_field_key(spec, msgs, last_answered_field, settings)
    field_key = fallback_key
    is_first_turn = _user_interview_answer_count(msgs) == 0

    if is_first_turn and field_key:
        return _build_catalog_backed_question(spec, field_key, settings, msgs)

    # 1) Prompt-driven question generation (easy wording + dynamic chips guidance).
    try:
        system = _build_catalog_pattern_prompt(spec, msgs, settings)
        raw = call_llm(
            client,
            settings,
            system,
            "Respond with the JSON object for this interview turn only.",
            json_mode=True,
            temperature=0.2,
        )
        if "READY_TO_GENERATE" in raw.upper():
            if _user_interview_answer_count(msgs) >= 1:
                spec = _infer_interview_fields_on_complete(spec, msgs, settings, client)
                if spec.status == "ready":
                    return None

        parsed = json.loads(strip_json_fences(raw))

        # Allow prompt to indicate completion only when no open gaps remain.
        if parsed.get("ready") is True and not open_gaps:
            if _user_interview_answer_count(msgs) >= 1:
                spec = _infer_interview_fields_on_complete(spec, msgs, settings, client)
                if spec.status == "ready":
                    return None
        elif parsed.get("ready") is True and open_gaps:
            logger.info(
                "Ignoring premature ready=true while gaps remain: %s",
                open_gaps,
            )

        parsed_field = str(parsed.get("field_key") or "").strip()
        resolved = _resolve_field_key_for_turn(
            parsed_field,
            open_gaps,
            spec,
            msgs,
            fallback_key,
        )
        if not resolved:
            return _build_catalog_backed_question(
                spec,
                fallback_key or open_gaps[0],
                settings,
                msgs,
            )
        field_key = resolved
        if parsed_field and parsed_field != field_key:
            logger.info(
                "Rejected field_key %r (open gaps: %s) — using %r",
                parsed_field,
                open_gaps,
                field_key,
            )

        prompt_question = _question_from_parsed(
            spec,
            field_key,
            parsed,
            settings,
            msgs,
        )
        if prompt_question.question and len(prompt_question.chips) >= 2:
            return prompt_question
    except Exception as exc:
        logger.warning("Hybrid prompt mode fallback triggered: %s", exc)

    # 2) Deterministic fallback if prompt output is invalid, hard to parse, or failed.
    return _build_catalog_backed_question(spec, field_key, settings, msgs)


def _agents_for_graph_draft(session: InterviewSession) -> list:
    """Merge workflow matches with catalog hints for a richer agent chain."""
    from schemas.agent_workflow import MatchedAgentSummary

    state = session.agent_workflow
    if not state:
        return []

    agents = list(state.matched_agents)
    seen = {a.agent_id for a in agents if a.agent_id}
    for hint in session.spec.catalog_hints or []:
        aid = str(hint.agent_id or "").strip()
        if not aid or aid in seen:
            continue
        agents.append(
            MatchedAgentSummary(
                agent_id=aid,
                name=hint.name or aid,
                reason=(hint.function_summary or "")[:140],
            )
        )
        seen.add(aid)
        if len(agents) >= 6:
            break
    return agents


def _graph_draft_from_workflow(session: InterviewSession) -> GraphDraft | None:
    """Fast sequential graph from agent-workflow matches (no LLM)."""
    chain = _agents_for_graph_draft(session)
    if not chain:
        return None

    from services.graph_sanitizer import normalize_node_id, sanitize_graph

    nodes: list[GraphNode] = [
        GraphNode(id="intake", label="Request intake", type="gateway"),
    ]
    edges: list[GraphEdge] = []
    prev = "intake"

    for i, agent in enumerate(chain):
        nid = normalize_node_id(f"agent-{agent.agent_id or i}")
        nodes.append(
            GraphNode(
                id=nid,
                label=agent.name,
                type="agent",
                agent_id=agent.agent_id or None,
                description=(agent.reason or "")[:200] or None,
            )
        )
        edges.append(GraphEdge(from_id=prev, to_id=nid))
        prev = nid

    nodes.append(GraphNode(id="delivery", label="Deliver result", type="gateway"))
    edges.append(GraphEdge(from_id=prev, to_id="delivery"))
    return sanitize_graph(GraphDraft(nodes=nodes, edges=edges))


def _blueprint_markdown_from_session(
    session: InterviewSession,
    settings: Settings,
) -> str:
    """Deterministic blueprint text for Phase 3 (no LLM)."""
    parts: list[str] = []
    ps = session.spec.problem_statement.strip()
    if ps:
        parts.append(f"## Problem\n{ps}")
    ts = (session.spec.transcript_summary or "").strip()
    if ts:
        parts.append(f"## Summary\n{ts}")
    known = session.spec.compact_known_json()
    if known:
        parts.append(
            f"## Requirements\n```json\n{json.dumps(known, indent=2)}\n```"
        )
    if session.agent_workflow:
        from services.agent_workflow_interview import format_workflow_configured

        parts.append(format_workflow_configured(session.agent_workflow, settings))
    return "\n\n".join(parts) or ps or "Architecture ready for planning."


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
    """
    Mark session ready and produce architecture artifacts.

    Fast path: deterministic blueprint + graph draft, then a single
    ``plan_architecture`` call cached on the session so the builder loads
    immediately. Skips the extra synthesis LLM that previously ran here.
    """
    session.spec.status = "ready"
    session.pending_question = None

    session.spec.architecture_blueprint = _blueprint_markdown_from_session(
        session, settings
    )
    workflow_graph = _graph_draft_from_workflow(session)
    if workflow_graph:
        session.spec.graph_draft = workflow_graph

    if session.architecture_plan is None:
        try:
            from services.architecture_planner import plan_architecture

            session.architecture_plan = plan_architecture(
                session, settings, client=client
            )
            logger.info(
                "Pre-generated architecture plan at finalize for session %s",
                session.id,
            )
        except Exception as exc:
            logger.warning(
                "Pre-plan at finalize failed for session %s (builder will retry): %s",
                session.id,
                exc,
            )

    session.messages.append(
        ChatMessage(
            role="assistant",
            content=(
                "Requirements and architectural flow are confirmed. "
                "Opening the workflow builder with your architecture plan."
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
    spec: ArchitectureSpec,
    settings: Settings,
    messages: list[ChatMessage] | None = None,
) -> InterviewQuestion:
    hint_ids = [h.agent_id for h in (spec.catalog_hints or []) if h.agent_id]
    clarifying_query = _chip_query_context(
        spec,
        messages or [],
        target_field="core_components",
    )
    scope_chips = suggest_clarifying_chips(
        clarifying_query,
        settings,
        preferred_agent_ids=hint_ids,
    )
    inline_chips = _extract_question_options(item.question)
    if len(inline_chips) >= 3:
        # For clarifying questions, clickable options should mirror question options first.
        scope_chips = _ensure_chips("core_components", inline_chips)
    elif inline_chips:
        # If we only extracted 1-2 options, blend with catalog-backed choices.
        scope_chips = merge_catalog_chips("core_components", inline_chips, scope_chips)
    catalog_ref, catalog_why = catalog_suggestion_context(
        clarifying_query,
        settings,
        preferred_agent_ids=hint_ids,
    )
    from services.chip_quality import pick_suggested_chip

    suggested = pick_suggested_chip(scope_chips, query=clarifying_query)
    return InterviewQuestion(
        field_key=clarifying_field_key(item.id),
        topic_label="Scope",
        question=_polish_interview_question(item.question),
        chips=scope_chips,
        why_it_matters=item.why_it_matters or "Narrows agent selection and pipeline ordering.",
        suggested_chip=suggested,
        catalog_reference=catalog_ref or None,
        suggestion_reason=(
            f"Suggested from {catalog_ref}: closest scope match in spec.json."
            if catalog_ref
            else None
        ),
    )


def _begin_main_interview(
    session: InterviewSession,
    settings: Settings,
    client: AzureOpenAI,
) -> InterviewSession:
    """Start spec.json agent workflow interview (match agents → input questions)."""
    if session.clarifying_answers:
        session.spec.transcript_summary = format_clarifying_summary(
            session.clarifying_questions,
            session.clarifying_answers,
        )
    else:
        session.spec.transcript_summary = session.spec.problem_statement[:800]

    # Agent-workflow interviews use catalog-backed questions; skip a full spec LLM pass here.
    return begin_agent_workflow_interview(session, settings, client)


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
            ChatMessage(role="user", content=answer, field_key=field_key
        )
        )

        if session.agent_workflow is not None:
            session.pending_question = None
            return advance_agent_workflow_turn(
                session,
                settings,
                answer,
                client,
                answered_field_key=field_key,
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
                q = _clarifying_to_interview_question(
                    next_cq, session.spec, settings, session.messages
                )
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
            if not is_agent_input_field_key(field_key):
                _apply_direct_answer(session.spec, field_key, answer)
                fields_just_set.add(field_key)

    session.spec = update_spec(
        session.spec,
        session.messages,
        settings,
        client=client,
        fields_just_set=fields_just_set,
    )

    should_refresh_hints = not session.spec.catalog_hints
    if not should_refresh_hints:
        user_turns = sum(1 for msg in session.messages if msg.role == "user")
        should_refresh_hints = (
            user_turns % CATALOG_HINT_REFRESH_USER_TURN_EVERY == 0
        )
    if should_refresh_hints:
        refresh_query = (
            f"{session.spec.problem_statement}\n\n{session.spec.transcript_summary}"
        )
        session.spec.catalog_hints = build_catalog_hints_for_interview(
            refresh_query, settings, top_k=12
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


def _start_clarifying_phase(
    session: InterviewSession,
    settings: Settings,
    client: AzureOpenAI,
) -> InterviewSession:
    """Load spec.json hints and ask catalog-grounded clarifying questions first."""
    statement = session.spec.problem_statement
    session.spec.catalog_hints = build_catalog_hints_for_interview(
        statement, settings, top_k=12
    )
    catalog_block = format_catalog_brief_for_interview(
        statement,
        settings,
        preferred_agent_ids=[h.agent_id for h in session.spec.catalog_hints or []],
    )

    try:
        session.clarifying_questions = generate_clarifying_questions(
            statement,
            settings,
            client=client,
            catalog_context=catalog_block,
        )
    except Exception as exc:
        logger.warning("Clarifying questions skipped: %s", exc)
        session.clarifying_questions = []

    session.clarifying_answers = {}
    next_cq = pending_clarifying_question(
        session.clarifying_questions,
        session.clarifying_answers,
    )
    if not next_cq:
        return _begin_main_interview(session, settings, client)

    question = _clarifying_to_interview_question(
        next_cq, session.spec, settings, session.messages
    )
    session.pending_question = question
    intro = (
        "I’ll ask several technical scoping questions to align your requirements "
        "with the right agents and architecture pattern. Select the closest option "
        "or provide a precise answer in chat. "
    )
    session.messages.append(
        ChatMessage(
            role="assistant",
            content=f"{intro}{_assistant_message_for_question(question)}",
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
    return _start_clarifying_phase(session, settings, client)
