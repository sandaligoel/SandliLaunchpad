"""Target architecture specification filled by the Phase 2 requirements interview."""

from __future__ import annotations

from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field

SpecStatus = Literal["draft", "ready"]


class FieldStatus(str, Enum):
    """Whether a spec field has a confirmed value."""

    PENDING = "pending"
    KNOWN = "known"


REQUIREMENTS_FIELD_DEFINITIONS: list[tuple[str, str]] = [
    ("use_case", "Use case"),
    ("data_volume", "Data volume"),
    ("accuracy_target", "Accuracy target"),
    ("hitl_behavior", "HITL / uncertainty behaviour"),
    ("integrations", "Required integrations"),
    ("latency_target", "Latency target"),
    ("model_preference", "Model preference"),
    ("deployment_platform", "Deployment platform"),
]

ARCHITECTURE_FIELD_DEFINITIONS: list[tuple[str, str]] = [
    ("architectural_flow", "End-to-end architectural flow"),
    ("architectural_flow_feedback", "Architectural flow — your feedback"),
    ("architectural_pattern", "Architectural pattern"),
    ("core_components", "Core components / agents"),
    ("data_flow", "Data flow between components"),
    ("orchestration_model", "Orchestration model"),
    ("scalability_constraints", "Scalability & concurrency"),
]

# Question order within each group (used by interview picker).
REQUIREMENTS_FIELD_ORDER: tuple[str, ...] = tuple(
    k for k, _ in REQUIREMENTS_FIELD_DEFINITIONS
)
ARCHITECTURE_FIELD_ORDER: tuple[str, ...] = tuple(
    k for k, _ in ARCHITECTURE_FIELD_DEFINITIONS
)

SPEC_FIELD_DEFINITIONS: list[tuple[str, str]] = (
    REQUIREMENTS_FIELD_DEFINITIONS + ARCHITECTURE_FIELD_DEFINITIONS
)

REQUIRED_FIELD_KEYS: tuple[str, ...] = tuple(k for k, _ in SPEC_FIELD_DEFINITIONS)

FIELD_GROUPS: dict[str, list[str]] = {
    "requirements": [k for k, _ in REQUIREMENTS_FIELD_DEFINITIONS],
    "architecture": [k for k, _ in ARCHITECTURE_FIELD_DEFINITIONS],
}


class SpecField(BaseModel):
    """One slot in the architecture specification form."""

    key: str
    label: str
    value: Optional[str] = None
    status: FieldStatus = FieldStatus.PENDING
    notes: Optional[str] = None

    @property
    def is_known(self) -> bool:
        return self.status == FieldStatus.KNOWN and bool(self.value and self.value.strip())


class ArchitectureSpec(BaseModel):
    """
    Single source of truth for requirements and architecture flow gathered in Phase 2.

    Passed as JSON into every LLM prompt; the chat transcript is auxiliary context only.
    """

    status: SpecStatus = "draft"
    problem_statement: str = ""
    fields: dict[str, SpecField] = Field(default_factory=dict)
    architecture_blueprint: Optional[str] = None

    @classmethod
    def empty(cls, problem_statement: str = "") -> ArchitectureSpec:
        """Create a spec with all target fields in pending state."""
        fields = {
            key: SpecField(key=key, label=label)
            for key, label in SPEC_FIELD_DEFINITIONS
        }
        return cls(problem_statement=problem_statement.strip(), fields=fields)

    def pending_field_keys(self) -> list[str]:
        """Return keys still missing a confirmed value, in definition order."""
        return [key for key in REQUIRED_FIELD_KEYS if not self.fields[key].is_known]

    def pending_architecture_keys(self) -> list[str]:
        return [
            key
            for key in FIELD_GROUPS["architecture"]
            if key in self.fields and not self.fields[key].is_known
        ]

    def pending_requirements_keys(self) -> list[str]:
        return [
            key
            for key in FIELD_GROUPS["requirements"]
            if key in self.fields and not self.fields[key].is_known
        ]

    def known_count(self) -> int:
        return sum(1 for key in REQUIRED_FIELD_KEYS if self.fields[key].is_known)

    def total_required(self) -> int:
        return len(REQUIRED_FIELD_KEYS)

    def recompute_status(self) -> None:
        """Set status to ready when every required field is known."""
        if not self.pending_field_keys():
            self.status = "ready"
        else:
            self.status = "draft"

    def apply_field_updates(self, updates: dict[str, dict]) -> None:
        """
        Merge LLM field updates into the spec.

        Each update entry may include: value, status (pending|known), notes.
        """
        for key, patch in updates.items():
            if key not in self.fields:
                continue
            field = self.fields[key]
            if "value" in patch and patch["value"] is not None:
                value = str(patch["value"]).strip()
                if value:
                    field.value = value
            if patch.get("status") == "known" or patch.get("status") == FieldStatus.KNOWN:
                field.status = FieldStatus.KNOWN
            elif patch.get("status") == "pending" or patch.get("status") == FieldStatus.PENDING:
                field.status = FieldStatus.PENDING
            elif field.value:
                field.status = FieldStatus.KNOWN
            if patch.get("notes"):
                field.notes = str(patch["notes"]).strip() or None
        self.recompute_status()


class ChatMessage(BaseModel):
    """One message in the interview transcript (UI + audit trail)."""

    role: Literal["assistant", "user"]
    content: str
    field_key: Optional[str] = None


class InterviewQuestion(BaseModel):
    """Assistant turn: one focused question with chip options."""

    field_key: str
    question: str
    chips: list[str] = Field(default_factory=list)


class InterviewSession(BaseModel):
    """Full server state for one requirements interview."""

    id: str
    spec: ArchitectureSpec
    messages: list[ChatMessage] = Field(default_factory=list)
    pending_question: Optional[InterviewQuestion] = None
    last_answered_field: Optional[str] = None
