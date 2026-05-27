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
    projects: int,
    agents: int,
    indexed: int,
    index_failures: int,
    project_names: list[str],
) -> None:
    preview = ", ".join(project_names[:3])
    if len(project_names) > 3:
        preview += f" (+{len(project_names) - 3} more)"
    lines = [
        "┌─────────────────────────────────┐",
        "│  Affine Agent Catalog — Built   │",
        "├─────────────────────────────────┤",
        f"│  Source:             JSON      │",
        f"│  Projects loaded:    {projects:<10}│",
        f"│  Agents loaded:      {agents:<10}│",
        f"│  Agents indexed:     {indexed:<10}│",
        f"│  Index failures:     {index_failures:<10}│",
        "└─────────────────────────────────┘",
    ]
    for line in lines:
        logger.info(line)
    if preview:
        logger.info("  Projects: %s", preview)


def run_pipeline(json_path: str) -> None:
    """
    Load the full catalog JSON, embed each agent, upload to Azure AI Search.

    No chunking, no LLM extraction — one file in, all agents indexed.
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
            "Put your catalog in data/spec.json and point PDF_PATH (or --source) at it."
        )

    if not index_exists(settings):
        logger.info("Search index not found — creating index")
        create_index(settings)
    else:
        logger.info("Search index '%s' exists", settings.azure_search_index_name)

    catalog = load_catalog_json(path)
    unique_agents = _dedupe_agents(catalog.agents)

    for project in catalog.projects:
        logger.info("  • %s (%s) — %s", project.name, project.client, project.vertical)

    if catalog.errors:
        logger.warning("%d parse warning(s) while loading catalog", len(catalog.errors))

    logger.info(
        "Indexing %d agents from %s (%d project block(s))",
        len(unique_agents),
        path.name,
        len(catalog.projects),
    )

    compute_embeddings(unique_agents, settings)
    index_result = index_agents(unique_agents, settings)

    _print_summary(
        projects=len(catalog.projects),
        agents=len(unique_agents),
        indexed=index_result.succeeded,
        index_failures=index_result.failed,
        project_names=[p.name for p in catalog.projects],
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
