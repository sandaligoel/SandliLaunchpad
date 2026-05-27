"""Schemas for search index documents and API requests/responses."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class EntityType(str, Enum):
    PROJECT = "project"
    AGENT = "agent"
    WORKFLOW = "workflow"
    ARCHITECTURE = "architecture"
    CHUNK = "chunk"


class SearchDocument(BaseModel):
    """Azure AI Search index document."""

    id: str
    entity_type: EntityType
    project_id: str
    project_name: str = ""
    industry: str = ""
    title: str = ""
    content: str
    content_vector: list[float] = Field(default_factory=list)
    agent_name: str = ""
    agent_purpose: str = ""
    architecture_pattern: str = ""
    orchestration_framework: str = ""
    cloud_provider: str = ""
    deployment_model: str = ""
    tech_stack: list[str] = Field(default_factory=list)
    models_used: list[str] = Field(default_factory=list)
    tools_used: list[str] = Field(default_factory=list)
    capabilities: list[str] = Field(default_factory=list)
    workflow_keywords: list[str] = Field(default_factory=list)
    retrieval_used: bool = False
    source_filename: str = ""
    source_page_start: int = 0
    source_page_end: int = 0
    confidence_score: float = 0.0
    ingested_at: datetime = Field(default_factory=datetime.utcnow)
    structured_payload: str = ""

    def to_index_dict(self) -> dict[str, Any]:
        from backend.app.utils.ids import azure_safe_document_id

        data = self.model_dump(mode="json")
        data["id"] = azure_safe_document_id(str(data["id"]))
        if not data.get("content_vector"):
            del data["content_vector"]
        # Azure DateTimeOffset: ISO-8601 with timezone (Z)
        if ingested := data.get("ingested_at"):
            if isinstance(ingested, str) and not ingested.endswith("Z"):
                data["ingested_at"] = ingested.replace("+00:00", "Z")
                if "T" in data["ingested_at"] and not data["ingested_at"].endswith("Z"):
                    data["ingested_at"] = f"{data['ingested_at'].split('.')[0]}Z"
        # Omit empty collection fields
        for key in ("tech_stack", "models_used", "tools_used", "capabilities", "workflow_keywords"):
            if key in data and not data[key]:
                del data[key]
        return data


class SearchMode(str, Enum):
    HYBRID = "hybrid"
    SEMANTIC = "semantic"
    KEYWORD = "keyword"


class SearchFilter(BaseModel):
    entity_types: list[EntityType] | None = None
    industry: str | None = None
    cloud_provider: str | None = None
    models_used: list[str] | None = None
    retrieval_used: bool | None = None
    project_id: str | None = None
    min_confidence: float | None = None
    source_filename: str | None = None


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    top_k: int = Field(default=10, ge=1, le=100)
    mode: SearchMode = SearchMode.HYBRID
    filters: SearchFilter | None = None
    include_structured_payload: bool = False


class AgentSearchRequest(SearchRequest):
    agent_name_contains: str | None = None
    tools_used: list[str] | None = None


class ArchitectureSearchRequest(SearchRequest):
    architecture_pattern: str | None = None
    orchestration_framework: str | None = None


class SearchHit(BaseModel):
    id: str
    entity_type: EntityType
    project_id: str
    project_name: str
    title: str
    content: str
    score: float
    agent_name: str = ""
    architecture_pattern: str = ""
    cloud_provider: str = ""
    tech_stack: list[str] = Field(default_factory=list)
    models_used: list[str] = Field(default_factory=list)
    confidence_score: float = 0.0
    structured_payload: dict[str, Any] | None = None


class SearchResponse(BaseModel):
    query: str
    mode: SearchMode
    total_results: int
    results: list[SearchHit]
    correlation_id: str = ""
