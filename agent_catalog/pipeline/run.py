"""Orchestrate the agent catalog build: load whole JSON spec, embed, index."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import typer

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from config import configure_logging, get_settings
from pipeline.embedder import compute_embeddings
from pipeline.indexer import index_agents
from pipeline.spec_loader import load_catalog_json
from schemas.agent_record import AgentRecord
from scripts.create_index import create_index, index_exists

logger = logging.getLogger(__name__)

app = typer.Typer(
    help="Affine Agent Catalog — load spec.json as a whole file (no chunking)"
)


def _dedupe_agents(agents: list[AgentRecord]) -> list[AgentRecord]:
    by_id: dict[str, AgentRecord] = {}
    for agent in agents:
        by_id[agent.id] = agent
    return list(by_id.values())


def _print_summary(
    agents: int,
    indexed: int,
    index_failures: int,
    project_name: str | None,
) -> None:
    lines = [
        "┌─────────────────────────────────┐",
        "│  Affine Agent Catalog — Built   │",
        "├─────────────────────────────────┤",
        f"│  Source:             JSON      │",
        f"│  Project:            {(project_name or '—')[:10]:<10}│",
        f"│  Agents loaded:      {agents:<10}│",
        f"│  Agents indexed:     {indexed:<10}│",
        f"│  Index failures:     {index_failures:<10}│",
        "└─────────────────────────────────┘",
    ]
    for line in lines:
        logger.info(line)


def run_pipeline(json_path: str) -> None:
    """
    Load the full catalog JSON, embed each agent, upload to Azure AI Search.

    No chunking, no LLM extraction, no search ranking — one file in, N agents indexed.
    """
    settings = get_settings()
    configure_logging(settings.log_level)
    settings.print_masked_summary()

    path = Path(json_path)
    if not path.exists():
        raise typer.BadParameter(f"File not found: {json_path}")
    if path.suffix.lower() != ".json":
        raise typer.BadParameter(
            f"Expected a .json catalog file, got '{path.suffix}'. "
            "Put your full spec in data/spec.json and point PDF_PATH (or --source) at it."
        )

    if not index_exists(settings):
        logger.info("Search index not found — creating index")
        create_index(settings)
    else:
        logger.info("Search index '%s' exists", settings.azure_search_index_name)

    project, agents = load_catalog_json(path)
    unique_agents = _dedupe_agents(agents)

    if project:
        logger.info("Loaded project: %s", project.name)
    logger.info("Indexing %d agents from %s (whole file, no chunks)", len(unique_agents), path.name)

    compute_embeddings(unique_agents, settings)
    index_result = index_agents(unique_agents, settings)

    _print_summary(
        agents=len(unique_agents),
        indexed=index_result.succeeded,
        index_failures=index_result.failed,
        project_name=project.name if project else None,
    )


@app.command()
def main(
    source: str = typer.Option(
        None,
        "--source",
        help="Path to catalog JSON (default: PDF_PATH from .env, e.g. ./data/spec.json)",
    ),
) -> None:
    """Ingest spec.json and index all agents."""
    settings = get_settings()
    run_pipeline(source or settings.pdf_path)


if __name__ == "__main__":
    app()
