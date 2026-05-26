"""Phase 1 catalog search to ground Phase 2 interviews."""

from __future__ import annotations

import logging

from config import Settings
from schemas.architecture_spec import CatalogHint

logger = logging.getLogger(__name__)


def fetch_catalog_hints(
    query: str,
    settings: Settings,
    *,
    top_k: int = 5,
) -> list[CatalogHint]:
    """
    Search the Affine agent catalog for records similar to the problem statement.

    Args:
        query: Problem statement or use-case text.
        settings: Azure configuration.
        top_k: Maximum agents to return.

    Returns:
        CatalogHint list; empty if search is unavailable or fails.

    Side effects:
        Azure OpenAI embedding + Azure AI Search hybrid query when configured.
    """
    text = (query or "").strip()
    if len(text) < 20:
        return []

    try:
        from pipeline.indexer import search_agents

        results = search_agents(text[:800], settings, top_k=top_k)
    except Exception as exc:
        logger.warning("Catalog hint search skipped: %s", exc)
        return []

    hints: list[CatalogHint] = []
    for row in results:
        score = float(row.get("score") or 0.0)
        hints.append(
            CatalogHint(
                agent_id=str(row.get("id") or ""),
                name=str(row.get("name") or "Unknown"),
                category=str(row.get("category") or ""),
                origin_client=str(row.get("origin_client") or ""),
                function_summary=str(row.get("function_summary") or "")[:240],
                score=score,
            )
        )

    logger.info("Catalog hints: %d agents for query (%d chars)", len(hints), len(text))
    return hints
