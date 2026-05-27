"""Index agent records into Azure AI Search and run hybrid queries."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery

from config import Settings
from pipeline.embedder import embed_query
from schemas.agent_record import AgentRecord

logger = logging.getLogger(__name__)

BATCH_SIZE = 50


@dataclass
class IndexResult:
    """Summary of a bulk index operation."""

    total: int = 0
    succeeded: int = 0
    failed: int = 0
    errors: list[str] = field(default_factory=list)


def _get_search_client(settings: Settings) -> SearchClient:
    """Create an Azure AI Search client for the agent catalog index."""
    return SearchClient(
        endpoint=settings.azure_search_endpoint,
        index_name=settings.azure_search_index_name,
        credential=AzureKeyCredential(settings.azure_search_api_key),
    )


def _record_to_document(record: AgentRecord) -> dict:
    """Serialize an AgentRecord to an Azure AI Search document."""
    return {
        "id": record.id,
        "name": record.name,
        "function_summary": record.function_summary,
        "version": record.version,
        "category": record.category,
        "vertical": record.vertical,
        "status": record.status,
        "origin_client": record.origin_client,
        "origin_project": record.origin_project,
        "inputs_text": ", ".join(record.inputs),
        "outputs_text": ", ".join(record.outputs),
        "tech_stack_text": ", ".join(record.tech_stack),
        "integrations_text": ", ".join(record.integrations),
        "model_used": record.model_used,
        "typical_accuracy": record.typical_accuracy or "",
        "notes": record.notes or "",
        "source_page": record.source_page,
        "embedding": record.embedding,
    }


def index_agents(
    records: list[AgentRecord],
    settings: Settings,
) -> IndexResult:
    """
    Upload or merge agent records into Azure AI Search.

    Args:
        records: Agent records with embeddings populated.
        settings: Application settings.

    Returns:
        IndexResult with success and failure counts.

    Side effects:
        Writes documents to Azure AI Search via merge_or_upload_documents (idempotent).
    """
    if not records:
        logger.warning("No records to index")
        return IndexResult()

    client = _get_search_client(settings)
    result = IndexResult(total=len(records))
    errors: list[str] = []

    for batch_start in range(0, len(records), BATCH_SIZE):
        batch = records[batch_start : batch_start + BATCH_SIZE]
        documents = [_record_to_document(r) for r in batch]

        upload_result = client.merge_or_upload_documents(documents=documents)
        for item in upload_result:
            if item.succeeded:
                result.succeeded += 1
            else:
                result.failed += 1
                err_msg = (
                    f"Failed to index document {item.key}: "
                    f"{item.error_message}"
                )
                errors.append(err_msg)
                logger.error(err_msg)

    result.errors = errors
    logger.info(
        "Indexing complete: %d succeeded, %d failed of %d total",
        result.succeeded,
        result.failed,
        result.total,
    )
    return result


def _search_agents_vector(
    client: SearchClient,
    query: str,
    query_vector: list[float],
    top_k: int,
) -> list[dict]:
    """Keyword + vector search without semantic ranker."""
    vector_query = VectorizedQuery(
        vector=query_vector,
        k_nearest_neighbors=top_k,
        fields="embedding",
    )
    results = client.search(
        search_text=query,
        vector_queries=[vector_query],
        top=top_k,
        select=[
            "id",
            "name",
            "function_summary",
            "category",
            "status",
            "origin_client",
            "origin_project",
            "version",
        ],
    )
    output: list[dict] = []
    for result in results:
        doc = dict(result)
        doc["score"] = result.get("@search.score", 0.0)
        output.append(doc)
    return output


def search_agents(
    query: str,
    settings: Settings,
    top_k: int = 5,
) -> list[dict]:
    """
    Run hybrid (keyword + vector + semantic) search against the agent catalog.

    Args:
        query: Natural language search query.
        settings: Application settings.
        top_k: Maximum number of results to return.

    Returns:
        List of result dicts with id, name, function_summary, category, status,
        origin_client, version, and search score.

    Side effects:
        Azure OpenAI embedding call plus Azure AI Search query.
    """
    from azure.search.documents.models import QueryType

    client = _get_search_client(settings)
    query_vector = embed_query(query, settings)

    vector_query = VectorizedQuery(
        vector=query_vector,
        k_nearest_neighbors=top_k,
        fields="embedding",
    )

    select = [
        "id",
        "name",
        "function_summary",
        "category",
        "status",
        "origin_client",
        "origin_project",
        "version",
    ]

    try:
        results = client.search(
            search_text=query,
            vector_queries=[vector_query],
            query_type=QueryType.SEMANTIC,
            semantic_configuration_name="affine-semantic",
            top=top_k,
            select=select,
        )
        output: list[dict] = []
        for result in results:
            doc = dict(result)
            doc["score"] = result.get("@search.score", 0.0)
            output.append(doc)
        return output
    except Exception as exc:
        logger.warning("Semantic search failed, falling back to vector+keyword: %s", exc)
        return _search_agents_vector(client, query, query_vector, top_k)
