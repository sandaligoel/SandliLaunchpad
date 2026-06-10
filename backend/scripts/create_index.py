#!/usr/bin/env python3
"""One-time script to create the Azure AI Search index for the agent catalog."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

# Allow imports from backend root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import HttpResponseError, ResourceExistsError, ResourceNotFoundError
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
    VectorSearchAlgorithmMetric,
    VectorSearchProfile,
)

from server import EMBEDDING_DIMENSIONS, configure_logging, get_settings

logger = logging.getLogger(__name__)



def build_index_definition(index_name: str) -> SearchIndex:
    """
    Build the Azure AI Search index schema for agent records.

    Args:
        index_name: Name of the search index.

    Returns:
        SearchIndex model ready to create or update.
    """
    fields = [
        SimpleField(name="id", type="Edm.String", key=True, filterable=True),
        SearchableField(
            name="name", type="Edm.String", analyzer_name="en.lucene"
        ),
        SearchableField(
            name="function_summary",
            type="Edm.String",
            analyzer_name="en.lucene",
        ),
        SimpleField(name="version", type="Edm.String", filterable=True),
        SimpleField(
            name="category", type="Edm.String", filterable=True, facetable=True
        ),
        SimpleField(
            name="vertical", type="Edm.String", filterable=True, facetable=True
        ),
        SimpleField(
            name="status", type="Edm.String", filterable=True, facetable=True
        ),
        SimpleField(
            name="origin_client", type="Edm.String", filterable=True
        ),
        SimpleField(
            name="origin_project", type="Edm.String", filterable=True
        ),
        SearchableField(name="inputs_text", type="Edm.String"),
        SearchableField(name="outputs_text", type="Edm.String"),
        SearchableField(name="tech_stack_text", type="Edm.String"),
        SearchableField(name="integrations_text", type="Edm.String"),
        SimpleField(name="model_used", type="Edm.String", filterable=True),
        SimpleField(name="typical_accuracy", type="Edm.String"),
        SimpleField(name="notes", type="Edm.String"),
        SimpleField(name="source_page", type="Edm.Int32"),
        SearchField(
            name="embedding",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True,
            vector_search_dimensions=EMBEDDING_DIMENSIONS,
            vector_search_profile_name="affine-vector-profile",
        ),
    ]

    vector_search = VectorSearch(
        algorithms=[
            HnswAlgorithmConfiguration(
                name="affine-hnsw",
                parameters=HnswParameters(
                    m=4,
                    ef_construction=400,
                    ef_search=500,
                    metric=VectorSearchAlgorithmMetric.COSINE,
                ),
            )
        ],
        profiles=[
            VectorSearchProfile(
                name="affine-vector-profile",
                algorithm_configuration_name="affine-hnsw",
            )
        ],
    )

    semantic_config = SemanticSearch(
        configurations=[
            SemanticConfiguration(
                name="affine-semantic",
                prioritized_fields=SemanticPrioritizedFields(
                    content_fields=[
                        SemanticField(field_name="function_summary"),
                        SemanticField(field_name="name"),
                    ]
                ),
            )
        ]
    )

    return SearchIndex(
        name=index_name,
        fields=fields,
        vector_search=vector_search,
        semantic_search=semantic_config,
    )


def delete_index(settings=None) -> bool:
    """
    Delete the agent catalog search index if it exists.

    Returns:
        True if the index was deleted, False if it was not found.
    """
    if settings is None:
        settings = get_settings()

    index_client = SearchIndexClient(
        endpoint=settings.azure_search_endpoint,
        credential=AzureKeyCredential(settings.azure_search_api_key),
    )
    try:
        index_client.delete_index(settings.azure_search_index_name)
        logger.info("Deleted index '%s'", settings.azure_search_index_name)
        return True
    except ResourceNotFoundError:
        logger.info("Index '%s' not found — nothing to delete", settings.azure_search_index_name)
        return False


def create_index(settings=None) -> bool:
    """
    Create the agent catalog search index if it does not exist.

    Args:
        settings: Optional Settings instance; loaded from env if omitted.

    Returns:
        True if index was created, False if it already existed.

    Side effects:
        Creates index in Azure AI Search when missing.
    """
    if settings is None:
        settings = get_settings()

    index_client = SearchIndexClient(
        endpoint=settings.azure_search_endpoint,
        credential=AzureKeyCredential(settings.azure_search_api_key),
    )

    if index_exists(settings):
        logger.info("Index '%s' already exists", settings.azure_search_index_name)
        return False

    index_def = build_index_definition(settings.azure_search_index_name)

    try:
        index_client.create_index(index_def)
        logger.info(
            "Created index '%s' with %d fields",
            settings.azure_search_index_name,
            len(index_def.fields),
        )
        return True
    except ResourceExistsError:
        logger.info("Index '%s' already exists", settings.azure_search_index_name)
        return False
    except HttpResponseError as exc:
        if "already exists" in str(exc).lower():
            logger.info("Index '%s' already exists", settings.azure_search_index_name)
            return False
        raise


def index_exists(settings) -> bool:
    """Return True if the configured search index already exists."""
    index_client = SearchIndexClient(
        endpoint=settings.azure_search_endpoint,
        credential=AzureKeyCredential(settings.azure_search_api_key),
    )
    try:
        index_client.get_index(settings.azure_search_index_name)
        return True
    except Exception:
        return False


def main() -> None:
    """CLI entry point for index creation."""
    import argparse

    parser = argparse.ArgumentParser(description="Create the Azure AI Search index")
    parser.add_argument(
        "--recreate",
        action="store_true",
        help="Delete the index first, then create it (required after embedding dimension changes)",
    )
    args = parser.parse_args()

    settings = get_settings()
    configure_logging(settings.log_level)
    settings.print_masked_summary()
    if args.recreate:
        delete_index(settings)
    created = create_index(settings)
    if created:
        print(
            f"Successfully created index '{settings.azure_search_index_name}' "
            f"with {len(build_index_definition(settings.azure_search_index_name).fields)} fields"
        )
    else:
        print(f"Index '{settings.azure_search_index_name}' already exists — no changes made")


if __name__ == "__main__":
    main()
