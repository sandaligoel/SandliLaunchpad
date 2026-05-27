"""Phase 3: plan architecture graph with catalog reuse decisions."""

from __future__ import annotations

import json
import logging
import re
from typing import Optional

from openai import AzureOpenAI
from pydantic import ValidationError

from config import Settings
from pipeline.indexer import search_agents
from schemas.architecture_plan import (
    ArchitecturePlan,
    ArchitectureValidationReport,
    CatalogMatch,
    ReuseDecision,
)
from schemas.architecture_spec import (
    ArchitectureSpec,
    GraphDraft,
    GraphEdge,
    GraphNode,
    InterviewSession,
)
from services.architecture_validator import validate_architecture_plan
from services.graph_sanitizer import normalize_node_id, sanitize_graph
from services.llm import call_llm, load_prompt, make_client, strip_json_fences

logger = logging.getLogger(__name__)

MIN_SPEC_STATUS = ("sufficient", "ready")


def _field_value(spec: ArchitectureSpec, key: str) -> str:
    field = spec.fields.get(key)
    if field and field.is_known and field.value:
        return field.value.strip()
    return ""


def _enriched_problem_context(spec: ArchitectureSpec) -> str:
    """Problem statement plus clarifying summary — same signal as Phase 2 catalog hints."""
    parts: list[str] = []
    if spec.problem_statement.strip():
        parts.append(spec.problem_statement.strip())
    if spec.transcript_summary and spec.transcript_summary.strip():
        parts.append(spec.transcript_summary.strip())
    return "\n\n".join(parts)


def _build_search_queries(spec: ArchitectureSpec) -> list[str]:
    """Derive catalog search queries from confirmed spec fields."""
    queries: list[str] = []
    enriched = _enriched_problem_context(spec)
    if enriched:
        queries.append(enriched[:800])

    use_case = _field_value(spec, "use_case")
    if use_case:
        queries.append(use_case[:400])

    for key in (
        "core_components",
        "architectural_flow",
        "architectural_flow_feedback",
        "data_flow",
    ):
        text = _field_value(spec, key)
        if text and len(text) > 20:
            queries.append(text[:400])

    if not queries:
        queries.append(enriched[:800] if enriched else spec.problem_statement[:500])

    return queries[:4]


def _fetch_catalog_matches(
    spec: ArchitectureSpec,
    settings: Settings,
    *,
    top_k_per_query: int = 5,
) -> list[CatalogMatch]:
    """
    Run multiple catalog searches and merge by best score per agent id.

    Side effects:
        Azure OpenAI embeddings + Azure AI Search queries.
    """
    by_id: dict[str, CatalogMatch] = {}

    for query in _build_search_queries(spec):
        try:
            rows = search_agents(query, settings, top_k=top_k_per_query)
        except Exception as exc:
            logger.warning("Catalog search failed for query snippet: %s", exc)
            continue

        for row in rows:
            agent_id = str(row.get("id") or "").strip()
            if not agent_id:
                continue
            score = float(row.get("score") or 0.0)
            existing = by_id.get(agent_id)
            if existing and existing.score >= score:
                continue
            by_id[agent_id] = CatalogMatch(
                agent_id=agent_id,
                name=str(row.get("name") or "Unknown"),
                category=str(row.get("category") or ""),
                origin_client=str(row.get("origin_client") or ""),
                origin_project=str(row.get("origin_project") or ""),
                function_summary=str(row.get("function_summary") or "")[:300],
                score=score,
                matched_for=query[:80],
            )

    matches = sorted(by_id.values(), key=lambda m: m.score, reverse=True)
    logger.info("Catalog matches for planning: %d agents", len(matches))
    return matches[:20]


def refresh_catalog_matches(
    spec: ArchitectureSpec,
    settings: Settings,
) -> list[CatalogMatch]:
    """Re-query Azure AI Search for planning/remediation (fresh catalog evidence)."""
    return _fetch_catalog_matches(spec, settings)


def _format_matches_for_prompt(matches: list[CatalogMatch]) -> str:
    if not matches:
        return "(no catalog matches — index empty or search unavailable)"
    lines = []
    for m in matches:
        lines.append(
            f"- id={m.agent_id} | {m.name} | {m.category} | score={m.score:.2f} | "
            f"{m.function_summary[:120]}"
        )
    return "\n".join(lines)


def _format_spec_for_plan(spec: ArchitectureSpec) -> str:
    known = spec.compact_known_json()
    return json.dumps(
        {
            "problem_statement": spec.problem_statement,
            "status": spec.status,
            "transcript_summary": spec.transcript_summary,
            "known_fields": known,
            "architecture_blueprint_excerpt": (spec.architecture_blueprint or "")[:2000],
        },
        indent=2,
    )


def _validate_graph(graph: GraphDraft) -> list[str]:
    """Return validation warnings for the planned graph."""
    warnings: list[str] = []
    node_ids = {n.id for n in graph.nodes}
    if not graph.nodes:
        warnings.append("Graph has no nodes")
        return warnings

    for edge in graph.edges:
        if edge.from_id not in node_ids:
            warnings.append(f"Edge from unknown node: {edge.from_id}")
        if edge.to_id not in node_ids:
            warnings.append(f"Edge to unknown node: {edge.to_id}")

    out_degree = {nid: 0 for nid in node_ids}
    in_degree = {nid: 0 for nid in node_ids}
    for edge in graph.edges:
        out_degree[edge.from_id] = out_degree.get(edge.from_id, 0) + 1
        in_degree[edge.to_id] = in_degree.get(edge.to_id, 0) + 1

    sources = [nid for nid in node_ids if in_degree.get(nid, 0) == 0]
    sinks = [nid for nid in node_ids if out_degree.get(nid, 0) == 0]
    if not sources:
        warnings.append("No clear entry node (all nodes have incoming edges)")
    if not sinks:
        warnings.append("No clear exit node (all nodes have outgoing edges)")

    return warnings


def _normalize_node_id(raw: str) -> str:
    return normalize_node_id(raw)


def _apply_catalog_ids(
    graph: GraphDraft,
    matches: list[CatalogMatch],
) -> GraphDraft:
    """Ensure agent_id on nodes references a known catalog id when possible."""
    valid_ids = {m.agent_id for m in matches}
    by_name = {m.name.lower(): m.agent_id for m in matches}
    old_to_new: dict[str, str] = {}

    nodes: list[GraphNode] = []
    for node in graph.nodes:
        new_id = _normalize_node_id(node.id)
        old_to_new[node.id] = new_id
        agent_id = node.agent_id
        if agent_id and agent_id not in valid_ids:
            agent_id = None
        if not agent_id and node.type == "agent":
            agent_id = by_name.get(node.label.lower())
        if agent_id and agent_id not in valid_ids:
            agent_id = None
        nodes.append(
            node.model_copy(update={"id": new_id, "agent_id": agent_id})
        )

    edges: list[GraphEdge] = []
    for edge in graph.edges:
        edges.append(
            GraphEdge(
                from_id=old_to_new.get(edge.from_id, _normalize_node_id(edge.from_id)),
                to_id=old_to_new.get(edge.to_id, _normalize_node_id(edge.to_id)),
                label=edge.label,
            )
        )

    return sanitize_graph(GraphDraft(nodes=nodes, edges=edges))


def _ensure_reuse_decisions(
    graph: GraphDraft,
    decisions: list[ReuseDecision],
    matches: list[CatalogMatch],
) -> list[ReuseDecision]:
    """One reuse decision per graph node; fill gaps after LLM output."""
    by_id = {d.node_id: d for d in decisions}
    out: list[ReuseDecision] = []
    for node in graph.nodes:
        existing = by_id.get(node.id)
        if existing:
            out.append(existing.model_copy(update={"node_label": node.label}))
            continue
        agent_name = None
        if node.agent_id:
            agent_name = next(
                (m.name for m in matches if m.agent_id == node.agent_id),
                None,
            )
        out.append(
            ReuseDecision(
                node_id=node.id,
                node_label=node.label,
                decision="reuse" if node.agent_id else "build",
                agent_id=node.agent_id,
                agent_name=agent_name,
                rationale="Auto-filled for graph step.",
            )
        )
    return out


def _fallback_from_graph_draft(
    spec: ArchitectureSpec,
    matches: list[CatalogMatch],
) -> ArchitecturePlan:
    """Use interview graph_draft when LLM planning fails."""
    graph = sanitize_graph(spec.graph_draft or GraphDraft())
    graph = _apply_catalog_ids(graph, matches)
    decisions = [
        ReuseDecision(
            node_id=n.id,
            node_label=n.label,
            decision="reuse" if n.agent_id else "build",
            agent_id=n.agent_id,
            agent_name=next((m.name for m in matches if m.agent_id == n.agent_id), None),
            rationale="From interview graph draft (LLM plan unavailable).",
        )
        for n in graph.nodes
    ]
    return ArchitecturePlan(
        graph=graph,
        reuse_decisions=decisions,
        catalog_matches=matches,
        summary_markdown=spec.architecture_blueprint or "Architecture plan from interview draft.",
        open_questions=["LLM planner failed — review graph draft manually."],
    )


def plan_architecture(
    session: InterviewSession,
    settings: Settings,
    client: AzureOpenAI | None = None,
) -> ArchitecturePlan:
    """
    Build a Phase 3 architecture plan from a completed interview session.

    Args:
        session: Interview session with spec status sufficient or ready.
        settings: Azure settings.
        client: Optional OpenAI client.

    Returns:
        ArchitecturePlan with graph, reuse decisions, and summary.

    Raises:
        ValueError: If spec is not complete enough for planning.
    """
    spec = session.spec
    if spec.status not in MIN_SPEC_STATUS:
        raise ValueError(
            f"Specification status must be 'sufficient' or 'ready' (got '{spec.status}'). "
            "Complete more of the interview first."
        )

    if client is None:
        client = make_client(settings)

    matches = _fetch_catalog_matches(spec, settings)
    system = load_prompt("architecture_plan.txt")
    draft_json = (
        spec.graph_draft.model_dump_json(indent=2)
        if spec.graph_draft
        else '{"nodes":[],"edges":[]}'
    )
    user = (
        f"PROBLEM STATEMENT:\n{spec.problem_statement}\n\n"
        f"SPEC:\n{_format_spec_for_plan(spec)}\n\n"
        f"INTERVIEW GRAPH_DRAFT:\n{draft_json}\n\n"
        f"CATALOG MATCHES:\n{_format_matches_for_prompt(matches)}"
    )

    try:
        raw = call_llm(client, settings, system, user, json_mode=True, temperature=0.15)
        parsed = json.loads(strip_json_fences(raw))
        graph = GraphDraft.model_validate(parsed.get("graph") or {})
        graph = sanitize_graph(graph)
        graph = _apply_catalog_ids(graph, matches)

        decisions_raw = parsed.get("reuse_decisions") or []
        decisions: list[ReuseDecision] = []
        for item in decisions_raw:
            if isinstance(item, dict):
                try:
                    decisions.append(ReuseDecision.model_validate(item))
                except ValidationError:
                    continue

        decisions = _ensure_reuse_decisions(graph, decisions, matches)

        plan = ArchitecturePlan(
            graph=graph,
            reuse_decisions=decisions,
            catalog_matches=matches,
            summary_markdown=(parsed.get("summary_markdown") or "").strip(),
            open_questions=[
                str(q) for q in (parsed.get("open_questions") or []) if str(q).strip()
            ],
        )
    except Exception as exc:
        logger.error("Architecture planning LLM failed: %s", exc)
        plan = _fallback_from_graph_draft(spec, matches)

    for warning in _validate_graph(plan.graph):
        logger.warning("Graph validation: %s", warning)
        if warning not in plan.open_questions:
            plan.open_questions.append(warning)

    from services.architecture_remediation import enrich_validation_report

    validation_raw = validate_architecture_plan(spec, plan)
    enriched = enrich_validation_report(spec, plan, validation_raw)
    plan.validation = ArchitectureValidationReport.model_validate(enriched)
    logger.info(
        "Architecture validation: overall=%s pass=%d warn=%d fail=%d",
        plan.validation.overall,
        plan.validation.pass_count,
        plan.validation.warn_count,
        plan.validation.fail_count,
    )

    logger.info(
        "Architecture plan: %d nodes, %d edges, %d reuse decisions",
        len(plan.graph.nodes),
        len(plan.graph.edges),
        len(plan.reuse_decisions),
    )
    return plan
