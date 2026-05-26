"""Load pre-structured catalog JSON (no LLM extraction or chunking)."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

from pydantic import ValidationError

from schemas.agent_record import (
    AgentRecord,
    ProjectRecord,
    normalize_vertical,
    slugify,
)

logger = logging.getLogger(__name__)


@dataclass
class CatalogLoadResult:
    """Agents and projects loaded from a catalog JSON file."""

    projects: list[ProjectRecord] = field(default_factory=list)
    agents: list[AgentRecord] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def project(self) -> ProjectRecord | None:
        """First project, for backward-compatible callers."""
        return self.projects[0] if self.projects else None


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


def _normalize_entries(data: object) -> list[dict]:
    """
    Accept catalog JSON as either:

    - Array of ``{ "project": {...}, "agents": [...] }`` (multi-project catalog)
    - Single object ``{ "project": {...}, "agents": [...] }`` (legacy)
    """
    if isinstance(data, list):
        entries = []
        for i, item in enumerate(data):
            if not isinstance(item, dict):
                raise ValueError(f"Catalog entry[{i}] must be an object")
            entries.append(item)
        return entries

    if isinstance(data, dict):
        if "agents" in data or "project" in data:
            return [data]
        raise ValueError(
            "Catalog JSON object must include 'agents' and/or 'project' keys"
        )

    raise ValueError(
        "Catalog JSON must be a top-level array of project entries or a single object"
    )


def _ensure_unique_agent_ids(agents: list[AgentRecord]) -> list[AgentRecord]:
    """Disambiguate duplicate slugs across projects (same agent name in multiple entries)."""
    used: set[str] = set()
    result: list[AgentRecord] = []
    for agent in agents:
        agent_id = agent.id
        if agent_id not in used:
            used.add(agent_id)
            result.append(agent)
            continue
        suffix = slugify(agent.origin_project or agent.origin_client or "project")
        disambiguated = f"{agent_id}-{suffix}"
        counter = 2
        while disambiguated in used:
            disambiguated = f"{agent_id}-{suffix}-{counter}"
            counter += 1
        used.add(disambiguated)
        logger.info(
            "Disambiguated agent id %s → %s (project %s)",
            agent_id,
            disambiguated,
            agent.origin_project,
        )
        result.append(agent.model_copy(update={"id": disambiguated}))
    return result


def _load_entry(
    entry: dict,
    entry_index: int,
) -> tuple[ProjectRecord | None, list[AgentRecord], list[str]]:
    """Load one project + agents block from the catalog."""
    errors: list[str] = []
    project: ProjectRecord | None = None
    source_page = entry_index + 1

    if isinstance(entry.get("project"), dict):
        try:
            project = _parse_project(entry["project"], source_page=source_page)
        except (ValidationError, KeyError) as exc:
            errors.append(f"entry[{entry_index}].project: {exc}")

    agents: list[AgentRecord] = []
    raw_agents = entry.get("agents")
    if raw_agents is None:
        errors.append(f"entry[{entry_index}]: missing 'agents' array")
        return project, agents, errors

    if not isinstance(raw_agents, list):
        errors.append(f"entry[{entry_index}].agents: must be an array")
        return project, agents, errors

    for i, item in enumerate(raw_agents):
        if not isinstance(item, dict):
            continue
        try:
            agents.append(_parse_agent(item, source_page=source_page))
        except (ValidationError, KeyError) as exc:
            errors.append(f"entry[{entry_index}].agents[{i}]: {exc}")

    return project, agents, errors


def load_catalog_json(path: str | Path) -> CatalogLoadResult:
    """
    Load all projects and agents from a catalog JSON file.

    Supports:
    - Multi-project: ``[ { "project": {...}, "agents": [...] }, ... ]``
    - Legacy single: ``{ "project": {...}, "agents": [...] }``

    Raises:
        FileNotFoundError, json.JSONDecodeError, ValueError
    """
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"Catalog file not found: {file_path}")

    data = json.loads(file_path.read_text(encoding="utf-8"))
    entries = _normalize_entries(data)

    projects: list[ProjectRecord] = []
    all_agents: list[AgentRecord] = []
    all_errors: list[str] = []

    for idx, entry in enumerate(entries):
        project, agents, errors = _load_entry(entry, idx)
        all_errors.extend(errors)
        if project:
            projects.append(project)
        all_agents.extend(agents)

    if not all_agents:
        raise ValueError("Catalog JSON contains no valid agents")

    unique_agents = _ensure_unique_agent_ids(all_agents)

    if all_errors:
        logger.warning(
            "Skipped %d catalog parse issue(s): %s",
            len(all_errors),
            all_errors[:5],
        )

    logger.info(
        "Loaded catalog from %s: %d project(s), %d agent(s)",
        file_path.name,
        len(projects),
        len(unique_agents),
    )
    return CatalogLoadResult(
        projects=projects,
        agents=unique_agents,
        errors=all_errors,
    )


def load_catalog_json_legacy(path: str | Path) -> tuple[ProjectRecord | None, list[AgentRecord]]:
    """
    Backward-compatible loader returning (first_project, all_agents).

    Prefer :func:`load_catalog_json` for multi-project catalogs.
    """
    result = load_catalog_json(path)
    return result.project, result.agents
