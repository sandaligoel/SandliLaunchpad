"""Phase 2 smart interview: requirements + architectural flow feedback → blueprint."""

from __future__ import annotations

import json
import logging
import uuid
from typing import Optional

from openai import AzureOpenAI

from config import Settings
from schemas.architecture_spec import (
    ARCHITECTURE_FIELD_ORDER,
    FIELD_GROUPS,
    REQUIREMENTS_FIELD_ORDER,
    ArchitectureSpec,
    ChatMessage,
    FieldStatus,
    InterviewQuestion,
    InterviewSession,
)
from services.llm import call_llm, load_prompt, make_client, strip_json_fences

logger = logging.getLogger(__name__)


def _format_transcript(messages: list[ChatMessage]) -> str:
    if not messages:
        return "(no messages yet)"
    lines = []
    for msg in messages:
        role = "User" if msg.role == "user" else "Assistant"
        suffix = f" [re: {msg.field_key}]" if msg.field_key else ""
        lines.append(f"{role}{suffix}: {msg.content}")
    return "\n".join(lines)


def _user_answered_fields(messages: list[ChatMessage]) -> set[str]:
    """Field keys the user explicitly answered after an assistant question."""
    return {
        m.field_key
        for m in messages
        if m.role == "user" and m.field_key
    }


def _enforce_architecture_confirmation_gate(
    spec: ArchitectureSpec,
    messages: list[ChatMessage],
) -> None:
    """
    Keep architecture fields pending until the user answers a targeted question.

    Prevents skipping flow feedback by auto-marking architecture as known from the problem statement alone.
    """
    confirmed = _user_answered_fields(messages)
    for key in FIELD_GROUPS["architecture"]:
        field = spec.fields[key]
        if field.is_known and key not in confirmed:
            if field.value:
                draft = f"Draft (unconfirmed): {field.value}"
                field.notes = (
                    f"{field.notes} | {draft}" if field.notes else draft
                )
                field.value = None
            field.status = FieldStatus.PENDING
    spec.recompute_status()


def _pick_next_field_key(
    spec: ArchitectureSpec,
    last_answered_field: Optional[str],
) -> str:
    """
    Choose the next field to ask about — alternates architecture feedback with requirements.
    """
    pending = spec.pending_field_keys()
    if not pending:
        return "use_case"

    if "use_case" in pending:
        return "use_case"

    arch_pending = [
        k for k in ARCHITECTURE_FIELD_ORDER if k in spec.pending_architecture_keys()
    ]
    req_pending = [
        k for k in REQUIREMENTS_FIELD_ORDER if k in spec.pending_requirements_keys()
    ]

    if arch_pending and req_pending:
        last_was_arch = (
            last_answered_field in FIELD_GROUPS["architecture"]
            if last_answered_field
            else False
        )
        return req_pending[0] if last_was_arch else arch_pending[0]

    if arch_pending:
        return arch_pending[0]
    return req_pending[0]


def _draft_for_field(spec: ArchitectureSpec, field_key: str) -> str:
    field = spec.fields.get(field_key)
    if not field:
        return ""
    parts = []
    if field.value:
        parts.append(field.value)
    if field.notes:
        parts.append(field.notes)
    return " | ".join(parts) if parts else "(none yet — infer briefly from problem statement)"


def update_spec(
    spec: ArchitectureSpec,
    messages: list[ChatMessage],
    settings: Settings,
    client: AzureOpenAI | None = None,
) -> ArchitectureSpec:
    """Merge problem statement and conversation into the spec (step 1 of each turn)."""
    if client is None:
        client = make_client(settings)

    system = load_prompt("spec_update.txt")
    user = (
        f"PROBLEM STATEMENT:\n{spec.problem_statement}\n\n"
        f"CONVERSATION:\n{_format_transcript(messages)}\n\n"
        f"USER-CONFIRMED FIELD KEYS (architecture known only if listed here): "
        f"{', '.join(sorted(_user_answered_fields(messages))) or 'none'}\n\n"
        f"CURRENT SPEC JSON:\n{spec.model_dump_json(indent=2)}"
    )

    raw = call_llm(client, settings, system, user)
    parsed = json.loads(strip_json_fences(raw))
    updates = parsed.get("field_updates") or {}
    if updates:
        spec.apply_field_updates(updates)
    _enforce_architecture_confirmation_gate(spec, messages)
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


def next_question(
    spec: ArchitectureSpec,
    settings: Settings,
    last_answered_field: Optional[str] = None,
    client: AzureOpenAI | None = None,
) -> Optional[InterviewQuestion]:
    """Pick next field (code) and generate a requirements or architecture feedback question (LLM)."""
    spec.recompute_status()
    if spec.status == "ready":
        return None

    if client is None:
        client = make_client(settings)

    target_field = _pick_next_field_key(spec, last_answered_field)
    is_architecture = target_field in FIELD_GROUPS["architecture"]

    if is_architecture:
        system = load_prompt("architecture_feedback_question.txt")
    else:
        system = load_prompt("requirements_question.txt")

    label = spec.fields[target_field].label
    user = (
        f"TARGET FIELD (mandatory): {target_field}\n"
        f"FIELD LABEL: {label}\n\n"
        f"PROBLEM STATEMENT:\n{spec.problem_statement}\n\n"
        f"DRAFT INFERENCE FOR THIS FIELD:\n{_draft_for_field(spec, target_field)}\n\n"
        f"PENDING ARCHITECTURE: {', '.join(spec.pending_architecture_keys()) or 'none'}\n"
        f"PENDING REQUIREMENTS: {', '.join(spec.pending_requirements_keys()) or 'none'}\n\n"
        f"CURRENT SPEC JSON:\n{spec.model_dump_json(indent=2)}"
    )

    raw = call_llm(client, settings, system, user)
    parsed = json.loads(strip_json_fences(raw))

    field_key = target_field
    question = (parsed.get("question") or "").strip()
    chips = parsed.get("chips") or []

    if not question:
        if field_key == "architectural_flow_feedback":
            question = (
                "Based on your problem statement, what is the correct end-to-end "
                "architectural flow — and what would you change in our understanding?"
            )
        elif field_key == "architectural_flow":
            question = (
                "Based on your description, what is the end-to-end flow from "
                "first trigger to final outcome for this system?"
            )
        else:
            question = f"For {label}, what should we record for your architecture?"

    return InterviewQuestion(
        field_key=field_key,
        question=question,
        chips=[str(c).strip() for c in chips if str(c).strip()],
    )


def synthesize_architecture_blueprint(
    spec: ArchitectureSpec,
    messages: list[ChatMessage],
    settings: Settings,
    client: AzureOpenAI | None = None,
) -> str:
    if client is None:
        client = make_client(settings)

    system = load_prompt("architecture_synthesis.txt")
    user = (
        f"PROBLEM STATEMENT:\n{spec.problem_statement}\n\n"
        f"COMPLETED SPEC JSON:\n{spec.model_dump_json(indent=2)}\n\n"
        f"CONVERSATION:\n{_format_transcript(messages)}"
    )

    blueprint = call_llm(client, settings, system, user, temperature=0.2).strip()
    logger.info("Architecture blueprint synthesized (%d chars)", len(blueprint))
    return blueprint


def _finalize_session(
    session: InterviewSession,
    settings: Settings,
    client: AzureOpenAI,
) -> InterviewSession:
    session.spec.status = "ready"
    session.pending_question = None
    session.spec.architecture_blueprint = synthesize_architecture_blueprint(
        session.spec, session.messages, settings, client=client
    )
    session.messages.append(
        ChatMessage(
            role="assistant",
            content=(
                "Requirements and architectural flow are confirmed. "
                "See the Architecture blueprint in the panel — ready for Phase 3."
            ),
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

    if user_answer is not None:
        answer = user_answer.strip()
        if not answer:
            raise ValueError("Answer cannot be empty")
        field_key = session.pending_question.field_key if session.pending_question else None
        session.messages.append(
            ChatMessage(role="user", content=answer, field_key=field_key)
        )
        if field_key:
            session.last_answered_field = field_key
        session.pending_question = None

    session.spec = update_spec(session.spec, session.messages, settings, client=client)

    if session.spec.status == "ready":
        return _finalize_session(session, settings, client)

    question = next_question(
        session.spec,
        settings,
        last_answered_field=session.last_answered_field,
        client=client,
    )
    if question is None:
        return _finalize_session(session, settings, client)

    session.pending_question = question
    prefix = (
        "Architecture feedback: "
        if question.field_key in FIELD_GROUPS["architecture"]
        else ""
    )
    session.messages.append(
        ChatMessage(
            role="assistant",
            content=f"{prefix}{question.question}",
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
    session.spec = update_spec(session.spec, session.messages, settings, client=client)

    if session.spec.status == "ready":
        return _finalize_session(session, settings, client)

    question = next_question(
        session.spec,
        settings,
        last_answered_field=None,
        client=client,
    )
    if question:
        session.pending_question = question
        prefix = (
            "Architecture feedback: "
            if question.field_key in FIELD_GROUPS["architecture"]
            else ""
        )
        session.messages.append(
            ChatMessage(
                role="assistant",
                content=f"{prefix}{question.question}",
                field_key=question.field_key,
            )
        )
    return session
