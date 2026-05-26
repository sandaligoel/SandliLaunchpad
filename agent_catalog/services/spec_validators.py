"""Deterministic validation for ArchitectureSpec fields after LLM updates."""

from __future__ import annotations

import re
from typing import Optional

from schemas.architecture_spec import ArchitectureSpec, FIELD_GROUPS

_LATENCY_PATTERN = re.compile(
    r"(\d+\s*(ms|sec|secs|second|seconds|s|min|minutes|hour|hours|h)\b|real[- ]?time|batch|near[- ]?real[- ]?time)",
    re.IGNORECASE,
)
_ACCURACY_PATTERN = re.compile(r"(\d+\s*%|high|medium|low|strict|lenient)", re.IGNORECASE)


def validate_field_value(field_key: str, value: Optional[str]) -> list[str]:
    """
    Return validation warnings for a field value (empty list = acceptable).

    Warnings do not block known status but are stored in field notes for the UI.
    """
    if not value or not value.strip():
        return ["Value is empty"]

    text = value.strip()
    warnings: list[str] = []

    if field_key == "latency_target" and not _LATENCY_PATTERN.search(text):
        warnings.append("Specify a latency target (e.g. '<2s', 'batch nightly', 'real-time').")

    if field_key == "accuracy_target" and not _ACCURACY_PATTERN.search(text):
        warnings.append("Specify accuracy (e.g. '96%', 'high precision').")

    if field_key == "data_volume" and len(text) < 8:
        warnings.append("Add scale detail (e.g. documents/day, concurrent users).")

    if field_key == "integrations" and len(text) < 3:
        warnings.append("Name at least one external system or API.")

    if field_key in ("architectural_flow", "architectural_flow_feedback", "data_flow"):
        if len(text) < 40:
            warnings.append("Flow description is very short — add steps or components.")

    return warnings


def apply_validators(spec: ArchitectureSpec) -> list[str]:
    """
    Run validators on all known fields; append warnings to notes.

    Returns:
        List of human-readable warning messages for logging.
    """
    log_warnings: list[str] = []
    for key, field in spec.fields.items():
        if not field.is_known or not field.value:
            continue
        for msg in validate_field_value(key, field.value):
            note = f"Validator: {msg}"
            field.notes = f"{field.notes} | {note}" if field.notes else note
            log_warnings.append(f"{key}: {msg}")

    _validate_dependencies(spec, log_warnings)
    return log_warnings


def _validate_dependencies(spec: ArchitectureSpec, log_warnings: list[str]) -> None:
    """Cross-field rules (logged only)."""
    hitl = spec.fields.get("hitl_behavior")
    integrations = spec.fields.get("integrations")
    if hitl and hitl.is_known and hitl.value:
        if "approval" in hitl.value.lower() or "human" in hitl.value.lower():
            if integrations and integrations.is_known:
                if integrations.value and "email" not in integrations.value.lower():
                    if "ui" not in integrations.value.lower() and "portal" not in integrations.value.lower():
                        log_warnings.append(
                            "hitl_behavior: HITL mentioned but integrations may need email/UI."
                        )

    pattern = spec.fields.get("architectural_pattern")
    data_flow = spec.fields.get("data_flow")
    if pattern and pattern.is_known and pattern.value:
        pl = pattern.value.lower()
        if "graphrag" in pl or "rag" in pl:
            if data_flow and data_flow.is_known and data_flow.value:
                if "index" not in data_flow.value.lower() and "vector" not in data_flow.value.lower():
                    log_warnings.append(
                        "data_flow: RAG/GraphRAG pattern usually needs indexing/vector store in data_flow."
                    )
