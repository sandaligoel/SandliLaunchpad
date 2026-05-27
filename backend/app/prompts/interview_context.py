"""Helpers for JSON-grounded interview prompts."""

from __future__ import annotations

import json
import re

from backend.app.schemas.architecture_spec import ArchitectureSpec, SlotStatus

# Prior answers that should inform the next question.
SLOT_RELATED: dict[str, list[str]] = {
    "flow_steps": [],
    "agent_roles": ["flow_steps"],
    "data_sources": ["flow_steps"],
    "data_volume_scale": ["flow_steps", "data_sources"],
    "orchestration_pattern": ["flow_steps", "agent_roles"],
    "retrieval_required": ["flow_steps", "data_sources", "agent_roles"],
    "knowledge_graph_scope": ["flow_steps", "retrieval_required"],
    "agent_tools": ["agent_roles", "data_sources"],
    "model_constraints": ["agent_roles"],
    "integrations": ["data_sources", "flow_steps"],
    "deployment_target": ["data_volume_scale"],
    "cloud_provider": ["deployment_target"],
    "human_in_the_loop": ["flow_steps", "agent_roles"],
    "failure_escalation": ["flow_steps", "agent_roles"],
}

_HELPER_WORD = re.compile(r"\bhelpers?\b", re.IGNORECASE)


def spec_slots_json(spec: ArchitectureSpec) -> str:
    rows = [
        {
            "key": s.key,
            "label": s.label,
            "description": s.description,
            "value": s.value or "",
            "status": s.status.value,
            "required": s.required,
        }
        for s in sorted(spec.slots, key=lambda x: x.priority)
    ]
    return json.dumps(rows, indent=2)


def related_slots_json(spec: ArchitectureSpec, target_key: str) -> str:
    related_keys = SLOT_RELATED.get(target_key, [])
    if not related_keys:
        return "[]"
    by_key = {s.key: s for s in spec.slots}
    rows = []
    for key in related_keys:
        s = by_key.get(key)
        if not s or not s.value.strip():
            continue
        rows.append(
            {
                "key": s.key,
                "label": s.label,
                "value": s.value,
                "status": s.status.value,
            }
        )
    return json.dumps(rows, indent=2)


def interview_progress_summary(spec: ArchitectureSpec) -> str:
    confirmed = [
        s.label for s in spec.slots if s.status == SlotStatus.CONFIRMED and s.value.strip()
    ]
    inferred = [
        s.label for s in spec.slots if s.status == SlotStatus.INFERRED and s.value.strip()
    ]
    empty = [s.label for s in spec.slots if not s.value.strip()]
    parts = []
    if confirmed:
        parts.append(f"Confirmed: {', '.join(confirmed)}")
    if inferred:
        parts.append(f"Needs confirmation: {', '.join(inferred)}")
        parts.append(f"Still empty: {', '.join(empty[:6])}")
    return " | ".join(parts) if parts else "No slots filled yet."


def sanitize_interview_text(text: str) -> str:
    """Replace vague 'helper' role wording with plain 'automated step'."""
    if not text:
        return text

    def _repl(match: re.Match[str]) -> str:
        word = "automated step" if match.group(0).lower() == "helper" else "automated steps"
        if match.start() == 0 or (match.start() > 0 and text[match.start() - 1] in ".!?\n"):
            word = word[0].upper() + word[1:]
        return word

    return _HELPER_WORD.sub(_repl, text)