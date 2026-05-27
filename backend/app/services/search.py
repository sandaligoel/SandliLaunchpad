"""Hybrid and semantic search over Azure AI Search."""

from __future__ import annotations

import json
import uuid

from azure.search.documents.models import QueryType

from backend.app.core.config import get_settings
from backend.app.core.logging import get_logger
from backend.app.embeddings.azure_embeddings import AzureEmbeddingService
from backend.app.schemas.search import (
    AgentSearchRequest,
    ArchitectureSearchRequest,
    EntityType,
    SearchHit,
    SearchMode,
    SearchRequest,
    SearchResponse,
)
from backend.app.search.index_manager import IndexManager
from backend.app.search.query_builder import QueryBuilder

logger = get_logger(__name__)


class SearchService:
    """Executes vector, keyword, and hybrid retrieval."""

    def __init__(
        self,
        index_manager: IndexManager | None = None,
        embedding_service: AzureEmbeddingService | None = None,
    ) -> None:
        self.settings = get_settings()
        self.index_manager = index_manager or IndexManager()
        self.embeddings = embedding_service or AzureEmbeddingService()
        self.client = self.index_manager.get_search_client()
        self.semantic_config = self.settings.azure_search_semantic_config_name

    async def search(self, request: SearchRequest) -> SearchResponse:
        cid = str(uuid.uuid4())
        odata_filter = QueryBuilder.build_filter(request.filters)
        return await self._execute(
            query=request.query,
            top_k=request.top_k,
            mode=request.mode,
            odata_filter=odata_filter,
            include_payload=request.include_structured_payload,
            correlation_id=cid,
        )

    async def search_agents(self, request: AgentSearchRequest) -> SearchResponse:
        cid = str(uuid.uuid4())
        odata_filter = QueryBuilder.agent_filter_extras(
            request.filters,
            request.agent_name_contains,
            request.tools_used,
        )
        return await self._execute(
            query=request.query,
            top_k=request.top_k,
            mode=request.mode,
            odata_filter=odata_filter,
            include_payload=request.include_structured_payload,
            correlation_id=cid,
            boost_agent=True,
        )

    async def search_architectures(
        self, request: ArchitectureSearchRequest
    ) -> SearchResponse:
        cid = str(uuid.uuid4())
        odata_filter = QueryBuilder.architecture_filter_extras(
            request.filters,
            request.architecture_pattern,
            request.orchestration_framework,
        )
        return await self._execute(
            query=request.query,
            top_k=request.top_k,
            mode=request.mode,
            odata_filter=odata_filter,
            include_payload=request.include_structured_payload,
            correlation_id=cid,
        )

    async def _execute(
        self,
        query: str,
        top_k: int,
        mode: SearchMode,
        odata_filter: str | None,
        include_payload: bool,
        correlation_id: str,
        boost_agent: bool = False,
    ) -> SearchResponse:
        select = QueryBuilder.select_fields(include_payload)
        search_text = query if mode != SearchMode.SEMANTIC else None
        if mode == SearchMode.KEYWORD:
            vector_queries = None
            query_type = QueryType.SIMPLE
        elif mode == SearchMode.SEMANTIC:
            vector = await self.embeddings.embed_text(query)
            vector_queries = [
                IndexManager.build_vector_query(vector, top_k)
            ]
            search_text = query
            query_type = QueryType.SEMANTIC
        else:
            vector = await self.embeddings.embed_text(query)
            vector_queries = [
                IndexManager.build_vector_query(vector, top_k)
            ]
            search_text = query
            query_type = QueryType.SIMPLE

        search_fields = ["content", "title", "agent_name", "agent_purpose"]
        if boost_agent:
            search_fields = ["agent_name", "agent_purpose", "content", "capabilities"]

        kwargs: dict = {
            "search_text": search_text,
            "filter": odata_filter,
            "top": top_k,
            "select": select,
            "search_fields": search_fields,
        }

        if vector_queries:
            kwargs["vector_queries"] = vector_queries

        if query_type == QueryType.SEMANTIC:
            kwargs["query_type"] = QueryType.SEMANTIC
            kwargs["semantic_configuration_name"] = self.semantic_config

        results_iter = self.client.search(**kwargs)
        hits: list[SearchHit] = []
        for result in results_iter:
            payload = None
            if include_payload and result.get("structured_payload"):
                try:
                    payload = json.loads(result["structured_payload"])
                except json.JSONDecodeError:
                    payload = {"raw": result["structured_payload"]}

            hits.append(
                SearchHit(
                    id=result["id"],
                    entity_type=EntityType(result.get("entity_type", "chunk")),
                    project_id=result.get("project_id", ""),
                    project_name=result.get("project_name", ""),
                    title=result.get("title", ""),
                    content=(result.get("content") or "")[:2000],
                    score=float(result.get("@search.score", 0.0)),
                    agent_name=result.get("agent_name", ""),
                    architecture_pattern=result.get("architecture_pattern", ""),
                    cloud_provider=result.get("cloud_provider", ""),
                    tech_stack=result.get("tech_stack") or [],
                    models_used=result.get("models_used") or [],
                    confidence_score=float(result.get("confidence_score", 0.0)),
                    structured_payload=payload,
                )
            )

        logger.info(
            "search_completed",
            correlation_id=correlation_id,
            mode=mode.value,
            results=len(hits),
        )

        return SearchResponse(
            query=query,
            mode=mode,
            total_results=len(hits),
            results=hits,
            correlation_id=correlation_id,
        )
