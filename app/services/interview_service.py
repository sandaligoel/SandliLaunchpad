"""Smart interview — fill architecture spec slots, not free-form chat."""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.core.llm_client import AzureLLMClient
from app.core.logging import get_logger
from app.prompts.deep_interview import SLOT_DEEP_GUIDANCE
from app.prompts.interview import (
    ANSWER_PARSE_SYSTEM,
    ANSWER_PARSE_USER,
    FOLLOWUP_QUESTION_SYSTEM,
    FOLLOWUP_QUESTION_USER,
    INTERVIEW_QUESTION_SYSTEM,
    INTERVIEW_QUESTION_USER,
    SLOT_EXTRACT_SYSTEM,
    SLOT_EXTRACT_USER,
)
from app.prompts.interview_context import (
    interview_progress_summary,
    related_slots_json,
    sanitize_interview_text,
    spec_slots_json,
)
from app.schemas.architecture_spec import (
    DEPTH_FOLLOWUP_SLOTS,
    GENERIC_ANSWER_MARKERS,
    SHALLOW_ANSWER_MAX_CHARS,
    SLOT_DEFINITIONS,
    ArchitectureSpec,
    SlotStatus,
    SpecSlot,
)
from app.schemas.interview import (
    InterviewAnswerResponse,
    InterviewOption,
    InterviewStartResponse,
    InterviewStatusResponse,
)
from app.services.interview_options import default_options_for_slot
from app.services.session_store import create_session, get_session, update_session

logger = get_logger(__name__)


def _slot_label(spec: ArchitectureSpec, key: str | None) -> str | None:
    if not key:
        return None
    slot = next((s for s in spec.slots if s.key == key), None)
    return slot.label if slot else key.replace("_", " ").title()


class SlotUpdate(BaseModel):
    key: str
    value: str = ""
    status: SlotStatus = SlotStatus.EMPTY


class SlotExtractionResult(BaseModel):
    slot_updates: list[SlotUpdate] = Field(default_factory=list)


class QuestionOptionResult(BaseModel):
    id: str = Field(description="snake_case id, e.g. shelf_vision_pipeline — not A/B/C/D")
    label: str = Field(
        description="Short visible title, 5–12 plain words — never a single letter; never use 'helper'"
    )
    value: str = Field(
        description="Full answer text stored when selected; plain language; never use 'helper' as a role"
    )


class QuestionResult(BaseModel):
    question: str = Field(
        description="One plain sentence; must reference spec JSON context; never use 'helper' as a role"
    )
    options: list[QuestionOptionResult] = Field(default_factory=list)


class InterviewService:
    def __init__(self) -> None:
        self.llm = AzureLLMClient()

    def _new_spec(self, problem_statement: str) -> ArchitectureSpec:
        slots = [
            SpecSlot(
                key=d["key"],
                label=d["label"],
                description=d.get("description", ""),
                priority=d.get("priority", 50),
                required=d.get("required", True),
            )
            for d in SLOT_DEFINITIONS
        ]
        return ArchitectureSpec(
            session_id=str(uuid.uuid4()),
            problem_statement=problem_statement,
            slots=slots,
        )

    def _deep_guidance(self, slot_key: str, description: str) -> str:
        return SLOT_DEEP_GUIDANCE.get(
            slot_key,
            f"Probe {description} with concrete examples, quantities, owners, and constraints.",
        )

    def _slot_is_shallow(self, slot: SpecSlot) -> bool:
        if not slot.value.strip():
            return False
        lower = slot.value.lower()
        if len(slot.value) < SHALLOW_ANSWER_MAX_CHARS:
            return True
        return any(m in lower for m in GENERIC_ANSWER_MARKERS)

    def _mark_depth_if_sufficient(self, slot: SpecSlot) -> None:
        if slot.key not in DEPTH_FOLLOWUP_SLOTS:
            slot.depth_followup_done = True
            return
        if slot.value.strip() and not self._slot_is_shallow(slot):
            slot.depth_followup_done = True

    def _apply_updates(self, spec: ArchitectureSpec, updates: list[SlotUpdate]) -> list[str]:
        changed: list[str] = []
        by_key = {s.key: s for s in spec.slots}
        for u in updates:
            if u.key not in by_key:
                continue
            slot = by_key[u.key]
            if u.value.strip():
                slot.value = sanitize_interview_text(u.value.strip())
            if u.status != SlotStatus.EMPTY or u.value.strip():
                slot.status = u.status
                slot.source = "interview"
                changed.append(u.key)
        spec.updated_at = datetime.utcnow()
        return changed

    async def _extract_slots_from_text(
        self,
        spec: ArchitectureSpec,
        system: str,
        user_template: str,
        extra: dict | None = None,
    ) -> list[SlotUpdate]:
        extra = extra or {}
        current = [
            {"key": s.key, "label": s.label, "value": s.value, "status": s.status.value}
            for s in spec.slots
        ]
        user = user_template.format(
            problem_statement=spec.problem_statement,
            slot_keys=", ".join(s.key for s in spec.slots),
            current_slots=json.dumps(current, indent=2),
            **extra,
        )
        result = await self.llm.complete_structured(
            system, user, SlotExtractionResult
        )
        return result.slot_updates

    @staticmethod
    def _is_placeholder_label(label: str, option_id: str) -> bool:
        text = label.strip()
        oid = option_id.strip().lower()
        if not text or len(text) <= 2:
            return True
        if re.fullmatch(r"[A-D]", text, re.IGNORECASE):
            return True
        if re.fullmatch(r"option[_\s-]?[a-d0-9]*", text, re.IGNORECASE):
            return True
        if re.fullmatch(r"opt[_\s-]?[a-d0-9]*", text, re.IGNORECASE):
            return True
        if text.lower() == oid and len(text) < 10:
            return True
        return False

    @staticmethod
    def _label_from_value(value: str, *, max_len: int = 110) -> str:
        line = value.strip().replace("\n", " ")
        if not line:
            return ""
        sentence = line.split(". ")[0].split("; ")[0]
        return sentence[:max_len].strip()

    def _raw_options_are_placeholders(self, raw: list[QuestionOptionResult]) -> bool:
        if len(raw) < 2:
            return True
        valid = sum(
            1
            for o in raw[:4]
            if not self._is_placeholder_label((o.label or "").strip(), (o.id or ""))
        )
        return valid < 2

    def _normalize_options(
        self, raw: list[QuestionOptionResult], slot: SpecSlot
    ) -> list[InterviewOption]:
        if self._raw_options_are_placeholders(raw):
            logger.info(
                "interview_options_placeholder_fallback",
                slot=slot.key,
                raw_labels=[(o.label or "")[:20] for o in raw[:4]],
            )
            return default_options_for_slot(slot.key, slot.label)[:4]

        options: list[InterviewOption] = []
        seen: set[str] = set()
        for o in raw[:4]:
            value = (o.value or o.label or "").strip()
            if not value:
                continue
            oid = (o.id or "").strip() or f"opt_{len(options)}"
            if re.fullmatch(r"[A-D]", oid, re.IGNORECASE):
                oid = f"opt_{len(options)}"
            if oid in seen:
                oid = f"{oid}_{len(options)}"
            seen.add(oid)
            label = (o.label or "").strip()[:120]
            if self._is_placeholder_label(label, oid):
                label = self._label_from_value(value)
            if self._is_placeholder_label(label, oid):
                continue
            options.append(InterviewOption(id=oid, label=label, value=value))

        if len(options) < 3:
            for fallback in default_options_for_slot(slot.key, slot.label):
                if fallback.id not in seen:
                    options.append(fallback)
                    seen.add(fallback.id)
                if len(options) >= 4:
                    break
        return options[:4]

    def _set_pending_question(
        self,
        spec: ArchitectureSpec,
        target: SpecSlot | None,
        question: str | None,
        options: list[InterviewOption],
        *,
        is_followup: bool = False,
    ) -> None:
        if target and question:
            spec.pending_question = question
            spec.pending_target_slot = target.key
            spec.pending_options = [o.model_dump() for o in options]
            spec.pending_is_followup = is_followup
        else:
            spec.pending_question = ""
            spec.pending_target_slot = ""
            spec.pending_options = []
            spec.pending_is_followup = False

    def _pending_options(self, spec: ArchitectureSpec) -> list[InterviewOption]:
        return [InterviewOption.model_validate(o) for o in spec.pending_options]

    def _sanitize_question_result(
        self, question: str, options: list[InterviewOption]
    ) -> tuple[str, list[InterviewOption]]:
        q = sanitize_interview_text(question.strip())
        cleaned: list[InterviewOption] = []
        for o in options:
            cleaned.append(
                InterviewOption(
                    id=o.id,
                    label=sanitize_interview_text(o.label),
                    value=sanitize_interview_text(o.value),
                )
            )
        return q, cleaned

    async def _build_question(
        self,
        spec: ArchitectureSpec,
        target: SpecSlot,
        *,
        followup: bool = False,
    ) -> tuple[str, list[InterviewOption]]:
        spec_json = spec_slots_json(spec)
        related_json = related_slots_json(spec, target.key)
        progress = interview_progress_summary(spec)
        common = {
            "problem_statement": spec.problem_statement[:3000],
            "slot_label": target.label,
            "slot_key": target.key,
            "deep_guidance": self._deep_guidance(target.key, target.description),
            "spec_json": spec_json,
            "related_slots_json": related_json,
        }
        if followup:
            user = FOLLOWUP_QUESTION_USER.format(
                current_value=target.value[:2000],
                **common,
            )
            system = FOLLOWUP_QUESTION_SYSTEM
        else:
            user = INTERVIEW_QUESTION_USER.format(
                slot_description=target.description,
                current_value=target.value or "(not set)",
                current_status=target.status.value,
                progress_summary=progress,
                **common,
            )
            system = INTERVIEW_QUESTION_SYSTEM

        try:
            result = await self.llm.complete_structured(
                system, user, QuestionResult, temperature=0.35
            )
            question = sanitize_interview_text(result.question.strip())
            options = self._normalize_options(result.options, target)
            question, options = self._sanitize_question_result(question, options)
        except Exception as exc:
            logger.warning(
                "interview_question_llm_fallback",
                slot=target.key,
                followup=followup,
                error=str(exc),
            )
            if followup:
                question = (
                    f"Can you list each automated step for {target.label}, in order?"
                )
            else:
                question = self._fallback_question_for_slot(
                    spec, target, related_json
                )
            options = default_options_for_slot(target.key, target.label)

        if not question:
            question = self._fallback_question_for_slot(spec, target, related_json)
        if not options:
            options = default_options_for_slot(target.key, target.label)

        question, options = self._sanitize_question_result(question, options)
        self._set_pending_question(spec, target, question, options, is_followup=followup)
        return question, options

    def _fallback_question_for_slot(
        self, spec: ArchitectureSpec, target: SpecSlot, related_json: str
    ) -> str:
        """Plain-language fallback grounded in spec JSON when the LLM fails."""
        try:
            related = json.loads(related_json)
        except json.JSONDecodeError:
            related = []
        if related:
            labels = [r.get("label", r.get("key", "")) for r in related if r]
            context = labels[0] if len(labels) == 1 else ", ".join(labels[:2])
            return f"Based on what you shared about {context}, how should we handle {target.label.lower()}?"
        return f"What should we record for {target.label.lower()}?"

    async def _maybe_followup(
        self, spec: ArchitectureSpec, slot_key: str
    ) -> tuple[str, list[InterviewOption], str] | None:
        """Return (question, options, slot_key) if this slot needs a depth follow-up."""
        if not slot_key:
            return None
        by_key = {s.key: s for s in spec.slots}
        slot = by_key.get(slot_key)
        if not slot or slot.key not in DEPTH_FOLLOWUP_SLOTS or slot.depth_followup_done:
            return None
        if not self._slot_is_shallow(slot):
            slot.depth_followup_done = True
            return None
        question, options = await self._build_question(spec, slot, followup=True)
        return question, options, slot.key

    async def start(self, problem_statement: str) -> InterviewStartResponse:
        spec = self._new_spec(problem_statement)
        updates = await self._extract_slots_from_text(
            spec, SLOT_EXTRACT_SYSTEM, SLOT_EXTRACT_USER
        )
        self._apply_updates(spec, updates)
        for s in spec.slots:
            if s.key not in DEPTH_FOLLOWUP_SLOTS:
                s.depth_followup_done = True
            elif s.status == SlotStatus.CONFIRMED:
                self._mark_depth_if_sufficient(s)
        if spec.is_complete():
            spec.ready_for_plan = True
        sid = create_session(spec)

        target = spec.next_slot_to_ask()
        question = None
        options: list[InterviewOption] = []
        is_followup = False
        if target and not spec.is_complete():
            question, options = await self._build_question(spec, target)
            is_followup = spec.pending_is_followup
            update_session(spec)

        logger.info(
            "interview_started",
            session_id=sid,
            completion=spec.completion_pct(),
            slot_count=len(spec.slots),
        )
        return InterviewStartResponse(
            session_id=sid,
            spec=spec,
            is_complete=spec.is_complete(),
            completion_pct=spec.completion_pct(),
            question=question,
            options=options,
            target_slot=target.key if target else None,
            target_slot_label=_slot_label(spec, target.key if target else None),
            is_followup=is_followup,
            message=(
                "We'll ask a few simple questions to shape your workflow."
                if question
                else "We already captured a lot from your description."
            ),
        )

    async def answer(
        self,
        session_id: str,
        answer: str,
        force_complete: bool = False,
    ) -> InterviewAnswerResponse:
        spec = get_session(session_id)
        if not spec:
            from app.core.exceptions import KnowledgeBaseError
            raise KnowledgeBaseError("Interview session not found", {"session_id": session_id})

        asked_key = spec.pending_target_slot or (
            spec.next_slot_to_ask().key if spec.next_slot_to_ask() else ""
        )
        target = next((s for s in spec.slots if s.key == asked_key), None)
        target_key = target.key if target else ""
        target_label = target.label if target else ""

        if spec.pending_is_followup and target:
            target.value = f"{target.value.strip()}\n\nFurther detail: {answer.strip()}"
            target.status = SlotStatus.CONFIRMED
            target.depth_followup_done = True
            target.source = "interview"
            spec.pending_is_followup = False
            changed = [target.key]
        else:
            updates = await self._extract_slots_from_text(
                spec,
                ANSWER_PARSE_SYSTEM,
                ANSWER_PARSE_USER,
                {
                    "target_slot": target_key,
                    "target_label": target_label,
                    "answer": answer,
                },
            )
            changed = self._apply_updates(spec, updates)
            for s in spec.slots:
                if s.key not in DEPTH_FOLLOWUP_SLOTS:
                    s.depth_followup_done = True
            if target:
                self._mark_depth_if_sufficient(target)

        if force_complete:
            spec.ready_for_plan = True
            for s in spec.slots:
                if s.value.strip() and s.status != SlotStatus.CONFIRMED:
                    s.status = SlotStatus.CONFIRMED
                elif not s.value.strip():
                    s.value = "(Not specified — proceed with best effort)"
                    s.status = SlotStatus.CONFIRMED
                s.depth_followup_done = True

        if spec.is_complete():
            spec.ready_for_plan = True

        update_session(spec)

        complete = spec.is_complete() or force_complete
        question = None
        options: list[InterviewOption] = []
        next_target = None
        is_followup = False

        if not complete:
            followup = await self._maybe_followup(spec, target_key)
            if followup:
                question, options, next_target = followup[0], followup[1], followup[2]
                is_followup = True
                update_session(spec)
            else:
                next_slot = spec.next_slot_to_ask()
                if next_slot:
                    question, options = await self._build_question(spec, next_slot)
                    is_followup = spec.pending_is_followup
                    next_target = next_slot.key
                    update_session(spec)
        else:
            self._set_pending_question(spec, None, None, [])

        return InterviewAnswerResponse(
            session_id=session_id,
            spec=spec,
            is_complete=complete,
            completion_pct=spec.completion_pct(),
            question=question,
            options=options,
            target_slot=next_target,
            target_slot_label=_slot_label(spec, next_target),
            answered_slot=target_key or None,
            answered_slot_label=target_label or None,
            is_followup=is_followup,
            slots_updated=changed,
            message="All set — you can review the specification and build the diagram."
            if complete
            else (
                "Could you add a bit more detail on this topic?"
                if is_followup
                else "Pick the option that fits best, or choose Other."
            ),
        )

    def status(self, session_id: str) -> InterviewStatusResponse:
        spec = get_session(session_id)
        if not spec:
            from app.core.exceptions import KnowledgeBaseError
            raise KnowledgeBaseError("Interview session not found", {"session_id": session_id})
        pending = [s for s in spec.slots if s.status != SlotStatus.CONFIRMED or not s.value.strip()]
        return InterviewStatusResponse(
            session_id=session_id,
            spec=spec,
            is_complete=spec.is_complete(),
            completion_pct=spec.completion_pct(),
            pending_slots=pending,
            question=spec.pending_question or None,
            options=self._pending_options(spec),
            target_slot=spec.pending_target_slot or None,
            target_slot_label=_slot_label(spec, spec.pending_target_slot or None),
            is_followup=spec.pending_is_followup,
        )
