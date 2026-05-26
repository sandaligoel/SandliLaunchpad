"""Azure AI Search index definition and lifecycle management."""

from __future__ import annotations

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    HnswAlgorithmConfiguration,
    HnswParameters,
    SearchableField,
    SearchField,
    SearchFieldDataType,
    SearchIndex,
    SemanticConfiguration,
    SemanticField,
    SemanticPrioritizedFields,
    SemanticSearch,
    SimpleField,
    VectorSearch,
    VectorSearchProfile,
)
from azure.search.documents.models import VectorizedQuery

from app.core.config import get_settings
from app.core.exceptions import ConfigurationError, SearchIndexError
from app.core.logging import get_logger
from app.schemas.search import SearchDocument

logger = get_logger(__name__)


class IndexManager:
    """Creates and manages the Azure AI Search vector index."""

    def __init__(self) -> None:
        settings = get_settings()
        if not settings.azure_search_endpoint or not settings.azure_search_api_key:
            raise ConfigurationError(
                "Azure AI Search endpoint and API key required",
                {"vars": ["AZURE_SEARCH_ENDPOINT", "AZURE_SEARCH_API_KEY"]},
            )
        self.settings = settings
        self.credential = AzureKeyCredential(settings.azure_search_api_key)
        self.index_client = SearchIndexClient(
            endpoint=settings.azure_search_endpoint,
            credential=self.credential,
        )
        self._search_client: SearchClient | None = None

    @property
    def index_name(self) -> str:
        return self.settings.azure_search_index_name

    def get_search_client(self) -> SearchClient:
        if self._search_client is None:
            self._search_client = SearchClient(
                endpoint=self.settings.azure_search_endpoint,
                index_name=self.index_name,
                credential=self.credential,
            )
        return self._search_client

    def ensure_index_exists(self) -> None:
        try:
            self.index_client.get_index(self.index_name)
            logger.info("search_index_exists", index=self.index_name)
        except Exception:
            logger.info("creating_search_index", index=self.index_name)
            self._create_index()

    def _create_index(self) -> None:
        dim = self.settings.azure_openai_embedding_dimensions
        vector_search = VectorSearch(
            algorithms=[
                HnswAlgorithmConfiguration(
                    name="hnsw-cosine",
                    parameters=HnswParameters(
                        m=4,
                        ef_construction=400,
                        ef_search=500,
                        metric="cosine",
                    ),
                )
            ],
            profiles=[
                VectorSearchProfile(
                    name="vector-profile",
                    algorithm_configuration_name="hnsw-cosine",
                )
            ],
        )
        semantic_config = SemanticConfiguration(
            name=self.settings.azure_search_semantic_config_name,
            prioritized_fields=SemanticPrioritizedFields(
                title_field=SemanticField(field_name="title"),
                content_fields=[SemanticField(field_name="content")],
            ),
        )
        fields = [
            SimpleField(name="id", type=SearchFieldDataType.String, key=True),
            SearchableField(
                name="entity_type",
                type=SearchFieldDataType.String,
                filterable=True,
                facetable=True,
            ),
            SearchableField(
                name="project_id",
                type=SearchFieldDataType.String,
                filterable=True,
            ),
            SearchableField(
                name="project_name",
                type=SearchFieldDataType.String,
                filterable=True,
                facetable=True,
            ),
            SearchableField(
                name="industry",
                type=SearchFieldDataType.String,
                filterable=True,
                facetable=True,
            ),
            SearchableField(name="title", type=SearchFieldDataType.String),
            SearchableField(name="content", type=SearchFieldDataType.String),
            SearchField(
                name="content_vector",
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                searchable=True,
                vector_search_dimensions=dim,
                vector_search_profile_name="vector-profile",
            ),
            SearchableField(
                name="agent_name",
                type=SearchFieldDataType.String,
                filterable=True,
            ),
            SearchableField(name="agent_purpose", type=SearchFieldDataType.String),
            SearchableField(
                name="architecture_pattern",
                type=SearchFieldDataType.String,
                filterable=True,
                facetable=True,
            ),
            SearchableField(
                name="orchestration_framework",
                type=SearchFieldDataType.String,
                filterable=True,
                facetable=True,
            ),
            SearchableField(
                name="cloud_provider",
                type=SearchFieldDataType.String,
                filterable=True,
                facetable=True,
            ),
            SearchableField(
                name="deployment_model",
                type=SearchFieldDataType.String,
                filterable=True,
            ),
            SearchField(
                name="tech_stack",
                type=SearchFieldDataType.Collection(SearchFieldDataType.String),
                searchable=True,
                filterable=True,
                facetable=True,
            ),
            SearchField(
                name="models_used",
                type=SearchFieldDataType.Collection(SearchFieldDataType.String),
                searchable=True,
                filterable=True,
                facetable=True,
            ),
            SearchField(
                name="tools_used",
                type=SearchFieldDataType.Collection(SearchFieldDataType.String),
                searchable=True,
                filterable=True,
                facetable=True,
            ),
            SearchField(
                name="capabilities",
                type=SearchFieldDataType.Collection(SearchFieldDataType.String),
                searchable=True,
                filterable=True,
                facetable=True,
            ),
            SearchField(
                name="workflow_keywords",
                type=SearchFieldDataType.Collection(SearchFieldDataType.String),
                searchable=True,
                filterable=True,
            ),
            SimpleField(
                name="retrieval_used",
                type=SearchFieldDataType.Boolean,
                filterable=True,
            ),
            SearchableField(
                name="source_filename",
                type=SearchFieldDataType.String,
                filterable=True,
            ),
            SimpleField(
                name="source_page_start",
                type=SearchFieldDataType.Int32,
                filterable=True,
            ),
            SimpleField(
                name="source_page_end",
                type=SearchFieldDataType.Int32,
            ),
            SimpleField(
                name="confidence_score",
                type=SearchFieldDataType.Double,
                filterable=True,
            ),
            SimpleField(
                name="ingested_at",
                type=SearchFieldDataType.DateTimeOffset,
                filterable=True,
            ),
            SearchableField(
                name="structured_payload",
                type=SearchFieldDataType.String,
            ),
        ]
        index = SearchIndex(
            name=self.index_name,
            fields=fields,
            vector_search=vector_search,
            semantic_search=SemanticSearch(configurations=[semantic_config]),
        )
        try:
            self.index_client.create_or_update_index(index)
            logger.info("search_index_created", index=self.index_name, dimensions=dim)
        except Exception as e:
            raise SearchIndexError(
                f"Failed to create index {self.index_name}",
                {"error": str(e)},
            ) from e

    def upsert_documents(self, documents: list[SearchDocument], batch_size: int = 100) -> int:
        if not documents:
            return 0
        client = self.get_search_client()
        total_succeeded = 0
        errors: list[str] = []

        for i in range(0, len(documents), batch_size):
            batch = documents[i : i + batch_size]
            payload = [d.to_index_dict() for d in batch]
            try:
                result = client.upload_documents(documents=payload)
                for r in result:
                    if r.succeeded:
                        total_succeeded += 1
                    elif r.error_message:
                        errors.append(r.error_message)
            except Exception as e:
                raise SearchIndexError(
                    "Document upsert failed",
                    {
                        "count": len(batch),
                        "batch_start": i,
                        "error": str(e),
                        "prior_errors": errors[:3],
                    },
                ) from e

        if errors:
            logger.warning(
                "partial_index_failure",
                failed=len(errors),
                errors=errors[:5],
            )
            if total_succeeded == 0:
                raise SearchIndexError(
                    "All document upserts failed",
                    {"errors": errors[:5]},
                )
        return total_succeeded

    @staticmethod
    def build_vector_query(
        vector: list[float],
        k: int,
        fields: str = "content_vector",
    ) -> VectorizedQuery:
        return VectorizedQuery(
            vector=vector,
            k_nearest_neighbors=k,
            fields=fields,
        )
