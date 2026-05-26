"""Interview session API schemas."""

from pydantic import BaseModel, Field

from app.schemas.architecture_spec import ArchitectureSpec, SpecSlot


class InterviewOption(BaseModel):
    """Selectable answer choice for a targeted interview question."""

    id: str
    label: str
    value: str = Field(description="Text submitted as the answer when this option is chosen")


class InterviewStartRequest(BaseModel):
    problem_statement: str = Field(..., min_length=20, max_length=8000)


class InterviewStartResponse(BaseModel):
    session_id: str
    spec: ArchitectureSpec
    is_complete: bool
    completion_pct: float
    question: str | None = None
    options: list[InterviewOption] = Field(default_factory=list)
    target_slot: str | None = None
    target_slot_label: str | None = None
    is_followup: bool = False
    message: str = ""


class InterviewAnswerRequest(BaseModel):
    session_id: str
    answer: str = Field(..., min_length=1, max_length=4000)
    force_complete: bool = False


class InterviewAnswerResponse(BaseModel):
    session_id: str
    spec: ArchitectureSpec
    is_complete: bool
    completion_pct: float
    question: str | None = None
    options: list[InterviewOption] = Field(default_factory=list)
    target_slot: str | None = None
    target_slot_label: str | None = None
    answered_slot: str | None = None
    answered_slot_label: str | None = None
    is_followup: bool = False
    slots_updated: list[str] = Field(default_factory=list)
    message: str = ""


class InterviewStatusResponse(BaseModel):
    session_id: str
    spec: ArchitectureSpec
    is_complete: bool
    completion_pct: float
    pending_slots: list[SpecSlot] = Field(default_factory=list)
    question: str | None = None
    options: list[InterviewOption] = Field(default_factory=list)
    target_slot: str | None = None
    target_slot_label: str | None = None
    is_followup: bool = False
