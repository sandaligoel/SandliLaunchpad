"""Architecture graph — nodes, edges, reuse decisions."""

from enum import Enum

from pydantic import BaseModel, Field

from app.schemas.architecture_spec import ArchitectureSpec


class NodeType(str, Enum):
    AGENT = "agent"
    TOOL = "tool"
    DATA_STORE = "data_store"
    HUMAN = "human"
    API = "api"
    ORCHESTRATOR = "orchestrator"


class EdgeType(str, Enum):
    USES = "uses"
    PRODUCES = "produces"
    INVOKES = "invokes"
    READS_FROM = "reads_from"
    ESCALATES_TO = "escalates_to"
    PART_OF = "part_of"


class ReuseDecision(str, Enum):
    REUSE = "reuse"
    BUILD = "build"
    ADAPT = "adapt"


class GraphNode(BaseModel):
    id: str
    type: NodeType
    label: str
    description: str = ""
    layer: int = 0
    catalog_agent_id: str = ""
    source_project: str = ""
    reuse_decision: ReuseDecision = ReuseDecision.BUILD
    metadata: dict[str, str] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    type: EdgeType = EdgeType.USES
    label: str = ""


class CapabilityMatch(BaseModel):
    capability: str
    decision: ReuseDecision
    catalog_agent_name: str = ""
    catalog_project: str = ""
    search_score: float = 0.0
    rationale: str = ""


class ArchitecturePlanRequest(BaseModel):
    session_id: str | None = None
    spec: ArchitectureSpec | None = None


class ArchitecturePlanResponse(BaseModel):
    session_id: str = ""
    spec_summary: dict[str, str] = Field(default_factory=dict)
    capabilities: list[CapabilityMatch] = Field(default_factory=list)
    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)
    reuse_count: int = 0
    build_count: int = 0
    narrative: str = ""
