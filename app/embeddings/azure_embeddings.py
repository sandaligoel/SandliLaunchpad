"""Azure OpenAI embedding provider with batching."""

from __future__ import annotations

import asyncio

from openai import AsyncAzureOpenAI

from app.core.config import get_settings
from app.core.exceptions import ConfigurationError, EmbeddingError
from app.core.logging import get_logger
from app.core.retry import embedding_retry
from app.utils.text import truncate_for_embedding

logger = get_logger(__name__)


class AzureEmbeddingService:
    """Generates embeddings via Azure OpenAI deployment."""

    def __init__(self) -> None:
        settings = get_settings()
        if not settings.azure_openai_endpoint or not settings.azure_openai_api_key:
            raise ConfigurationError("Azure OpenAI credentials required for embeddings")
        self.settings = settings
        self.client = AsyncAzureOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            api_version=settings.azure_openai_api_version,
        )
        self.deployment = settings.azure_openai_embedding_deployment
        self.dimensions = settings.azure_openai_embedding_dimensions
        self.batch_size = settings.embedding_batch_size

    async def embed_text(self, text: str) -> list[float]:
        vectors = await self.embed_batch([text])
        return vectors[0]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        truncated = [truncate_for_embedding(t) for t in texts]
        all_vectors: list[list[float]] = []
        for i in range(0, len(truncated), self.batch_size):
            batch = truncated[i : i + self.batch_size]
            batch_vectors = await self._embed_batch_with_retry(batch)
            all_vectors.extend(batch_vectors)
        return all_vectors

    @embedding_retry()
    async def _embed_batch_with_retry(self, texts: list[str]) -> list[list[float]]:
        try:
            kwargs: dict = {
                "model": self.deployment,
                "input": texts,
            }
            if self.dimensions:
                kwargs["dimensions"] = self.dimensions
            response = await self.client.embeddings.create(**kwargs)
            sorted_data = sorted(response.data, key=lambda x: x.index)
            return [item.embedding for item in sorted_data]
        except Exception as e:
            raise EmbeddingError(
                "Embedding batch failed",
                {"count": len(texts), "error": str(e)},
            ) from e

    async def embed_batch_concurrent(
        self,
        texts: list[str],
        concurrency: int = 3,
    ) -> list[list[float]]:
        batches = [
            texts[i : i + self.batch_size]
            for i in range(0, len(texts), self.batch_size)
        ]
        semaphore = asyncio.Semaphore(concurrency)
        results: list[list[float]] = []

        async def run_batch(batch: list[str]) -> list[list[float]]:
            async with semaphore:
                return await self._embed_batch_with_retry(batch)

        batch_results = await asyncio.gather(*(run_batch(b) for b in batches))
        for br in batch_results:
            results.extend(br)
        return results
