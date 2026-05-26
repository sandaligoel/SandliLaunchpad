"""Health and readiness endpoints."""

from fastapi import APIRouter

from app import __version__
from app.core.config import get_settings
from app.schemas.api import HealthResponse, IndexStatsResponse

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    settings = get_settings()
    index_ready = bool(
        settings.azure_search_endpoint and settings.azure_search_api_key
    )
    return HealthResponse(
        status="healthy",
        version=__version__,
        index_name=settings.azure_search_index_name,
        index_ready=index_ready,
    )


@router.get("/index/stats", response_model=IndexStatsResponse)
async def index_stats() -> IndexStatsResponse:
    settings = get_settings()
    try:
        from app.search.index_manager import IndexManager

        client = IndexManager().get_search_client()
        results = client.search(search_text="*", top=0, include_total_count=True)
        total = results.get_count()  # type: ignore[union-attr]
        return IndexStatsResponse(
            index_name=settings.azure_search_index_name,
            document_count=total,
        )
    except Exception:
        return IndexStatsResponse(
            index_name=settings.azure_search_index_name,
            document_count=None,
        )
