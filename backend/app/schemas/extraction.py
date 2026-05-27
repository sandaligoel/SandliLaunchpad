"""Pydantic schemas for structured AI architecture knowledge extraction."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class SchemaVersion(str, Enum):
    V1 = "1.0.0"


class SectionType(str, Enum):
    PROJECT_OVERVIEW = "project_overview"
    AGENT = "agent"
    ARCHITECTURE = "architecture"
    WORKFLOW = "workflow"
    TECH_STACK = "tech_stack"
    DEPLOYMENT = "deployment"
    USE_CASE = "use_case"
    CONSTRAINTS = "constraints"
    INTEGRATION = "integration"
    GENERAL = "general"
    TABLE = "table"


class OrchestrationPattern(str, Enum):
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    SUPERVISOR = "supervisor"
    HIERARCHICAL = "hierarchical"
    EVENT_DRIVEN = "event_driven"
    UNKNOWN = "unknown"


class RelationType(str, Enum):
    USES = "uses"
    DEPENDS_ON = "depends_on"
    INVOKES = "invokes"
    PART_OF = "part_of"
    ESCALATES_TO = "escalates_to"
    RETRIEVES_FROM = "retrieves_from"


class EntityRelationship(BaseModel):
    source_type: str
    source_id: str = ""
    source_name: str = ""
    target_type: str
    target_id: str = ""
    target_name: str = ""
    relation: RelationType = RelationType.USES


class AgentKnowledge(BaseModel):
    agent_id: str = ""
    agent_name: str = ""
    purpose: str = ""
    inputs: list[str] = Field(default_factory=list)
    outputs: list[str] = Field(default_factory=list)
    llm_used: str = ""
    tools_used: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    workflow_position: str = ""
    memory_used: str = ""
    retrieval_used: bool = False
    decision_logic: str = ""
    external_integrations: list[str] = Field(default_factory=list)
    capabilities: list[str] = Field(default_factory=list)
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0)

    @field_validator(
        "inputs", "outputs", "tools_used", "dependencies",
        "external_integrations", "capabilities",
        mode="before",
    )
    @classmethod
    def coerce_lists(cls, v: Any) -> list[str]:
        if v is None:
            return []
        if isinstance(v, str):
            return [v] if v.strip() else []
        return list(v)


class WorkflowKnowledge(BaseModel):
    workflow_id: str = ""
    name: str = ""
    description: str = ""
    steps: list[str] = Field(default_factory=list)
    triggers: list[str] = Field(default_factory=list)
    orchestration_notes: str = ""
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0)


class ArchitectureKnowledge(BaseModel):
    pattern: str = ""
    communication_style: str = ""
    orchestration_framework: str = ""
    deployment: str = ""
    cloud_provider: str = ""
    deployment_model: str = ""
    scalability_notes: str = ""
    latency_constraints: str = ""
    security_notes: str = ""
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0)


class OrchestrationKnowledge(BaseModel):
    framework: str = ""
    pattern: OrchestrationPattern = OrchestrationPattern.UNKNOWN
    agent_graph_description: str = ""
    supervisor_agent: str = ""
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0)


class IntegrationKnowledge(BaseModel):
    name: str = ""
    integration_type: str = ""
    protocol: str = ""
    purpose: str = ""


class ExtractionMetadata(BaseModel):
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0)
    source_chunk_ids: list[str] = Field(default_factory=list)
    model_version: str = ""
    schema_version: str = SchemaVersion.V1.value
    extracted_at: datetime = Field(default_factory=datetime.utcnow)
    extraction_notes: str = ""


class SourceDocument(BaseModel):
    filename: str
    page_count: int = 0
    ingested_at: datetime = Field(default_factory=datetime.utcnow)
    content_hash: str = ""


class ChunkExtraction(BaseModel):
    """Partial extraction from a single semantic chunk — grounded, minimal."""

    chunk_id: str
    section_type: SectionType = SectionType.GENERAL
    project_name_hint: str = ""
    industry_hint: str = ""
    agents: list[AgentKnowledge] = Field(default_factory=list)
    workflows: list[WorkflowKnowledge] = Field(default_factory=list)
    architecture: ArchitectureKnowledge | None = None
    orchestration: OrchestrationKnowledge | None = None
    tech_stack: list[str] = Field(default_factory=list)
    models_used: list[str] = Field(default_factory=list)
    vector_databases: list[str] = Field(default_factory=list)
    apis_used: list[str] = Field(default_factory=list)
    integrations: list[IntegrationKnowledge] = Field(default_factory=list)
    business_problem: str = ""
    summary: str = ""
    workflow_description: str = ""
    business_outcomes: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    future_improvements: list[str] = Field(default_factory=list)
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0)
    evidence_quotes: list[str] = Field(
        default_factory=list,
        description="Short verbatim quotes supporting extraction",
    )


class ProjectKnowledge(BaseModel):
    """Full merged project knowledge — canonical architecture memory record."""

    project_id: str
    project_name: str = ""
    industry: str = ""
    business_problem: str = ""
    summary: str = ""
    agents: list[AgentKnowledge] = Field(default_factory=list)
    workflows: list[WorkflowKnowledge] = Field(default_factory=list)
    architecture: ArchitectureKnowledge = Field(default_factory=ArchitectureKnowledge)
    orchestration: OrchestrationKnowledge = Field(default_factory=OrchestrationKnowledge)
    tech_stack: list[str] = Field(default_factory=list)
    models_used: list[str] = Field(default_factory=list)
    vector_databases: list[str] = Field(default_factory=list)
    apis_used: list[str] = Field(default_factory=list)
    integrations: list[IntegrationKnowledge] = Field(default_factory=list)
    workflow_description: str = ""
    business_outcomes: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    future_improvements: list[str] = Field(default_factory=list)
    relationships: list[EntityRelationship] = Field(default_factory=list)
    source_document: SourceDocument | None = None
    extraction_metadata: ExtractionMetadata = Field(default_factory=ExtractionMetadata)

    def model_post_init(self, __context: Any) -> None:
        for i, agent in enumerate(self.agents):
            if not agent.agent_id:
                self.agents[i] = agent.model_copy(
                    update={"agent_id": f"{self.project_id}:agent:{i}"}
                )
        for i, wf in enumerate(self.workflows):
            if not wf.workflow_id:
                self.workflows[i] = wf.model_copy(
                    update={"workflow_id": f"{self.project_id}:workflow:{i}"}
                )
