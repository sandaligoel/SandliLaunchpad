"""Load pre-structured catalog JSON (no LLM extraction or chunking)."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from pydantic import ValidationError

from schemas.agent_record import (
    AgentRecord,
    ProjectRecord,
    normalize_vertical,
    slugify,
)

logger = logging.getLogger(__name__)


def _parse_project(raw: dict, source_page: int = 1) -> ProjectRecord:
    name = raw.get("name") or "unknown-project"
    return ProjectRecord(
        id=slugify(name),
        name=name,
        client=raw.get("client") or "",
        vertical=normalize_vertical(raw.get("vertical")),
        business_problem=raw.get("business_problem") or "",
        solution_summary=raw.get("solution_summary") or "",
        agents_used=raw.get("agents_used") or [],
        tech_stack=raw.get("tech_stack") or [],
        outcomes=raw.get("outcomes"),
        source_page=source_page,
    )


def _parse_agent(item: dict, source_page: int = 1) -> AgentRecord:
    name = item.get("name") or "unknown-agent"
    version = item.get("version") or "1.0"
    agent_id = slugify(name)
    if version and version != "1.0":
        agent_id = f"{agent_id}-v{version.replace('.', '-')}"

    return AgentRecord(
        id=agent_id,
        name=name,
        version=version,
        category=item["category"],
        function_summary=item.get("function_summary") or "",
        inputs=item.get("inputs") or [],
        outputs=item.get("outputs") or [],
        model_used=item.get("model_used") or "Unknown",
        tech_stack=item.get("tech_stack") or [],
        integrations=item.get("integrations") or [],
        origin_project=item.get("origin_project") or "",
        origin_client=item.get("origin_client") or "",
        vertical=normalize_vertical(item.get("vertical")),
        status=item.get("status") or "available",
        typical_accuracy=item.get("typical_accuracy"),
        notes=item.get("notes"),
        source_page=int(item.get("source_page", source_page)),
    )


def load_catalog_json(path: str | Path) -> tuple[ProjectRecord | None, list[AgentRecord]]:
    """
    Load project + agents from a catalog JSON file.

    Expected shape: { "project": { ... }, "agents": [ ... ] }

    Raises:
        FileNotFoundError, json.JSONDecodeError, ValidationError, ValueError
    """
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"Catalog file not found: {file_path}")

    data = json.loads(file_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Catalog JSON must be a top-level object")

    project: ProjectRecord | None = None
    if isinstance(data.get("project"), dict):
        project = _parse_project(data["project"])

    agents: list[AgentRecord] = []
    raw_agents = data.get("agents")
    if not isinstance(raw_agents, list):
        raise ValueError("Catalog JSON must include an 'agents' array")

    errors: list[str] = []
    for i, item in enumerate(raw_agents):
        if not isinstance(item, dict):
            continue
        try:
            agents.append(_parse_agent(item))
        except (ValidationError, KeyError) as exc:
            errors.append(f"agents[{i}]: {exc}")

    if errors:
        logger.warning("Skipped %d invalid agent(s): %s", len(errors), errors[:3])

    logger.info(
        "Loaded catalog from %s: project=%s, agents=%d",
        file_path.name,
        project.name if project else "(none)",
        len(agents),
    )
    return project, agents
