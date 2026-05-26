"""Architecture planner — retrieval, reuse vs build, graph generation."""

from __future__ import annotations

import re

from pydantic import BaseModel, Field

from app.core.llm_client import AzureLLMClient
from app.core.logging import get_logger
from app.prompts.planner import (
    CAPABILITY_DECOMPOSE_SYSTEM,
    CAPABILITY_DECOMPOSE_USER,
    FLOW_ALIGN_SYSTEM,
    FLOW_ALIGN_USER,
    PLANNER_NARRATIVE_SYSTEM,
    PLANNER_NARRATIVE_USER,
)
from app.schemas.architecture_graph import (
    ArchitecturePlanResponse,
    CapabilityMatch,
    EdgeType,
    GraphEdge,
    GraphNode,
    NodeType,
    ReuseDecision,
)
from app.schemas.architecture_spec import ArchitectureSpec
from app.schemas.search import AgentSearchRequest, SearchMode
from app.services.search import SearchService
from app.services.session_store import get_session, save_plan
from app.utils.ids import azure_safe_document_id

logger = get_logger(__name__)

REUSE_SCORE_THRESHOLD = 0.015
_MIN_SPEC_AGENTS = 3
_MAX_FLOW_AGENTS = 14


class CapabilityItem(BaseModel):
    id: str
    description: str
    pipeline_order: int = 0


class CapabilityListResult(BaseModel):
    capabilities: list[CapabilityItem] = Field(default_factory=list)


class NarrativeResult(BaseModel):
    narrative: str


def _normalize_key(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")[:48]


def _display_label(text: str, fallback: str) -> str:
    t = (text or "").strip()
    if not t or t.lower() in ("empty", "none", "n/a", "unknown"):
        return fallback
    return t[:80]


def _entry_gateway_label(summary: dict[str, str], problem: str) -> str:
    data = summary.get("data_sources", "").lower()
    p = problem.lower()
    if any(x in p for x in ("planogram", "shelf", "pos", "erp", "retail")):
        return "Planogram & POS feeds"
    if any(x in data for x in ("dam", "pim", "asset")):
        return "DAM / PIM"
    if any(x in p for x in ("amazon", "pdp", "marketplace")):
        return "Catalog & assets"
    if any(x in p for x in ("kyc", "trade", "onboarding")):
        return "Case & document inputs"
    return "External inputs"


_NON_AGENT_PART_MARKERS = (
    "orchestrator",
    "supervisor",
    "gateway",
    "entry point",
    "human review",
    "human gate",
    "human-in-the-loop",
    "start →",
    "end-to-end flow",
    "published output",
    "deployment target",
)


def _is_agent_part(part: str) -> bool:
    p = part.strip().lower()
    if len(p) < 3:
        return False
    if any(m in p for m in _NON_AGENT_PART_MARKERS) and "agent" not in p:
        return False
    if p in ("start", "end", "input", "output", "inputs", "outputs"):
        return False
    return True


def _agent_label_from_part(part: str) -> str:
    p = part.strip()
    low = p.lower()
    if "agent" in low or any(
        low.endswith(suffix)
        for suffix in ("checker", "extractor", "mapper", "scorer", "matcher", "router", "builder")
    ):
        return p
    return f"{p} agent"


def _split_flow_parts(text: str) -> list[str]:
    if not text.strip():
        return []
    normalized = text.strip()
    normalized = re.sub(r"\s*[\n;]+\s*", "\n", normalized)
    normalized = re.sub(r"(?m)^\s*[-•*]\s+", "", normalized)
    parts = re.split(
        r"\n+|,\s+|(?:\s*→\s*)|(?:\s*->\s*)|(?:\s+then\s+)|(?:(?:\d+)[\.\)]\s*)",
        normalized,
        flags=re.IGNORECASE,
    )
    out: list[str] = []
    for p in parts:
        p = re.sub(r"^[\-\*•\d\.\)\s]+", "", p).strip()
        p = re.sub(r"^(?:step\s*)?\d+[\.\):\-]\s*", "", p, flags=re.IGNORECASE).strip()
        if _is_agent_part(p):
            out.append(p)
    return out


def _capabilities_from_text(
    text: str, *, id_prefix: str = "agent"
) -> list[CapabilityItem]:
    parts = _split_flow_parts(text)
    caps: list[CapabilityItem] = []
    seen_ids: set[str] = set()
    for i, part in enumerate(parts):
        base_id = _normalize_key(part) or f"{id_prefix}_{i}"
        uid = base_id
        n = 2
        while uid in seen_ids:
            uid = f"{base_id}_{n}"
            n += 1
        seen_ids.add(uid)
        label = _agent_label_from_part(part)
        caps.append(
            CapabilityItem(
                id=uid,
                description=label,
                pipeline_order=i + 1,
            )
        )
    return caps


def _cap_exists(merged: list[CapabilityItem], cap: CapabilityItem) -> bool:
    cid = _normalize_key(cap.id)
    return any(_normalize_key(m.id) == cid for m in merged)


def _normalize_words(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]{3,}", (text or "").lower()))


def _fuzzy_dup_existing(merged: list[CapabilityItem], cap: CapabilityItem) -> bool:
    if _cap_exists(merged, cap):
        return True
    new_w = _normalize_words(cap.description)
    if not new_w:
        return False
    for existing in merged:
        old_w = _normalize_words(existing.description)
        if not old_w:
            continue
        overlap = len(new_w & old_w)
        denom = min(len(new_w), len(old_w))
        if denom and overlap / denom >= 0.5:
            return True
    return False


def _merge_roles_and_steps(roles: str, steps: str) -> list[CapabilityItem]:
    """flow_steps defines execution order; agent_roles adds agents not already listed."""
    step_caps = _capabilities_from_text(steps, id_prefix="step")
    role_caps = _capabilities_from_text(roles, id_prefix="role")
    if step_caps and role_caps:
        merged: list[CapabilityItem] = list(step_caps)
        for role in role_caps:
            if not _fuzzy_dup_existing(merged, role):
                _append_capabilities(merged, [role])
        return merged
    if step_caps:
        return list(step_caps)
    if role_caps:
        return list(role_caps)
    return []


def _drop_infra_duplicates(
    summary: dict[str, str], caps: list[CapabilityItem]
) -> list[CapabilityItem]:
    """Avoid duplicate supervisor/human nodes already shown as orchestrator or HITL gate."""
    orch = summary.get("orchestration_pattern", "").lower()
    hitl = summary.get("human_in_the_loop", "").lower()
    out: list[CapabilityItem] = []
    for cap in caps:
        cid = _normalize_key(cap.id)
        desc = cap.description.lower()
        if ("supervisor" in orch or "router" in orch) and cid in (
            "supervisor_agent",
            "router_agent",
        ):
            continue
        if hitl and "none" not in hitl and "no human" not in hitl:
            if cid in ("human_handoff_agent", "human_review_agent") or (
                "human" in desc and "agent" in desc
            ):
                continue
        out.append(cap)
    return out


def _optional_extras_from_spec(
    summary: dict[str, str], merged: list[CapabilityItem]
) -> list[CapabilityItem]:
    """At most two agents implied by retrieval/graph slots when not already in the pipeline."""
    existing = " ".join(c.description.lower() for c in merged)
    extras: list[CapabilityItem] = []

    retrieval = summary.get("retrieval_required", "").lower()
    if retrieval and not any(
        x in retrieval
        for x in (
            "no retrieval",
            "no rag",
            "none",
            "not required",
            "structured only",
            "flat only",
        )
    ):
        if not any(x in existing for x in ("retriev", "rag", "index")):
            extras.append(
                CapabilityItem(
                    id="retrieval_agent",
                    description="Retrieval / RAG agent",
                    pipeline_order=0,
                )
            )

    graph = summary.get("knowledge_graph_scope", "").lower()
    if graph and not any(
        x in graph
        for x in ("flat", "no graph", "out of scope", "phase 1 only", "not in scope")
    ):
        if "graph" not in existing:
            extras.append(
                CapabilityItem(
                    id="knowledge_graph_agent",
                    description="Knowledge graph agent",
                    pipeline_order=0,
                )
            )

    return extras[:2]


def _append_capabilities(
    merged: list[CapabilityItem], new_caps: list[CapabilityItem]
) -> list[CapabilityItem]:
    order = len(merged) + 1
    for c in new_caps:
        if _cap_exists(merged, c):
            continue
        c.pipeline_order = order
        merged.append(c)
        order += 1
    return merged


def _dedupe_capabilities(caps: list[CapabilityItem]) -> list[CapabilityItem]:
    seen_ids: set[str] = set()
    out: list[CapabilityItem] = []
    for c in sorted(caps, key=lambda x: x.pipeline_order):
        cid = _normalize_key(c.id)
        if cid in seen_ids:
            continue
        seen_ids.add(cid)
        out.append(c)
    for i, c in enumerate(out):
        c.pipeline_order = i + 1
    return out[:_MAX_FLOW_AGENTS]


def _capabilities_from_platform_slots(summary: dict[str, str]) -> list[CapabilityItem]:
    """Extra agents implied by retrieval, graph, tools, and data — not duplicate infra nodes."""
    caps: list[CapabilityItem] = []
    problem = " ".join(summary.values()).lower()

    caps.append(
        CapabilityItem(id="ingest_agent", description="Ingest & staging agent", pipeline_order=0)
    )
    caps.append(
        CapabilityItem(
            id="document_classifier_agent",
            description="Document classifier agent",
            pipeline_order=0,
        )
    )

    if any(x in problem for x in ("pdf", "document", "pack", "bl", "receipt", "ocr")):
        caps.append(
            CapabilityItem(
                id="document_intelligence_agent",
                description="Document Intelligence / OCR agent",
                pipeline_order=0,
            )
        )

    retrieval = summary.get("retrieval_required", "").lower()
    if retrieval and not any(
        x in retrieval
        for x in ("no retrieval", "no rag", "none", "structured only", "flat only")
    ):
        caps.extend(
            [
                CapabilityItem(
                    id="indexing_agent",
                    description="Chunking & indexing agent",
                    pipeline_order=0,
                ),
                CapabilityItem(
                    id="retrieval_agent",
                    description="Retrieval / RAG query agent",
                    pipeline_order=0,
                ),
            ]
        )

    graph = summary.get("knowledge_graph_scope", "").lower()
    if graph and not any(
        x in graph for x in ("flat", "no graph", "out of scope", "phase 1 only")
    ):
        caps.extend(
            [
                CapabilityItem(
                    id="graph_builder_agent",
                    description="Knowledge graph builder agent",
                    pipeline_order=0,
                ),
                CapabilityItem(
                    id="graph_query_agent",
                    description="Graph traversal / GraphRAG agent",
                    pipeline_order=0,
                ),
            ]
        )

    if any(x in problem for x in ("kyc", "ubo", "policy", "sanction", "compliance")):
        caps.extend(
            [
                CapabilityItem(
                    id="entity_extraction_agent",
                    description="Entity & UBO extraction agent",
                    pipeline_order=0,
                ),
                CapabilityItem(
                    id="policy_validation_agent",
                    description="Policy validation agent",
                    pipeline_order=0,
                ),
                CapabilityItem(
                    id="risk_scoring_agent",
                    description="Risk scoring agent",
                    pipeline_order=0,
                ),
            ]
        )

    if any(x in problem for x in ("trade", "warehouse", "photo", "vision", "bl", "sku")):
        caps.extend(
            [
                CapabilityItem(
                    id="trade_extraction_agent",
                    description="Trade document extraction agent",
                    pipeline_order=0,
                ),
                CapabilityItem(
                    id="vision_matching_agent",
                    description="Vision / warehouse matching agent",
                    pipeline_order=0,
                ),
                CapabilityItem(
                    id="discrepancy_agent",
                    description="Discrepancy & mismatch reporter agent",
                    pipeline_order=0,
                ),
            ]
        )

    if any(
        x in problem
        for x in ("planogram", "shelf", "share-of-shelf", "eye-level", "field photo")
    ):
        caps.extend(
            [
                CapabilityItem(
                    id="photo_intake_agent",
                    description="Photo intake & ordering agent",
                    pipeline_order=0,
                ),
                CapabilityItem(
                    id="shelf_vision_agent",
                    description="Shelf vision / detection agent",
                    pipeline_order=0,
                ),
                CapabilityItem(
                    id="sku_mapper_agent",
                    description="SKU mapping & shelf_state agent",
                    pipeline_order=0,
                ),
                CapabilityItem(
                    id="pos_join_agent",
                    description="POS / promo join agent",
                    pipeline_order=0,
                ),
                CapabilityItem(
                    id="forecast_scenario_agent",
                    description="Forecast scenario agent",
                    pipeline_order=0,
                ),
                CapabilityItem(
                    id="compliance_output_agent",
                    description="Compliance & guidance output agent",
                    pipeline_order=0,
                ),
            ]
        )

    orch = summary.get("orchestration_pattern", "").lower()
    if "supervisor" in orch or "router" in orch:
        caps.insert(
            0,
            CapabilityItem(
                id="supervisor_agent",
                description="Supervisor / router agent",
                pipeline_order=0,
            ),
        )

    tools = summary.get("agent_tools", "").lower()
    if "rules" in tools or "policy" in problem:
        caps.append(
            CapabilityItem(
                id="rules_engine_agent",
                description="Rules engine agent",
                pipeline_order=0,
            )
        )

    hitl = summary.get("human_in_the_loop", "").lower()
    if hitl and "none" not in hitl and "no human" not in hitl:
        caps.append(
            CapabilityItem(
                id="human_handoff_agent",
                description="Human handoff / queue agent",
                pipeline_order=0,
            )
        )

    caps.append(
        CapabilityItem(
            id="case_output_agent",
            description="Case output & notification agent",
            pipeline_order=0,
        )
    )

    return caps


class ArchitecturePlannerService:
    def __init__(self) -> None:
        self.llm = AzureLLMClient()
        self.search = SearchService()

    async def plan(
        self,
        spec: ArchitectureSpec,
        session_id: str = "",
    ) -> ArchitecturePlanResponse:
        if (
            not spec.is_complete()
            and not spec.ready_for_plan
            and spec.completion_pct() < 50
        ):
            from app.core.exceptions import KnowledgeBaseError
            raise KnowledgeBaseError(
                "Architecture spec incomplete — complete the interview first",
                {"completion_pct": spec.completion_pct()},
            )

        capabilities = await self._resolve_capabilities(spec)
        matches: list[CapabilityMatch] = []
        nodes: list[GraphNode] = []
        edges: list[GraphEdge] = []

        summary = spec.to_summary_dict()
        orch_label = self._orchestrator_label(summary)
        orch_id = azure_safe_document_id(f"{spec.session_id}_orchestrator")
        nodes.append(
            GraphNode(
                id=orch_id,
                type=NodeType.ORCHESTRATOR,
                label=orch_label,
                description=summary.get("orchestration_pattern", "Flow orchestration"),
                layer=1,
                reuse_decision=ReuseDecision.BUILD,
            )
        )

        prev_agent_id: str | None = None
        layer = 2
        edge_ids: set[str] = set()
        first_agent = True

        for cap in sorted(capabilities, key=lambda c: c.pipeline_order):
            match = await self._match_capability(cap, spec)
            matches.append(match)

            node_id = azure_safe_document_id(f"{spec.session_id}_{cap.id}")
            fallback = cap.id.replace("_", " ").title()
            label = _display_label(cap.description, fallback)

            nodes.append(
                GraphNode(
                    id=node_id,
                    type=NodeType.AGENT,
                    label=label,
                    description=cap.description,
                    layer=layer,
                    catalog_agent_id=match.catalog_agent_name,
                    source_project=match.catalog_project,
                    reuse_decision=match.decision,
                    metadata={
                        "capability": cap.id,
                        "pipeline_order": str(cap.pipeline_order),
                    },
                )
            )
            layer += 1

            if first_agent:
                eid = azure_safe_document_id(f"e_{orch_id}_{node_id}")
                if eid not in edge_ids:
                    edges.append(
                        GraphEdge(
                            id=eid,
                            source=orch_id,
                            target=node_id,
                            type=EdgeType.INVOKES,
                            label="start",
                        )
                    )
                    edge_ids.add(eid)
                first_agent = False
            elif prev_agent_id:
                eid = azure_safe_document_id(f"e_{prev_agent_id}_{node_id}")
                if eid not in edge_ids:
                    edges.append(
                        GraphEdge(
                            id=eid,
                            source=prev_agent_id,
                            target=node_id,
                            type=EdgeType.PRODUCES,
                            label="flow",
                        )
                    )
                    edge_ids.add(eid)

            prev_agent_id = node_id

        entry_id = self._add_entry_gateway(
            spec, nodes, edges, orch_id, edge_ids, first_agent
        )
        self._add_human_node(spec, nodes, edges, prev_agent_id, edge_ids)

        agent_nodes = [n for n in nodes if n.type == NodeType.AGENT]
        reuse_count = sum(
            1 for n in agent_nodes if n.reuse_decision == ReuseDecision.REUSE
        )
        build_count = sum(
            1 for n in agent_nodes if n.reuse_decision == ReuseDecision.BUILD
        )

        narrative = await self._narrative(spec, matches, len(nodes), len(edges))

        logger.info(
            "architecture_planned",
            session_id=session_id or spec.session_id,
            capabilities=len(capabilities),
            unique_agents=len(agent_nodes),
            reuse=reuse_count,
            build=build_count,
        )

        response = ArchitecturePlanResponse(
            session_id=session_id or spec.session_id,
            spec_summary=summary,
            capabilities=matches,
            nodes=nodes,
            edges=edges,
            reuse_count=reuse_count,
            build_count=build_count,
            narrative=narrative,
        )
        save_plan(response)
        return response

    async def plan_from_session(self, session_id: str) -> ArchitecturePlanResponse:
        spec = get_session(session_id)
        if not spec:
            from app.core.exceptions import KnowledgeBaseError
            raise KnowledgeBaseError("Session not found", {"session_id": session_id})
        return await self.plan(spec, session_id)

    def _orchestrator_label(self, summary: dict[str, str]) -> str:
        orch = summary.get("orchestration_pattern", "")
        if "supervisor" in orch.lower():
            return "Supervisor orchestrator"
        if "parallel" in orch.lower():
            return "Parallel orchestrator"
        if "sequential" in orch.lower() or "pipeline" in orch.lower():
            return "Pipeline orchestrator"
        return "Flow orchestrator"

    async def _resolve_capabilities(self, spec: ArchitectureSpec) -> list[CapabilityItem]:
        summary = spec.to_summary_dict()
        roles = summary.get("agent_roles", "")
        steps = summary.get("flow_steps", "") or summary.get("use_case", "")

        merged = _merge_roles_and_steps(roles, steps)
        spec_count = len(merged)

        if spec_count < 2:
            try:
                aligned = await self._align_flow_from_spec(spec)
                for cap in aligned:
                    if not _fuzzy_dup_existing(merged, cap):
                        _append_capabilities(merged, [cap])
            except Exception as exc:
                logger.warning("flow_align_failed", error=str(exc))

        if len(merged) < 2:
            try:
                decomposed = await self._decompose_capabilities(spec)
                for cap in decomposed:
                    if not _fuzzy_dup_existing(merged, cap):
                        _append_capabilities(merged, [cap])
            except Exception as exc:
                logger.warning("capability_decompose_failed", error=str(exc))

        if len(merged) < 1:
            for cap in self._minimal_defaults_from_problem(spec):
                if not _fuzzy_dup_existing(merged, cap):
                    _append_capabilities(merged, [cap])

        if len(merged) < 2:
            for extra in _optional_extras_from_spec(summary, merged):
                if not _fuzzy_dup_existing(merged, extra):
                    _append_capabilities(merged, [extra])

        merged = _drop_infra_duplicates(summary, merged)
        result = _dedupe_capabilities(merged)
        logger.info(
            "capabilities_resolved",
            session_id=spec.session_id,
            count=len(result),
            from_roles=len(_capabilities_from_text(roles)),
            from_steps=len(_capabilities_from_text(steps)),
        )
        return result

    async def _align_flow_from_spec(self, spec: ArchitectureSpec) -> list[CapabilityItem]:
        user = FLOW_ALIGN_USER.format(spec_json=spec.model_dump_json(indent=2)[:12000])
        result = await self.llm.complete_structured(
            FLOW_ALIGN_SYSTEM, user, CapabilityListResult
        )
        return result.capabilities or []

    async def _decompose_capabilities(self, spec: ArchitectureSpec) -> list[CapabilityItem]:
        user = CAPABILITY_DECOMPOSE_USER.format(
            spec_json=spec.model_dump_json(indent=2)[:12000]
        )
        result = await self.llm.complete_structured(
            CAPABILITY_DECOMPOSE_SYSTEM, user, CapabilityListResult
        )
        return result.capabilities or []

    def _minimal_defaults_from_problem(self, spec: ArchitectureSpec) -> list[CapabilityItem]:
        """Short domain-specific fallback only when the spec has no parseable agents."""
        problem = spec.problem_statement.lower()
        caps: list[CapabilityItem] = []
        if any(x in problem for x in ("planogram", "shelf", "sku", "share-of-shelf")):
            caps = [
                CapabilityItem(id="photo_intake_agent", description="Photo intake agent", pipeline_order=1),
                CapabilityItem(id="shelf_vision_agent", description="Shelf vision agent", pipeline_order=2),
                CapabilityItem(id="sku_mapper_agent", description="SKU mapping agent", pipeline_order=3),
                CapabilityItem(id="compliance_output_agent", description="Compliance output agent", pipeline_order=4),
            ]
        elif any(x in problem for x in ("kyc", "ubo", "onboarding", "sanction")):
            caps = [
                CapabilityItem(id="document_intake_agent", description="Document intake agent", pipeline_order=1),
                CapabilityItem(id="entity_extraction_agent", description="Entity extraction agent", pipeline_order=2),
                CapabilityItem(id="policy_validation_agent", description="Policy validation agent", pipeline_order=3),
                CapabilityItem(id="risk_scoring_agent", description="Risk scoring agent", pipeline_order=4),
            ]
        elif any(x in problem for x in ("trade", "warehouse", "bill of lading", "bl ")):
            caps = [
                CapabilityItem(id="trade_extraction_agent", description="Trade document extraction agent", pipeline_order=1),
                CapabilityItem(id="vision_matching_agent", description="Vision matching agent", pipeline_order=2),
                CapabilityItem(id="discrepancy_agent", description="Discrepancy reporter agent", pipeline_order=3),
            ]
        else:
            caps = [
                CapabilityItem(id="intake_agent", description="Intake agent", pipeline_order=1),
                CapabilityItem(id="processing_agent", description="Processing agent", pipeline_order=2),
                CapabilityItem(id="output_agent", description="Output agent", pipeline_order=3),
            ]
        for i, c in enumerate(caps):
            c.pipeline_order = i + 1
        return caps

    async def _match_capability(
        self, cap: CapabilityItem, spec: ArchitectureSpec
    ) -> CapabilityMatch:
        summary = spec.to_summary_dict()
        query = (
            f"{cap.description} {cap.id} "
            f"{summary.get('flow_steps', summary.get('use_case', ''))}"
        )
        try:
            resp = await self.search.search_agents(
                AgentSearchRequest(query=query, top_k=5, mode=SearchMode.HYBRID)
            )
        except Exception as e:
            logger.warning("capability_search_failed", capability=cap.id, error=str(e))
            return CapabilityMatch(
                capability=cap.id,
                decision=ReuseDecision.BUILD,
                rationale=f"No catalog match: {e}",
            )

        for hit in resp.results:
            name = (hit.agent_name or hit.title or "").strip()
            if not name:
                continue
            if hit.score >= REUSE_SCORE_THRESHOLD:
                return CapabilityMatch(
                    capability=cap.id,
                    decision=ReuseDecision.REUSE,
                    catalog_agent_name=name,
                    catalog_project=hit.project_name,
                    search_score=hit.score,
                    rationale=f"Reuse from catalog: {hit.project_name}",
                )
            return CapabilityMatch(
                capability=cap.id,
                decision=ReuseDecision.ADAPT,
                catalog_agent_name=name,
                catalog_project=hit.project_name,
                search_score=hit.score,
                rationale="Partial match — adapt existing agent",
            )

        return CapabilityMatch(
            capability=cap.id,
            decision=ReuseDecision.BUILD,
            rationale="No similar agent in catalog",
        )

    def _add_entry_gateway(
        self,
        spec: ArchitectureSpec,
        nodes: list[GraphNode],
        edges: list[GraphEdge],
        orch_id: str,
        edge_ids: set[str],
        no_agents: bool,
    ) -> str | None:
        """Single entry node; RAG/graph noted in description only (not separate boxes)."""
        summary = spec.to_summary_dict()
        problem = spec.problem_statement
        data = summary.get("data_sources", "").strip()
        if not data or data.lower().startswith("(not specified"):
            if not any(
                x in problem.lower()
                for x in ("planogram", "shelf", "pos", "ingest", "document", "api")
            ):
                return None

        desc_parts = []
        if data and not data.lower().startswith("(not specified"):
            desc_parts.append(data[:120])
        retrieval = summary.get("retrieval_required", "")
        if retrieval and not any(
            x in retrieval.lower()
            for x in ("no retrieval", "no rag", "none", "structured only", "flat")
        ):
            desc_parts.append(f"RAG: {retrieval[:80]}")
        graph = summary.get("knowledge_graph_scope", "")
        if graph and not any(
            x in graph.lower() for x in ("flat", "no graph", "out of scope")
        ):
            desc_parts.append(f"Graph: {graph[:80]}")
        deploy = summary.get("deployment_target", "")
        if deploy.strip():
            desc_parts.append(f"Runtime: {deploy[:60]}")

        entry_id = azure_safe_document_id(f"{spec.session_id}_entry")
        nodes.insert(
            1,
            GraphNode(
                id=entry_id,
                type=NodeType.DATA_STORE,
                label=_entry_gateway_label(summary, problem),
                description=" · ".join(desc_parts)[:240] or data[:200],
                layer=0,
                reuse_decision=ReuseDecision.BUILD,
            ),
        )
        eid = azure_safe_document_id(f"e_{entry_id}_{orch_id}")
        if eid not in edge_ids:
            edges.append(
                GraphEdge(
                    id=eid,
                    source=entry_id,
                    target=orch_id,
                    type=EdgeType.READS_FROM,
                )
            )
            edge_ids.add(eid)
        if no_agents:
            return entry_id
        return entry_id

    def _add_human_node(
        self,
        spec: ArchitectureSpec,
        nodes: list[GraphNode],
        edges: list[GraphEdge],
        last_agent_id: str | None,
        edge_ids: set[str],
    ) -> None:
        summary = spec.to_summary_dict()
        hitl = summary.get("human_in_the_loop", "")
        if not hitl or "none" in hitl.lower() or "no human" in hitl.lower():
            return
        h_id = azure_safe_document_id(f"{spec.session_id}_human")
        nodes.append(
            GraphNode(
                id=h_id,
                type=NodeType.HUMAN,
                label="Human review / QA gate",
                description=hitl[:200],
                layer=99,
                reuse_decision=ReuseDecision.BUILD,
            )
        )
        source = last_agent_id
        if not source:
            source = next(
                (n.id for n in nodes if n.type == NodeType.ORCHESTRATOR),
                None,
            )
        if source:
            eid = azure_safe_document_id(f"e_{source}_{h_id}")
            if eid not in edge_ids:
                edges.append(
                    GraphEdge(
                        id=eid,
                        source=source,
                        target=h_id,
                        type=EdgeType.ESCALATES_TO,
                    )
                )
                edge_ids.add(eid)

    async def _narrative(
        self,
        spec: ArchitectureSpec,
        matches: list[CapabilityMatch],
        node_count: int,
        edge_count: int,
    ) -> str:
        import json

        summary = spec.to_summary_dict()
        user = PLANNER_NARRATIVE_USER.format(
            spec_summary=json.dumps(summary, indent=2),
            reuse_json=json.dumps([m.model_dump() for m in matches], indent=2)[:8000],
            node_count=node_count,
            edge_count=edge_count,
        )
        try:
            result = await self.llm.complete_structured(
                PLANNER_NARRATIVE_SYSTEM, user, NarrativeResult, temperature=0.4
            )
            return result.narrative
        except Exception:
            flow = summary.get("flow_steps", summary.get("use_case", "solution"))
            agent_count = sum(1 for m in matches)
            return (
                f"Flow: {flow[:300]}. "
                f"Pipeline includes {agent_count} agents "
                f"({len([m for m in matches if m.decision == ReuseDecision.REUSE])} reused from catalog)."
            )
