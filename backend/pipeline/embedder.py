"""Compute vector embeddings for agent records via Azure OpenAI."""

from __future__ import annotations

import logging
import time

from openai import AzureOpenAI

from config import EMBEDDING_DIMENSIONS, Settings
from schemas.agent_record import AgentRecord

logger = logging.getLogger(__name__)

BATCH_SIZE = 16
BATCH_SLEEP_SECONDS = 1


def _build_embed_text(record: AgentRecord) -> str:
    """Construct the text blob to embed for a single agent record."""
    return f"""
Agent: {record.name}
Function: {record.function_summary}
Inputs: {', '.join(record.inputs)}
Outputs: {', '.join(record.outputs)}
Category: {record.category}
Integrations: {', '.join(record.integrations)}
Tech: {', '.join(record.tech_stack)}
""".strip()


def embed_query(
    query: str,
    settings: Settings,
    client: AzureOpenAI | None = None,
) -> list[float]:
    """
    Embed a search query string for vector search.

    Args:
        query: Natural language search query.
        settings: Application settings.
        client: Optional pre-configured Azure OpenAI client.

    Returns:
        Embedding vector (dimension count from config.EMBEDDING_DIMENSIONS).

    Side effects:
        One Azure OpenAI embeddings API call.
    """
    if client is None:
        client = AzureOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            api_version=settings.azure_openai_api_version,
        )

    response = client.embeddings.create(
        input=query,
        model=settings.azure_openai_embedding_deployment,
        dimensions=EMBEDDING_DIMENSIONS,
    )
    return response.data[0].embedding


def compute_embeddings(
    records: list[AgentRecord],
    settings: Settings,
    client: AzureOpenAI | None = None,
) -> list[AgentRecord]:
    """
    Compute and attach embeddings to each AgentRecord.

    Args:
        records: Agent records without embeddings.
        settings: Application settings.
        client: Optional pre-configured Azure OpenAI client.

    Returns:
        Same records with embedding field populated.

    Side effects:
        Azure OpenAI embeddings API calls in batches of 16 with 1s pause between batches.
    """
    if not records:
        return records

    if client is None:
        client = AzureOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            api_version=settings.azure_openai_api_version,
        )

    total_batches = (len(records) + BATCH_SIZE - 1) // BATCH_SIZE
    logger.info("Embedding %d agents in %d batches", len(records), total_batches)

    for batch_idx in range(0, len(records), BATCH_SIZE):
        batch = records[batch_idx : batch_idx + BATCH_SIZE]
        texts = [_build_embed_text(r) for r in batch]

        response = client.embeddings.create(
            input=texts,
            model=settings.azure_openai_embedding_deployment,
            dimensions=EMBEDDING_DIMENSIONS,
        )

        for record, item in zip(batch, response.data):
            record.embedding = item.embedding

        batch_num = batch_idx // BATCH_SIZE + 1
        if batch_num < total_batches:
            time.sleep(BATCH_SLEEP_SECONDS)

        logger.info(
            "Embedded batch %d/%d (%d agents)",
            batch_num,
            total_batches,
            len(batch),
        )

    return records
