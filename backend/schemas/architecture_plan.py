"""Phase 3 architecture plan — graph + catalog reuse decisions."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

from schemas.architecture_spec import CatalogHint, GraphDraft

ReuseDecisionType = Literal["reuse", "adapt", "build"]


class CatalogMatch(BaseModel):
    """Agent retrieved from the catalog for planning."""

    agent_id: str
    name: str
    category: str = ""
    origin_client: str = ""
    origin_project: str = ""
    function_summary: str = ""
    score: float = 0.0
    matched_for: str = ""


class ReuseDecision(BaseModel):
    """Whether a graph node reuses a catalog agent or is built custom."""

    node_id: str
    node_label: str
    decision: ReuseDecisionType
    agent_id: Optional[str] = None
    agent_name: Optional[str] = None
    rationale: str = ""
    catalog_score: Optional[float] = None


class RemediationOption(BaseModel):
    """User-selectable fix for a validation finding."""

    id: str
    label: str
    description: str = ""
    finding_id: str = ""
    action: str = "acknowledge"
    node_id: Optional[str] = None
    decision: Optional[ReuseDecisionType] = None
    agent_id: Optional[str] = None
    agent_name: Optional[str] = None
    catalog_score: Optional[float] = None
    gateway_label: Optional[str] = None
    question_text: Optional[str] = None
    edge_from: Optional[str] = None
    edge_to: Optional[str] = None


class ValidationResolution(BaseModel):
    """Recorded user choice for a finding."""

    action: str
    action_id: str
    label: str = ""


class ValidationFinding(BaseModel):
    """One pass, warn, or fail check."""

    level: Literal["pass", "warn", "fail"]
    code: str
    message: str
    node_id: Optional[str] = None
    finding_id: Optional[str] = None
    finding_key: Optional[str] = None
    blocks_approval: bool = False
    help_text: str = ""
    remediations: list[RemediationOption] = Field(default_factory=list)
    resolved: bool = False
    resolution: Optional[ValidationResolution] = None


class ArchitectureValidationReport(BaseModel):
    """Rule-based validation of plan vs spec and catalog."""

    overall: Literal["pass", "warn", "fail"] = "pass"
    pass_count: int = 0
    warn_count: int = 0
    fail_count: int = 0
    structural_fail_count: int = 0
    unresolved_actionable_count: int = 0
    can_approve: bool = False
    approval_hint: str = ""
    items: list[ValidationFinding] = Field(default_factory=list)
    node_status: dict[str, Literal["pass", "warn", "fail"]] = Field(
        default_factory=dict
    )


class ArchitecturePlan(BaseModel):
    """Final planned architecture for canvas rendering."""

    graph: GraphDraft
    reuse_decisions: list[ReuseDecision] = Field(default_factory=list)
    catalog_matches: list[CatalogMatch] = Field(default_factory=list)
    summary_markdown: str = ""
    open_questions: list[str] = Field(default_factory=list)
    validation: Optional[ArchitectureValidationReport] = None
    validation_resolutions: dict[str, ValidationResolution] = Field(
        default_factory=dict
    )
    architecture_approved: bool = False
