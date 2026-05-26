"""Ground Phase 2 interview questions in agents from data/spec.json."""

from __future__ import annotations

import logging
import re
from pathlib import Path

from config import Settings
from pipeline.spec_loader import load_catalog_json
from schemas.agent_record import AgentRecord, slugify
from schemas.architecture_spec import CatalogHint
from services.catalog_hints import fetch_catalog_hints

logger = logging.getLogger(__name__)

_TOKEN_RE = re.compile(r"[a-z0-9]{3,}")


def _catalog_path(settings: Settings) -> Path:
    return Path(settings.pdf_path).expanduser()


def load_all_catalog_agents(settings: Settings) -> list[AgentRecord]:
    """All agents from data/spec.json for Agent Library API."""
    agents = _load_spec_agents(settings)
    return sorted(agents, key=lambda a: (a.category, a.name.lower()))


def _load_spec_agents(settings: Settings) -> list[AgentRecord]:
    path = _catalog_path(settings)
    if not path.is_file() or path.suffix.lower() != ".json":
        return []
    try:
        return load_catalog_json(path).agents
    except Exception as exc:
        logger.warning("Could not load spec.json for interview context: %s", exc)
        return []


def _tokens(text: str) -> set[str]:
    return set(_TOKEN_RE.findall((text or "").lower()))


def _keyword_score(query: str, agent: AgentRecord) -> float:
    q = _tokens(query)
    if not q:
        return 0.0
    blob = " ".join(
        [
            agent.name,
            agent.category,
            agent.function_summary,
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
    return overlap / max(len(q), 1)


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
    top_k: int = 8,
) -> list[CatalogHint]:
    """
    Hybrid catalog context: Azure Search when available, always enriched from spec.json.
    """
    text = (query or "").strip()
    all_agents = _load_spec_agents(settings)
    by_id = _agent_by_id(all_agents)

    search_hints = fetch_catalog_hints(text, settings, top_k=top_k) if len(text) >= 20 else []

    merged: list[CatalogHint] = []
    seen: set[str] = set()

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
            if kw_score < 0.08:
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


def format_catalog_for_interview_prompt(hints: list[CatalogHint]) -> str:
    """Rich block for LLM prompts — keeps spec.json agents in mind."""
    if not hints:
        return (
            "(No agents loaded from catalog — ensure data/spec.json exists and "
            "run pipeline.run to index for search.)"
        )

    lines = [
        "AFFINE BUILT AGENTS (data/spec.json). Prefer reuse; name these in questions and chips when relevant.",
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
