"""Target architecture specification filled by the Phase 2 requirements interview."""

from __future__ import annotations

from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field

SpecStatus = Literal["draft", "sufficient", "ready"]

# Alias: every requirements field must be known before architecture questions.
# Defined after REQUIREMENTS_FIELD_ORDER (see bottom of field lists).

FieldSource = Literal["problem_statement", "user_answer", "inferred"]


class FieldStatus(str, Enum):
    """Whether a spec field has a confirmed value."""

    PENDING = "pending"
    KNOWN = "known"


REQUIREMENTS_FIELD_DEFINITIONS: list[tuple[str, str]] = [
    ("use_case", "Main goal"),
    ("data_volume", "How much data"),
    ("accuracy_target", "How accurate it must be"),
    ("hitl_behavior", "When someone should review results"),
    ("integrations", "Where data comes from and goes"),
    ("latency_target", "How fast answers are needed"),
    ("model_preference", "AI preference"),
    ("deployment_platform", "Where it should run"),
]

ARCHITECTURE_FIELD_DEFINITIONS: list[tuple[str, str]] = [
    ("architectural_flow", "Order of steps in your process"),
    ("architectural_flow_feedback", "Check the steps we understood"),
    ("architectural_pattern", "Overall approach"),
    ("core_components", "Main parts you need"),
    ("data_flow", "Where information comes from and goes"),
    ("orchestration_model", "How steps run (one-by-one or together)"),
    ("scalability_constraints", "How many people use it at once"),
]

# Question order within each group (used by interview picker).
REQUIREMENTS_FIELD_ORDER: tuple[str, ...] = tuple(
    k for k, _ in REQUIREMENTS_FIELD_DEFINITIONS
)
ARCHITECTURE_FIELD_ORDER: tuple[str, ...] = tuple(
    k for k, _ in ARCHITECTURE_FIELD_DEFINITIONS
)

# Only these are asked in the chat (non-technical users).
USER_INTERVIEW_REQUIREMENT_KEYS: tuple[str, ...] = (
    "hitl_behavior",
    "integrations",
)
INFERRED_REQUIREMENT_KEYS: tuple[str, ...] = tuple(
    k for k, _ in REQUIREMENTS_FIELD_DEFINITIONS
    if k not in USER_INTERVIEW_REQUIREMENT_KEYS
)

USER_INTERVIEW_ARCHITECTURE_KEYS: tuple[str, ...] = (
    "architectural_flow",
    "core_components",
)
INFERRED_ARCHITECTURE_KEYS: tuple[str, ...] = tuple(
    k for k, _ in ARCHITECTURE_FIELD_DEFINITIONS
    if k not in USER_INTERVIEW_ARCHITECTURE_KEYS
)

USER_INTERVIEW_FIELD_KEYS: tuple[str, ...] = (
    USER_INTERVIEW_REQUIREMENT_KEYS + USER_INTERVIEW_ARCHITECTURE_KEYS
)

CORE_REQUIREMENTS_BEFORE_ARCHITECTURE: tuple[str, ...] = USER_INTERVIEW_REQUIREMENT_KEYS
SUFFICIENT_REQUIREMENT_KEYS: tuple[str, ...] = USER_INTERVIEW_REQUIREMENT_KEYS

SPEC_FIELD_DEFINITIONS: list[tuple[str, str]] = (
    REQUIREMENTS_FIELD_DEFINITIONS + ARCHITECTURE_FIELD_DEFINITIONS
)

REQUIRED_FIELD_KEYS: tuple[str, ...] = tuple(k for k, _ in SPEC_FIELD_DEFINITIONS)

FIELD_GROUPS: dict[str, list[str]] = {
    "requirements": [k for k, _ in REQUIREMENTS_FIELD_DEFINITIONS],
    "architecture": [k for k, _ in ARCHITECTURE_FIELD_DEFINITIONS],
}


class CatalogHint(BaseModel):
    """Similar agent from Phase 1 catalog (grounded in data/spec.json)."""

    agent_id: str
    name: str
    category: str = ""
    origin_client: str = ""
    function_summary: str = ""
    score: float = 0.0
    origin_project: str = ""
    integrations: str = ""
    model_used: str = ""
    status: str = "available"


class GraphNode(BaseModel):
    """Draft node for Phase 3 canvas."""

    id: str
    label: str
    type: Literal["agent", "custom", "gateway", "human"] = "custom"
    agent_id: Optional[str] = None
    description: Optional[str] = None


class GraphEdge(BaseModel):
    """Draft edge for Phase 3 canvas."""

    from_id: str
    to_id: str
    label: Optional[str] = None


class GraphDraft(BaseModel):
    """Structured graph emitted with the architecture blueprint."""

    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)


class SpecField(BaseModel):
    """One slot in the architecture specification form."""

    key: str
    label: str
    value: Optional[str] = None
    status: FieldStatus = FieldStatus.PENDING
    notes: Optional[str] = None
    source: Optional[FieldSource] = None
    confidence: Optional[float] = None

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
    transcript_summary: str = ""
    catalog_hints: list[CatalogHint] = Field(default_factory=list)
    architecture_blueprint: Optional[str] = None
    graph_draft: Optional[GraphDraft] = None

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

    def pending_core_requirements_keys(self) -> list[str]:
        """User-facing requirements that must be answered before architecture questions."""
        return [
            key
            for key in CORE_REQUIREMENTS_BEFORE_ARCHITECTURE
            if key in self.fields and not self.fields[key].is_known
        ]

    def pending_user_interview_keys(self) -> list[str]:
        """Fields the chatbot may ask (excludes latency, accuracy, etc.)."""
        return [
            key
            for key in USER_INTERVIEW_FIELD_KEYS
            if key in self.fields and not self.fields[key].is_known
        ]

    def core_requirements_complete(self) -> bool:
        return not self.pending_core_requirements_keys()

    def user_interview_complete(self) -> bool:
        return not self.pending_user_interview_keys()

    def known_count(self) -> int:
        return sum(1 for key in REQUIRED_FIELD_KEYS if self.fields[key].is_known)

    def total_required(self) -> int:
        return len(REQUIRED_FIELD_KEYS)

    def recompute_status(self) -> None:
        """Ready when user-facing interview topics are filled (often after LLM wrap-up)."""
        if self.user_interview_complete():
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
            if patch.get("notes"):
                field.notes = str(patch["notes"]).strip() or None
            if patch.get("source") in ("problem_statement", "user_answer", "inferred"):
                field.source = patch["source"]
            if patch.get("confidence") is not None:
                try:
                    field.confidence = float(patch["confidence"])
                except (TypeError, ValueError):
                    pass
        self.recompute_status()

    def compact_known_json(self) -> dict:
        """Known fields only — for smaller LLM prompts."""
        return {
            key: {
                "value": self.fields[key].value,
                "status": self.fields[key].status.value,
                "source": self.fields[key].source,
            }
            for key in REQUIRED_FIELD_KEYS
            if self.fields[key].is_known
        }


class ChatMessage(BaseModel):
    """One message in the interview transcript (UI + audit trail)."""

    role: Literal["assistant", "user"]
    content: str
    field_key: Optional[str] = None


class ClarifyingQuestionItem(BaseModel):
    """Pre-interview question before agents or architecture are suggested."""

    id: str
    question: str
    why_it_matters: str = ""


class InterviewQuestion(BaseModel):
    """Assistant turn: one focused question with chip options."""

    field_key: str
    question: str
    chips: list[str] = Field(default_factory=list)
    why_it_matters: Optional[str] = None


class InterviewSession(BaseModel):
    """Full server state for one requirements interview."""

    id: str
    spec: ArchitectureSpec
    messages: list[ChatMessage] = Field(default_factory=list)
    pending_question: Optional[InterviewQuestion] = None
    last_answered_field: Optional[str] = None
    architecture_plan: Optional["ArchitecturePlan"] = None
    clarifying_questions: list[ClarifyingQuestionItem] = Field(default_factory=list)
    clarifying_answers: dict[str, str] = Field(default_factory=dict)


from schemas.architecture_plan import ArchitecturePlan  # noqa: E402

InterviewSession.model_rebuild()
