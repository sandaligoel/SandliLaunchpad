"""Search API routes."""

from fastapi import APIRouter

from backend.app.api.dependencies import get_search_service
from backend.app.schemas.search import (
    AgentSearchRequest,
    ArchitectureSearchRequest,
    SearchRequest,
    SearchResponse,
)

router = APIRouter(prefix="/search", tags=["Search"])


@router.post("", response_model=SearchResponse)
async def search(request: SearchRequest) -> SearchResponse:
    """
    General hybrid/semantic/keyword search across all entity types.
    Supports metadata filters for industry, cloud, models, retrieval, etc.
    """
    service = get_search_service()
    return await service.search(request)


@router.post("/agents", response_model=SearchResponse)
async def search_agents(request: AgentSearchRequest) -> SearchResponse:
    """
    Agent-centric retrieval — e.g. "recommendation agents in retail",
    "agents handling human escalation".
    """
    service = get_search_service()
    return await service.search_agents(request)


@router.post("/architectures", response_model=SearchResponse)
async def search_architectures(
    request: ArchitectureSearchRequest,
) -> SearchResponse:
    """
    Architecture pattern retrieval — e.g. "multi-agent orchestration",
    "Azure-deployed RAG systems".
    """
    service = get_search_service()
    return await service.search_architectures(request)
