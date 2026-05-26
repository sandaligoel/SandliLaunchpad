"""FastAPI request/response schemas for ingestion endpoints."""

from pydantic import BaseModel, Field

from app.schemas.extraction import ProjectKnowledge
from app.schemas.search import EntityType


class IngestPDFResponse(BaseModel):
    success: bool
    project_id: str
    project_name: str
    filename: str
    pages_processed: int
    chunks_created: int
    entities_indexed: int
    entity_breakdown: dict[str, int]
    project_knowledge: ProjectKnowledge | None = None
    correlation_id: str
    warnings: list[str] = Field(default_factory=list)
    ingestion_mode: str = "pdf"


class IngestCatalogResponse(BaseModel):
    """Response when ingesting a multi-solution catalog PDF."""

    success: bool
    filename: str
    pages_processed: int
    solutions_found: int
    solutions_indexed: int
    total_entities_indexed: int
    entity_breakdown: dict[str, int]
    projects: list[IngestPDFResponse] = Field(default_factory=list)
    correlation_id: str
    ingestion_mode: str = "solution_catalog"


class HealthResponse(BaseModel):
    status: str
    version: str
    index_name: str
    index_ready: bool


class IndexStatsResponse(BaseModel):
    index_name: str
    document_count: int | None = None
