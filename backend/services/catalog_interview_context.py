"""Ground Phase 2 interview questions in agents from data/spec.json."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

from config import Settings
from pipeline.spec_loader import CatalogLoadResult, load_catalog_json
from schemas.agent_record import AgentRecord, ProjectRecord, slugify
from schemas.architecture_spec import CatalogHint
from services.catalog_hints import fetch_catalog_hints

logger = logging.getLogger(__name__)

_TOKEN_RE = re.compile(r"[a-z0-9]{3,}")
_CATALOG_CACHE: dict[str, Any] = {
    "path": None,
    "mtime_ns": None,
    "result": CatalogLoadResult(),
}


def _catalog_path(settings: Settings) -> Path:
    return Path(settings.pdf_path).expanduser()


def load_all_catalog_agents(settings: Settings) -> list[AgentRecord]:
    """All agents from data/spec.json for Agent Library API."""
    agents = _load_spec_agents(settings)
    return sorted(agents, key=lambda a: (a.category, a.name.lower()))


def _load_catalog(settings: Settings) -> CatalogLoadResult:
    path = _catalog_path(settings)
    if not path.is_file() or path.suffix.lower() != ".json":
        return CatalogLoadResult()
    try:
        stat = path.stat()
        mtime_ns = int(getattr(stat, "st_mtime_ns", 0))
        cache_path = _CATALOG_CACHE.get("path")
        cache_mtime = _CATALOG_CACHE.get("mtime_ns")
        if cache_path == str(path) and cache_mtime == mtime_ns:
            cached = _CATALOG_CACHE.get("result")
            if isinstance(cached, CatalogLoadResult):
                return cached
    except Exception:
        # If stat fails unexpectedly, fall through to normal load.
        mtime_ns = None
    try:
        loaded = load_catalog_json(path)
        _CATALOG_CACHE["path"] = str(path)
        _CATALOG_CACHE["mtime_ns"] = mtime_ns
        _CATALOG_CACHE["result"] = loaded
        return loaded
    except Exception as exc:
        logger.warning("Could not load spec.json for interview context: %s", exc)
        return CatalogLoadResult()


def _load_spec_agents(settings: Settings) -> list[AgentRecord]:
    return _load_catalog(settings).agents


def _tokens(text: str) -> set[str]:
    return set(_TOKEN_RE.findall((text or "").lower()))


# Mars Sales Genie copilot trio — SQL (Quin) + semantic RAG (Eryl) + intent routing.
DATA_COPILOT_AGENT_IDS: tuple[str, ...] = (
    "pipeline-intent-classifier",
    "quin-sql-agent-chain",
    "eryl-semantic-rag-agent-chain",
)


def is_data_copilot_query(query: str) -> bool:
    """
    Bot/copilot problems over structured + unstructured data (e.g. saturated/unsaturated).
    Routes to Quin (SQL) and Eryl (RAG) from Mars Sales Genie.
    """
    q = (query or "").lower()
    has_bot = any(
        w in q
        for w in (
            "bot",
            "chatbot",
            "copilot",
            "assistant",
            "q&a",
            "question answering",
            "genie",
        )
    )
    has_data = any(
        w in q
        for w in (
            "data",
            "saturated",
            "unsaturated",
            "sql",
            "analytics",
            "structured",
            "unstructured",
            "semantic",
            "database",
            "metric",
            "inventory",
            "sales",
        )
    )
    return has_bot and has_data


def _copilot_routing_boost(query: str, agent: AgentRecord) -> float:
    if not is_data_copilot_query(query):
        return 0.0
    if agent.id in DATA_COPILOT_AGENT_IDS:
        return 0.9
    return 0.0


def pinned_copilot_agents(
    query: str,
    agents: list[AgentRecord],
) -> list[AgentRecord]:
    """Return Pipeline + Quin + Eryl in stable order when query is a data copilot."""
    if not is_data_copilot_query(query):
        return []
    by_id = _agent_by_id(agents)
    return [by_id[aid] for aid in DATA_COPILOT_AGENT_IDS if aid in by_id]


def _keyword_score(query: str, agent: AgentRecord) -> float:
    q = _tokens(query)
    if not q:
        return 0.0
    blob = " ".join(
        [
            agent.name,
            agent.category,
            agent.function_summary,
            agent.notes or "",
            agent.origin_project,
            agent.origin_client,
            " ".join(agent.integrations),
            " ".join(agent.tech_stack),
        ]
    ).lower()
    a = _tokens(blob)
    if not a:
        return 0.0
    overlap = len(q & a)
    base = overlap / max(len(q), 1)
    return min(1.0, base + _copilot_routing_boost(query, agent))


def _agent_by_id(agents: list[AgentRecord]) -> dict[str, AgentRecord]:
    by_id: dict[str, AgentRecord] = {}
    for a in agents:
        by_id[a.id] = a
        by_id[slugify(a.name)] = a
    return by_id


def _hint_from_agent(agent: AgentRecord, score: float) -> CatalogHint:
    integrations = ", ".join(agent.integrations[:6]) if agent.integrations else ""
    return CatalogHint(
        agent_id=agent.id,
        name=agent.name,
        category=agent.category,
        origin_client=agent.origin_client,
        function_summary=(agent.function_summary or "")[:400],
        score=score,
        origin_project=agent.origin_project or "",
        integrations=integrations,
        model_used=agent.model_used or "",
        status=agent.status or "available",
    )


def build_catalog_hints_for_interview(
    query: str,
    settings: Settings,
    *,
    top_k: int = 12,
    preferred_agent_ids: list[str] | None = None,
) -> list[CatalogHint]:
    """
    Hybrid catalog context: Azure Search when available, always enriched from spec.json.
    """
    text = (query or "").strip()
    all_agents = _load_spec_agents(settings)
    by_id = _agent_by_id(all_agents)
    preferred = set(preferred_agent_ids or [])

    merged: list[CatalogHint] = []
    seen: set[str] = set()

    for agent in pinned_copilot_agents(text, all_agents):
        if agent.id not in seen:
            seen.add(agent.id)
            merged.append(_hint_from_agent(agent, 0.96))

    for aid in preferred:
        agent = by_id.get(aid)
        if agent and agent.id not in seen:
            seen.add(agent.id)
            merged.append(_hint_from_agent(agent, 0.95))

    search_hints = fetch_catalog_hints(text, settings, top_k=top_k) if len(text) >= 20 else []

    for h in search_hints:
        key = h.agent_id or slugify(h.name)
        if key in seen:
            continue
        seen.add(key)
        full = by_id.get(h.agent_id) or by_id.get(slugify(h.name))
        if full:
            merged.append(_hint_from_agent(full, h.score))
        else:
            merged.append(h)

    if len(merged) < top_k and all_agents and text:
        ranked = sorted(
            ((a, _keyword_score(text, a)) for a in all_agents),
            key=lambda x: x[1],
            reverse=True,
        )
        for agent, kw_score in ranked:
            if agent.id in seen:
                continue
            if kw_score < 0.05:
                continue
            seen.add(agent.id)
            merged.append(_hint_from_agent(agent, min(0.75, kw_score)))
            if len(merged) >= top_k:
                break

    logger.info(
        "Interview catalog context: %d agents (search=%d, spec.json=%d)",
        len(merged),
        len(search_hints),
        len(all_agents),
    )
    return merged[:top_k]


def _project_score(query: str, project: ProjectRecord, agents: list[AgentRecord]) -> float:
    blob = " ".join(
        [
            project.name,
            project.client,
            project.business_problem,
            project.solution_summary,
            project.outcomes or "",
            " ".join(project.tech_stack),
        ]
    )
    for agent in agents:
        if agent.origin_project == project.name:
            blob += " " + " ".join(
                [
                    agent.name,
                    agent.function_summary,
                    " ".join(agent.integrations),
                ]
            )
    q = _tokens(query)
    p = _tokens(blob)
    if not q or not p:
        return 0.0
    return len(q & p) / max(len(q), 1)


def _truncate(text: str, limit: int) -> str:
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rsplit(" ", 1)[0] + "…"


def format_catalog_brief_for_interview(
    query: str,
    settings: Settings,
    *,
    top_projects: int = 2,
    agents_per_project: int = 8,
    preferred_agent_ids: list[str] | None = None,
) -> str:
    """
    Project-first catalog brief for catalog_pattern_interview.txt.

    Ranks spec.json projects by keyword fit, then lists agents in catalog order
    with inputs, outputs, and integrations.
    """
    catalog = _load_catalog(settings)
    if not catalog.projects and not catalog.agents:
        return format_catalog_for_interview_prompt([])

    preferred = set(preferred_agent_ids or [])
    agents_by_project: dict[str, list[AgentRecord]] = {}
    for agent in catalog.agents:
        key = agent.origin_project or "unknown"
        agents_by_project.setdefault(key, []).append(agent)

    entries: list[tuple[ProjectRecord, list[AgentRecord], float]] = []
    for project in catalog.projects:
        project_agents = agents_by_project.get(project.name, [])[:agents_per_project]
        if not project_agents:
            continue
        score = _project_score(query, project, project_agents)
        if preferred:
            score += 0.15 * sum(1 for a in project_agents if a.id in preferred)
        entries.append((project, project_agents, score))

    entries.sort(key=lambda x: x[2], reverse=True)
    top = entries[:top_projects]

    lines = ["REFERENCE PROJECTS (spec.json, ranked by fit):", ""]
    if not top:
        return format_catalog_for_interview_prompt(
            build_catalog_hints_for_interview(query, settings, top_k=12)
        )

    for rank, (project, agents, score) in enumerate(top, 1):
        lines.append(f"{rank}. {project.name} — {project.vertical}")
        if project.client:
            lines.append(f"   Client: {project.client}")
        lines.append(f"   Fit score: {score:.2f}")
        lines.append(
            f"   Problem: {_truncate(project.business_problem, 280)}"
        )
        lines.append(
            f"   Solution pattern: {_truncate(project.solution_summary, 320)}"
        )
        if project.outcomes:
            lines.append(f"   Outcomes: {_truncate(str(project.outcomes), 200)}")
        lines.append("   Agents (typical pipeline order):")
        for agent in agents:
            ins = ", ".join(agent.inputs[:4]) if agent.inputs else "—"
            outs = ", ".join(agent.outputs[:4]) if agent.outputs else "—"
            ints = ", ".join(agent.integrations[:5]) if agent.integrations else "—"
            lines.append(f"   - {agent.name} [{agent.category}] id={agent.id}")
            lines.append(f"     Does: {_truncate(agent.function_summary, 200)}")
            lines.append(f"     In: {_truncate(ins, 120)} | Out: {_truncate(outs, 120)}")
            lines.append(f"     Integrations: {_truncate(ints, 100)}")
            if agent.notes:
                lines.append(f"     Notes: {_truncate(agent.notes, 120)}")
        lines.append("")

    lines.append("USER PROBLEM (match patterns above):")
    lines.append(_truncate(query, 500))
    return "\n".join(lines).strip()


def _dedupe_preserve(items: list[str], limit: int = 24) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for raw in items:
        text = (raw or "").strip()
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(text)
        if len(out) >= limit:
            break
    return out


def format_matched_agents_context(
    hints: list[CatalogHint],
    settings: Settings,
) -> dict[str, str]:
    """
    Build placeholder values for catalog_pattern_interview.txt from catalog hints
    and full agent records in spec.json.
    """
    catalog = _load_catalog(settings)
    by_id = _agent_by_id(catalog.agents)

    matched: list[dict] = []
    all_inputs: list[str] = []
    all_outputs: list[str] = []
    tech: list[str] = []
    models: list[str] = []
    notes: list[str] = []

    for h in hints[:8]:
        agent = by_id.get(h.agent_id) or by_id.get(slugify(h.name))
        entry = {
            "agent_id": h.agent_id,
            "name": h.name,
            "category": h.category,
            "origin_project": h.origin_project or "",
            "origin_client": h.origin_client or "",
            "function_summary": (h.function_summary or "")[:320],
            "score": round(h.score, 3),
        }
        if agent:
            entry["inputs"] = agent.inputs[:6]
            entry["outputs"] = agent.outputs[:6]
            entry["integrations"] = agent.integrations[:6]
            entry["tech_stack"] = agent.tech_stack[:6]
            entry["model_used"] = agent.model_used or ""
            if agent.notes:
                entry["notes"] = agent.notes
            all_inputs.extend(agent.inputs)
            all_outputs.extend(agent.outputs)
            tech.extend(agent.integrations)
            tech.extend(agent.tech_stack)
            if agent.model_used and agent.model_used != "Unknown":
                models.append(f"{agent.name}: {agent.model_used}")
            if agent.notes:
                notes.append(f"{agent.name}: {agent.notes}")
        elif h.integrations:
            tech.extend([s.strip() for s in h.integrations.split(",") if s.strip()])
        if h.model_used:
            models.append(f"{h.name}: {h.model_used}")
        matched.append(entry)

    if not matched and hints:
        matched = [
            {
                "agent_id": h.agent_id,
                "name": h.name,
                "category": h.category,
                "function_summary": (h.function_summary or "")[:320],
                "score": round(h.score, 3),
            }
            for h in hints[:8]
        ]

    tech_deduped = _dedupe_preserve(tech, 20)
    return {
        "matched_agents_json": json.dumps(matched, indent=2) if matched else "[]",
        "inputs_from_matched_agents": ", ".join(_dedupe_preserve(all_inputs, 16))
        or "(none listed — infer from problem statement)",
        "outputs_from_matched_agents": ", ".join(_dedupe_preserve(all_outputs, 16))
        or "(none listed — infer from problem statement)",
        "tech_stack_and_integrations": ", ".join(tech_deduped)
        or "(none listed)",
        "model_breakdown": "; ".join(_dedupe_preserve(models, 10))
        or "(not specified in catalog)",
        "notes_from_matched_agents": "; ".join(_dedupe_preserve(notes, 8))
        or "(none)",
    }


def format_catalog_for_interview_prompt(hints: list[CatalogHint]) -> str:
    """Rich block for LLM prompts — keeps spec.json agents in mind."""
    if not hints:
        return (
            "(No agents loaded from catalog — ensure data/spec.json exists and "
            "run pipeline.run to index for search.)"
        )

    lines = [
        "AFFINE BUILT AGENTS (data/spec.json). Ground requirements and architecture questions in these capabilities; chips may reflect similar patterns without naming agents unless the user already did.",
        "",
    ]
    for i, h in enumerate(hints, 1):
        lines.append(f"{i}. {h.name} [{h.category}]")
        if h.origin_project or h.origin_client:
            lines.append(
                f"   Project: {h.origin_project or '—'} ({h.origin_client or 'Affine'})"
            )
        lines.append(f"   Does: {h.function_summary}")
        if h.integrations:
            lines.append(f"   Integrations: {h.integrations}")
        if h.model_used:
            lines.append(f"   Model: {h.model_used}")
        lines.append(f"   Relevance: {h.score:.2f}")
        lines.append("")
    return "\n".join(lines).strip()
