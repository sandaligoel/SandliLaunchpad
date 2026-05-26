"""Validate Phase 3 architecture plans against spec and catalog evidence."""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Literal, Optional

from schemas.architecture_plan import ArchitecturePlan, ReuseDecision
from schemas.architecture_spec import ArchitectureSpec, GraphDraft

ValidationLevel = Literal["pass", "warn", "fail"]

_LEVEL_RANK = {"pass": 0, "warn": 1, "fail": 2}

SPEC_COVERAGE_CHECKS: list[tuple[str, str, tuple[str, ...]]] = [
    ("latency_target", "latency", ("latency", "ms", "second", "minute", "real-time", "batch", "sla")),
    ("accuracy_target", "accuracy", ("accuracy", "precision", "recall", "f1", "percent", "%")),
    ("deployment_platform", "deployment", ("azure", "aws", "gcp", "kubernetes", "cloud", "on-prem", "deploy")),
    ("data_volume", "data volume", ("volume", "gb", "tb", "records", "rows", "throughput", "scale")),
]


def _worst(a: ValidationLevel, b: ValidationLevel) -> ValidationLevel:
    return a if _LEVEL_RANK[a] >= _LEVEL_RANK[b] else b


def _tokens(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9]{3,}", text.lower()) if len(t) >= 3}


def _spec_value(spec: ArchitectureSpec, key: str) -> str:
    field = spec.fields.get(key)
    if field and field.is_known and field.value:
        return field.value.strip()
    return ""


def _graph_text(graph: GraphDraft) -> str:
    parts: list[str] = []
    for node in graph.nodes:
        parts.append(node.label)
        if node.description:
            parts.append(node.description)
    for edge in graph.edges:
        if edge.label:
            parts.append(edge.label)
    return " ".join(parts).lower()


def _forward_reachable(graph: GraphDraft, starts: list[str]) -> set[str]:
    adj: dict[str, list[str]] = defaultdict(list)
    for edge in graph.edges:
        adj[edge.from_id].append(edge.to_id)
    seen: set[str] = set()
    stack = [s for s in starts if s]
    while stack:
        nid = stack.pop()
        if nid in seen:
            continue
        seen.add(nid)
        for nxt in adj.get(nid, []):
            if nxt not in seen:
                stack.append(nxt)
    return seen


def _backward_reachable(graph: GraphDraft, starts: list[str]) -> set[str]:
    rev: dict[str, list[str]] = defaultdict(list)
    for edge in graph.edges:
        rev[edge.to_id].append(edge.from_id)
    seen: set[str] = set()
    stack = [s for s in starts if s]
    while stack:
        nid = stack.pop()
        if nid in seen:
            continue
        seen.add(nid)
        for prev in rev.get(nid, []):
            if prev not in seen:
                stack.append(prev)
    return seen


def _undirected_components(graph: GraphDraft) -> list[set[str]]:
    """Connected components treating edges as undirected."""
    parent: dict[str, str] = {}

    def find(x: str) -> str:
        parent.setdefault(x, x)
        if parent[x] != x:
            parent[x] = find(parent[x])
        return parent[x]

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for node in graph.nodes:
        find(node.id)
    for edge in graph.edges:
        if edge.from_id in parent or edge.to_id in parent:
            find(edge.from_id)
            find(edge.to_id)
            union(edge.from_id, edge.to_id)

    groups: dict[str, set[str]] = defaultdict(set)
    for node in graph.nodes:
        groups[find(node.id)].add(node.id)
    return list(groups.values())


def make_finding_key(
    code: str,
    message: str,
    node_id: Optional[str] = None,
    *,
    edge_from: Optional[str] = None,
    edge_to: Optional[str] = None,
    spec_key: Optional[str] = None,
    question_index: Optional[int] = None,
) -> str:
    if code == "open_question" and question_index is not None:
        return f"open_question:{question_index}"
    if code == "dangling_edge" and edge_from and edge_to:
        return f"dangling_edge:{edge_from}:{edge_to}"
    if spec_key:
        return f"{code}:{spec_key}"
    return f"{code}:{node_id or '_'}"


def finding_id_from_item(item: dict) -> str:
    """Stable id used by remediation and resolutions."""
    return item.get("finding_key") or make_finding_key(
        item["code"],
        item["message"],
        item.get("node_id"),
    )


class ValidationItem:
    """Single validation finding."""

    __slots__ = (
        "level",
        "code",
        "message",
        "node_id",
        "finding_key",
        "blocks_approval",
        "help_text",
    )

    def __init__(
        self,
        level: ValidationLevel,
        code: str,
        message: str,
        node_id: Optional[str] = None,
        *,
        finding_key: Optional[str] = None,
        blocks_approval: Optional[bool] = None,
        help_text: str = "",
        edge_from: Optional[str] = None,
        edge_to: Optional[str] = None,
        spec_key: Optional[str] = None,
        question_index: Optional[int] = None,
    ) -> None:
        self.level = level
        self.code = code
        self.message = message
        self.node_id = node_id
        self.finding_key = finding_key or make_finding_key(
            code,
            message,
            node_id,
            edge_from=edge_from,
            edge_to=edge_to,
            spec_key=spec_key,
            question_index=question_index,
        )
        self.blocks_approval = (
            blocks_approval if blocks_approval is not None else level == "fail"
        )
        self.help_text = help_text

    def to_dict(self) -> dict:
        out = {
            "level": self.level,
            "code": self.code,
            "message": self.message,
            "node_id": self.node_id,
            "finding_key": self.finding_key,
            "blocks_approval": self.blocks_approval,
            "help_text": self.help_text,
        }
        return out


def validate_architecture_plan(
    spec: ArchitectureSpec,
    plan: ArchitecturePlan,
) -> dict:
    """
    Run rule-based validation on a planned architecture.

    Returns:
        JSON-serializable report with overall status, counts, items, and per-node status.
    """
    items: list[ValidationItem] = []
    graph = plan.graph
    node_ids = {n.id for n in graph.nodes}
    id_list = [n.id for n in graph.nodes]
    if len(id_list) != len(node_ids):
        dupes = [nid for nid in id_list if id_list.count(nid) > 1]
        items.append(
            ValidationItem(
                "fail",
                "duplicate_node_id",
                f"Duplicate component ids: {', '.join(sorted(set(dupes))[:5])}.",
                blocks_approval=True,
                help_text="Regenerate architecture or fix duplicate ids in the plan.",
            )
        )

    decisions_by_node = {d.node_id: d for d in plan.reuse_decisions}
    catalog_ids = {m.agent_id for m in plan.catalog_matches}
    catalog_by_id = {m.agent_id: m for m in plan.catalog_matches}
    graph_blob = _graph_text(graph)

    if not plan.catalog_matches:
        items.append(
            ValidationItem(
                "warn",
                "catalog_empty",
                "No catalog agents were matched — reuse options may be limited.",
                help_text="Refresh catalog search or regenerate architecture after indexing.",
            )
        )

    for dec in plan.reuse_decisions:
        if dec.node_id not in node_ids:
            items.append(
                ValidationItem(
                    "fail",
                    "stale_decision",
                    f"Reuse decision references missing component '{dec.node_id}' ({dec.node_label}).",
                    node_id=dec.node_id,
                    finding_key=f"stale_decision:{dec.node_id}",
                    help_text="Remove stale decision or regenerate the graph.",
                )
            )

    # --- Graph structure ---
    if not graph.nodes:
        items.append(
            ValidationItem(
                "fail",
                "empty_graph",
                "Architecture has no components.",
                help_text="Regenerate architecture from your specification.",
            )
        )
    else:
        items.append(
            ValidationItem(
                "pass",
                "has_nodes",
                f"Graph has {len(graph.nodes)} components and {len(graph.edges)} connections.",
            )
        )

    for edge in graph.edges:
        if edge.from_id not in node_ids:
            items.append(
                ValidationItem(
                    "fail",
                    "dangling_edge",
                    f"Connection references missing source '{edge.from_id}'.",
                    edge_from=edge.from_id,
                    edge_to=edge.to_id or "_",
                    help_text="Remove invalid edge or restore the missing component.",
                )
            )
        if edge.to_id not in node_ids:
            items.append(
                ValidationItem(
                    "fail",
                    "dangling_edge",
                    f"Connection references missing target '{edge.to_id}'.",
                    edge_from=edge.from_id or "_",
                    edge_to=edge.to_id,
                    help_text="Remove invalid edge or restore the missing component.",
                )
            )

    in_degree = {nid: 0 for nid in node_ids}
    out_degree = {nid: 0 for nid in node_ids}
    for edge in graph.edges:
        if edge.from_id in out_degree:
            out_degree[edge.from_id] += 1
        if edge.to_id in in_degree:
            in_degree[edge.to_id] += 1

    sources = [nid for nid in node_ids if in_degree[nid] == 0]
    sinks = [nid for nid in node_ids if out_degree[nid] == 0]
    if not sources and node_ids:
        items.append(
            ValidationItem(
                "warn",
                "no_entry",
                "No clear entry point — every step has an incoming connection.",
                help_text="Add an entry gateway or confirm a cyclic flow is intentional.",
            )
        )
    if not sinks and node_ids:
        items.append(
            ValidationItem(
                "warn",
                "no_exit",
                "No clear exit point — every step has an outgoing connection.",
                help_text="Confirm the flow is intentional or add a terminal step.",
            )
        )

    if graph.edges and node_ids:
        fwd = _forward_reachable(graph, sources if sources else list(node_ids)[:1])
        bwd = _backward_reachable(graph, sinks if sinks else list(node_ids)[:1])
        on_path = fwd & bwd
        for node in graph.nodes:
            if node.id not in on_path:
                items.append(
                    ValidationItem(
                        "warn",
                        "orphan_node",
                        f"'{node.label}' is not on any entry→exit path.",
                        node_id=node.id,
                        help_text="Connect this step to the main flow or remove it.",
                    )
                )

    components = _undirected_components(graph)
    if len(components) > 1 and graph.nodes:
        sizes = sorted((len(c) for c in components), reverse=True)
        items.append(
            ValidationItem(
                "warn",
                "disconnected_subgraph",
                f"Graph has {len(components)} disconnected groups (sizes: {', '.join(map(str, sizes[:5]))}).",
                help_text="Add connections between groups or split into separate diagrams.",
            )
        )

    # --- Per-node: reuse / catalog ---
    for node in graph.nodes:
        dec = decisions_by_node.get(node.id)
        if not dec and node.type in ("agent", "custom", "gateway", "human"):
            items.append(
                ValidationItem(
                    "warn",
                    "missing_decision",
                    f"No reuse decision recorded for '{node.label}' ({node.type}).",
                    node_id=node.id,
                    help_text="Assign reuse, adapt, or build for this step.",
                )
            )

        if not dec:
            continue

        if dec.decision in ("reuse", "adapt"):
            if not dec.agent_id:
                items.append(
                    ValidationItem(
                        "fail",
                        "reuse_no_agent",
                        f"'{node.label}' marked {dec.decision} but no catalog agent id.",
                        node_id=node.id,
                        help_text="Pick a catalog agent or mark as custom build.",
                    )
                )
            elif dec.agent_id not in catalog_ids:
                items.append(
                    ValidationItem(
                        "fail",
                        "unknown_agent_id",
                        f"Agent id '{dec.agent_id}' was not in catalog search results.",
                        node_id=node.id,
                        help_text="Refresh catalog search or choose another agent.",
                    )
                )
            else:
                match = catalog_by_id.get(dec.agent_id)
                if match and match.score < 0.3:
                    items.append(
                        ValidationItem(
                            "warn",
                            "low_catalog_score",
                            f"Catalog match score is low ({match.score:.2f}) for '{match.name}'.",
                            node_id=node.id,
                        )
                    )
                node_tokens = _tokens(
                    f"{node.label} {node.description or ''} {dec.rationale}"
                )
                agent_text = (
                    match.function_summary if match else dec.agent_name or ""
                )
                agent_tokens = _tokens(agent_text)
                if node_tokens and agent_tokens:
                    overlap = len(node_tokens & agent_tokens) / max(
                        len(node_tokens), 1
                    )
                    if overlap < 0.08:
                        items.append(
                            ValidationItem(
                                "warn",
                                "weak_catalog_fit",
                                f"'{node.label}' may not match catalog agent capabilities (review fit).",
                                node_id=node.id,
                            )
                        )
                    else:
                        items.append(
                            ValidationItem(
                                "pass",
                                "catalog_fit",
                                f"Catalog agent '{dec.agent_name or dec.agent_id}' aligns with this step.",
                                node_id=node.id,
                            )
                        )

        if dec.decision == "build":
            items.append(
                ValidationItem(
                    "pass",
                    "build_ok",
                    f"Custom build for '{node.label}' — confirm no catalog alternative.",
                    node_id=node.id,
                )
            )

    # --- Spec coverage ---
    for field_key, label, hint_tokens in SPEC_COVERAGE_CHECKS:
        text = _spec_value(spec, field_key)
        if not text or len(text) < 8:
            continue
        field_tokens = _tokens(text)
        hint_hits = [t for t in hint_tokens if t in graph_blob]
        token_hits = len(field_tokens & _tokens(graph_blob))
        if len(field_tokens) >= 2 and token_hits < 1 and len(hint_hits) < 1:
            items.append(
                ValidationItem(
                    "warn",
                    "spec_coverage_gap",
                    f"Spec '{label}' may not be reflected on the architecture diagram.",
                    spec_key=field_key,
                    help_text=f"Add components or labels referencing {label}, or acknowledge.",
                )
            )

    hitl = _spec_value(spec, "hitl_behavior").lower()
    if hitl and any(
        w in hitl for w in ("human", "analyst", "approval", "review", "hitl")
    ):
        has_human = any(n.type == "human" for n in graph.nodes)
        if not has_human:
            items.append(
                ValidationItem(
                    "warn",
                    "hitl_missing",
                    "Spec requires human-in-the-loop but no 'human' step appears on the graph.",
                    help_text="Add a human approval step or acknowledge HITL is external.",
                )
            )
        else:
            items.append(
                ValidationItem(
                    "pass",
                    "hitl_present",
                    "Human-in-the-loop step present as specified.",
                )
            )

    integrations = _spec_value(spec, "integrations")
    if integrations:
        int_tokens = _tokens(integrations)
        found = [t for t in int_tokens if t in graph_blob]
        if len(int_tokens) >= 2 and len(found) < max(1, len(int_tokens) // 3):
            items.append(
                ValidationItem(
                    "warn",
                    "integrations_gap",
                    f"Integrations in spec may not appear on the graph (found: {', '.join(found[:5]) or 'none'}).",
                    help_text="Add integration gateway/labels or acknowledge implicit integrations.",
                )
            )
        elif found:
            items.append(
                ValidationItem(
                    "pass",
                    "integrations_reflected",
                    "Key integrations from spec appear in the architecture.",
                )
            )

    use_case = _spec_value(spec, "use_case")
    if use_case and len(use_case) > 20:
        uc_tokens = _tokens(use_case)
        overlap_graph = len(uc_tokens & _tokens(graph_blob)) / max(len(uc_tokens), 1)
        if overlap_graph < 0.05:
            items.append(
                ValidationItem(
                    "warn",
                    "use_case_drift",
                    "Use case text has little overlap with component names — verify flow matches intent.",
                    help_text="Compare canvas to specification use case.",
                )
            )
        else:
            items.append(
                ValidationItem(
                    "pass",
                    "use_case_aligned",
                    "Architecture text overlaps with stated use case.",
                )
            )

    flow_spec = _spec_value(spec, "architectural_flow_feedback") or _spec_value(
        spec, "architectural_flow"
    )
    if flow_spec and len(graph.nodes) >= 2:
        items.append(
            ValidationItem(
                "pass",
                "flow_documented",
                "Architectural flow was confirmed in the interview — compare visually to canvas.",
                help_text="Validation checks structure and spec overlap, not full business correctness.",
            )
        )

    for idx, q in enumerate(plan.open_questions):
        items.append(
            ValidationItem(
                "warn",
                "open_question",
                q,
                question_index=idx,
                help_text="Resolve or acknowledge open planning questions.",
            )
        )

    items.append(
        ValidationItem(
            "pass",
            "validation_scope",
            "Automated checks cover structure, catalog ids, and spec overlap — not full business proof.",
            blocks_approval=False,
        )
    )

    # --- Aggregate ---
    node_status: dict[str, ValidationLevel] = {}
    for node in graph.nodes:
        node_status[node.id] = "pass"

    pass_count = warn_count = fail_count = 0
    structural_fail_count = 0
    overall: ValidationLevel = "pass"

    for item in items:
        if item.level == "pass":
            pass_count += 1
        elif item.level == "warn":
            warn_count += 1
        else:
            fail_count += 1
            if item.blocks_approval:
                structural_fail_count += 1
        overall = _worst(overall, item.level)
        if item.node_id and item.node_id in node_status:
            node_status[item.node_id] = _worst(
                node_status[item.node_id], item.level
            )

    if fail_count > 0:
        overall = "fail"
    elif warn_count > 0 and overall == "pass":
        overall = "warn"

    return {
        "overall": overall,
        "pass_count": pass_count,
        "warn_count": warn_count,
        "fail_count": fail_count,
        "structural_fail_count": structural_fail_count,
        "items": [i.to_dict() for i in items],
        "node_status": node_status,
    }
