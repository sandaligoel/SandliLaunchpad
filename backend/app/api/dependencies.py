"""FastAPI dependency injection."""

from functools import lru_cache

from backend.app.services.architecture_planner import ArchitecturePlannerService
from backend.app.services.catalog_ingestion import CatalogIngestionService
from backend.app.services.ingestion import IngestionService
from backend.app.services.interview_service import InterviewService
from backend.app.services.search import SearchService
from backend.app.services.spec_ingestion import SpecIngestionService


@lru_cache
def get_ingestion_service() -> IngestionService:
    return IngestionService()


@lru_cache
def get_spec_ingestion_service() -> SpecIngestionService:
    return SpecIngestionService()


@lru_cache
def get_catalog_ingestion_service() -> CatalogIngestionService:
    return CatalogIngestionService()


@lru_cache
def get_interview_service() -> InterviewService:
    return InterviewService()


@lru_cache
def get_planner_service() -> ArchitecturePlannerService:
    return ArchitecturePlannerService()


@lru_cache
def get_search_service() -> SearchService:
    return SearchService()
