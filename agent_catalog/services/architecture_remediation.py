"""Remediation options and apply-actions for architecture validation findings."""

from __future__ import annotations

import re
import uuid
from typing import Any, Optional

from schemas.architecture_plan import (
    ArchitecturePlan,
    CatalogMatch,
    ReuseDecision,
)
from schemas.architecture_spec import ArchitectureSpec, GraphDraft, GraphEdge, GraphNode
from config import Settings
from services.architecture_validator import (
    finding_id_from_item,
    validate_architecture_plan,
)

RemediationOption = dict[str, Any]
ResolutionRecord = dict[str, Any]


def _normalize_resolution(resolution: Any) -> Optional[ResolutionRecord]:
    """Coerce ValidationResolution or dict to a plain dict."""
    if resolution is None:
        return None
    if hasattr(resolution, "model_dump"):
        return resolution.model_dump()
    if isinstance(resolution, dict):
        return resolution
    return None


def _resolution_action(resolution: Any) -> str:
    data = _normalize_resolution(resolution)
    return (data or {}).get("action", "")


def _resolutions_as_dicts(plan: ArchitecturePlan) -> dict[str, ResolutionRecord]:
    out: dict[str, ResolutionRecord] = {}
    for k, v in (plan.validation_resolutions or {}).items():
        data = _normalize_resolution(v)
        if data:
            out[k] = data
    return out


def resolve_remediation_option(
    plan: ArchitecturePlan,
    finding_id_str: str,
    option_id: str,
    spec: Optional[ArchitectureSpec] = None,
) -> RemediationOption:
    """
    Look up the remediation option from the current plan validation report.
    Falls back to rebuilding options for the finding.
    """
    if not plan.validation:
        raise ValueError(
            "No validation report on plan. Generate architecture first."
        )

    for item in plan.validation.items:
        raw = (
            item.model_dump()
            if hasattr(item, "model_dump")
            else dict(item)
        )
        fid = finding_id_from_item(raw)
        if fid != finding_id_str:
            continue
        for opt in item.remediations:
            oid = opt.id if hasattr(opt, "id") else opt.get("id")
            if oid == option_id:
                return (
                    opt.model_dump()
                    if hasattr(opt, "model_dump")
                    else dict(opt)
                )
        raw_level = item.level
        level = raw_level if raw_level in ("warn", "fail") else "fail"
        rebuilt = build_remediations(
            item.code,
            item.message,
            level,
            plan,
            spec,
            item.node_id,
            finding_key=fid,
        )
        for opt in rebuilt:
            if opt.get("id") == option_id:
                return opt
        raise ValueError(
            f"Option '{option_id}' is not valid for finding '{finding_id_str}'."
        )

    raise ValueError(
        f"Finding '{finding_id_str}' not found. Refresh validation or regenerate."
    )


def _new_node_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def _decision_index(plan: ArchitecturePlan) -> dict[str, ReuseDecision]:
    return {d.node_id: d for d in plan.reuse_decisions}


def _upsert_decision(
    plan: ArchitecturePlan,
    node_id: str,
    node_label: str,
    decision: str,
    agent_id: Optional[str] = None,
    agent_name: Optional[str] = None,
    rationale: str = "",
    catalog_score: Optional[float] = None,
) -> None:
    existing = _decision_index(plan)
    if node_id in existing:
        d = existing[node_id]
        d.decision = decision  # type: ignore[assignment]
        d.agent_id = agent_id
        d.agent_name = agent_name
        d.rationale = rationale or d.rationale
        d.catalog_score = catalog_score
        d.node_label = node_label
    else:
        plan.reuse_decisions.append(
            ReuseDecision(
                node_id=node_id,
                node_label=node_label,
                decision=decision,  # type: ignore[arg-type]
                agent_id=agent_id,
                agent_name=agent_name,
                rationale=rationale,
                catalog_score=catalog_score,
            )
        )


def _catalog_for_node(plan: ArchitecturePlan, node_id: str) -> list[CatalogMatch]:
    """Catalog matches relevant to a node (matched_for or all by score)."""
    targeted = [m for m in plan.catalog_matches if m.matched_for == node_id]
    if targeted:
        return sorted(targeted, key=lambda m: m.score, reverse=True)
    return sorted(plan.catalog_matches, key=lambda m: m.score, reverse=True)


def _best_catalog(plan: ArchitecturePlan, node_id: str) -> Optional[CatalogMatch]:
    matches = _catalog_for_node(plan, node_id)
    return matches[0] if matches else None


def _spec_integrations_label(spec: ArchitectureSpec) -> str:
    field = spec.fields.get("integrations")
    if field and field.is_known and field.value:
        first = re.split(r"[,;\n]+", field.value.strip())[0].strip()
        if first:
            return first[:60]
    return "Integration gateway"


def build_remediations(
    code: str,
    message: str,
    level: str,
    plan: ArchitecturePlan,
    spec: ArchitectureSpec,
    node_id: Optional[str] = None,
    *,
    finding_key: Optional[str] = None,
) -> list[RemediationOption]:
    """Return user-facing choices to address a warn/fail finding."""
    if level == "pass":
        return []

    fid = finding_key or finding_id_from_item(
        {"code": code, "message": message, "node_id": node_id}
    )
    options: list[RemediationOption] = []

    def opt(
        action_id: str,
        label: str,
        description: str = "",
        **params: Any,
    ) -> RemediationOption:
        return {
            "id": action_id,
            "label": label,
            "description": description,
            "finding_id": fid,
            **params,
        }

    node = next((n for n in plan.graph.nodes if n.id == node_id), None) if node_id else None
    dec = _decision_index(plan).get(node_id) if node_id else None
    catalog = _catalog_for_node(plan, node_id) if node_id else []

    if code in ("catalog_empty",):
        options.append(
            opt(
                "refresh_catalog",
                "Refresh catalog search",
                "Re-query the agent index with your current specification.",
                action="refresh_catalog",
            )
        )

    if code in ("reuse_no_agent", "unknown_agent_id", "missing_decision"):
        if not catalog:
            options.append(
                opt(
                    "refresh_catalog",
                    "Refresh catalog search",
                    "Load catalog agents before assigning reuse.",
                    action="refresh_catalog",
                )
            )
        if catalog:
            for i, m in enumerate(catalog[:3]):
                options.append(
                    opt(
                        f"use_catalog_{m.agent_id}",
                        f"Use catalog: {m.name}",
                        f"Set reuse with {m.name} (score {m.score:.2f}).",
                        action="set_decision",
                        node_id=node_id,
                        decision="reuse",
                        agent_id=m.agent_id,
                        agent_name=m.name,
                        catalog_score=m.score,
                    )
                )
            if len(catalog) > 1:
                options.append(
                    opt(
                        "adapt_top_catalog",
                        "Adapt top catalog agent",
                        "Extend the best match with custom logic.",
                        action="set_decision",
                        node_id=node_id,
                        decision="adapt",
                        agent_id=catalog[0].agent_id,
                        agent_name=catalog[0].name,
                        catalog_score=catalog[0].score,
                    )
                )
        options.append(
            opt(
                "mark_build",
                "Mark as custom build",
                "No catalog agent — build this component new.",
                action="set_decision",
                node_id=node_id,
                decision="build",
            )
        )

    elif code in ("low_catalog_score", "weak_catalog_fit"):
        if len(catalog) > 1:
            for m in catalog[1:4]:
                options.append(
                    opt(
                        f"switch_catalog_{m.agent_id}",
                        f"Try: {m.name}",
                        f"Switch to alternate catalog agent (score {m.score:.2f}).",
                        action="set_decision",
                        node_id=node_id,
                        decision="reuse",
                        agent_id=m.agent_id,
                        agent_name=m.name,
                        catalog_score=m.score,
                    )
                )
        options.append(
            opt(
                "mark_build",
                "Build custom instead",
                "Drop catalog reuse for this step.",
                action="set_decision",
                node_id=node_id,
                decision="build",
            )
        )
        options.append(
            opt(
                "acknowledge_fit",
                "Accept current match",
                "Keep assignment; you reviewed fit manually.",
                action="acknowledge",
            )
        )

    elif code == "hitl_missing":
        options.append(
            opt(
                "add_human_step",
                "Add human approval step",
                "Insert an analyst review node into the flow.",
                action="add_human_node",
            )
        )
        options.append(
            opt(
                "acknowledge_hitl",
                "HITL handled outside diagram",
                "Human review happens in another system.",
                action="acknowledge",
            )
        )

    elif code == "integrations_gap":
        options.append(
            opt(
                "add_integration_gateway",
                f"Add step: {_spec_integrations_label(spec)}",
                "Add a gateway component named from your integrations spec.",
                action="add_gateway_node",
                gateway_label=_spec_integrations_label(spec),
            )
        )
        options.append(
            opt(
                "acknowledge_integrations",
                "Integrations are implicit",
                "Connections exist but are not labeled on the diagram.",
                action="acknowledge",
            )
        )

    elif code == "use_case_drift":
        options.append(
            opt(
                "acknowledge_use_case",
                "Reviewed — flow matches intent",
                "You confirmed the diagram matches the use case.",
                action="acknowledge",
            )
        )

    elif code == "open_question":
        options.append(
            opt(
                "resolve_question",
                "Mark question resolved",
                "Remove this open question from the plan.",
                action="remove_open_question",
                question_text=message,
            )
        )
        options.append(
            opt(
                "keep_question",
                "Keep tracking this question",
                "Leave open; acknowledge you are aware.",
                action="acknowledge",
            )
        )

    elif code in ("no_entry", "no_exit"):
        if code == "no_entry":
            options.append(
                opt(
                    "add_entry_gateway",
                    "Add entry gateway",
                    "Add a routing entry point before the pipeline.",
                    action="add_entry_gateway",
                )
            )
        options.append(
            opt(
                "acknowledge_flow_shape",
                "Flow shape is intentional",
                "Cyclic or multi-entry design is expected.",
                action="acknowledge",
            )
        )

    elif code == "empty_graph":
        options.append(
            opt(
                "acknowledge_regenerate",
                "Regenerate architecture",
                "Use Regenerate in the toolbar to replan from spec.",
                action="acknowledge",
            )
        )

    elif code == "dangling_edge":
        options.append(
            opt(
                "remove_dangling_edges",
                "Remove all invalid connections",
                "Delete every edge that references missing nodes.",
                action="remove_dangling_edges",
            )
        )
        if finding_key and finding_key.startswith("dangling_edge:"):
            parts = finding_key.split(":")
            if len(parts) >= 3:
                options.insert(
                    0,
                    opt(
                        "remove_this_edge",
                        "Remove this connection only",
                        f"Delete edge {parts[1]} → {parts[2]}.",
                        action="remove_specific_edge",
                        edge_from=parts[1],
                        edge_to=parts[2],
                    ),
                )

    elif code == "stale_decision":
        options.append(
            opt(
                "prune_stale_decisions",
                "Remove stale reuse decisions",
                "Drop decisions that reference deleted components.",
                action="prune_stale_decisions",
            )
        )

    elif code == "orphan_node":
        options.append(
            opt(
                "mark_build",
                "Mark as custom build",
                "Treat orphan step as intentional custom component.",
                action="set_decision",
                node_id=node_id,
                decision="build",
            )
        )
        options.append(
            opt(
                "acknowledge_orphan",
                "Orphan is intentional",
                "This step is off the main path by design.",
                action="acknowledge",
            )
        )

    elif code == "disconnected_subgraph":
        options.append(
            opt(
                "add_entry_gateway",
                "Add entry gateway",
                "Connect groups via a shared entry/router step.",
                action="add_entry_gateway",
            )
        )
        options.append(
            opt(
                "acknowledge_disconnected",
                "Separate flows are intentional",
                action="acknowledge",
            )
        )

    elif code == "duplicate_node_id":
        options.append(
            opt(
                "acknowledge_regenerate",
                "Regenerate architecture",
                "Regenerate to obtain unique component ids.",
                action="acknowledge",
            )
        )

    elif code == "spec_coverage_gap":
        options.append(
            opt(
                "acknowledge_spec_gap",
                "Covered elsewhere in design",
                f"Acknowledge {message[:60]}…",
                action="acknowledge",
            )
        )

    else:
        if level in ("warn", "fail"):
            options.append(
                opt(
                    "acknowledge_generic",
                    "Accept / reviewed",
                    "You reviewed this finding and accept the current design.",
                    action="acknowledge",
                )
            )

    if not options and level in ("warn", "fail"):
        options.append(
            opt(
                "acknowledge_generic",
                "Mark reviewed",
                "Acknowledge you reviewed this item.",
                action="acknowledge",
            )
        )

    return options


def enrich_validation_report(
    spec: ArchitectureSpec,
    plan: ArchitecturePlan,
    raw: dict,
) -> dict:
    """Attach finding ids, remediations, and resolution state to validation items."""
    resolutions = _resolutions_as_dicts(plan)
    enriched_items = []

    structural_fail = int(raw.get("structural_fail_count", 0))
    unresolved_actionable = 0

    for item in raw.get("items", []):
        code = item["code"]
        message = item["message"]
        level = item["level"]
        node_id = item.get("node_id")
        blocks = item.get("blocks_approval", level == "fail")
        fid = finding_id_from_item(item)
        resolved = fid in resolutions
        resolution = resolutions.get(fid)

        display_level = level
        display_message = message
        if resolved and _resolution_action(resolution) == "acknowledge":
            if blocks:
                display_message = (
                    f"Reviewed (approval still blocked): {message}"
                )
            else:
                display_level = "pass"
                display_message = f"Reviewed: {message}"

        actionable = level in ("warn", "fail") and code not in (
            "validation_scope",
        )
        if actionable and not resolved:
            unresolved_actionable += 1
        elif (
            actionable
            and resolved
            and blocks
            and _resolution_action(resolution) == "acknowledge"
        ):
            unresolved_actionable += 1

        remediations = (
            []
            if (display_level == "pass" and resolved)
            else build_remediations(
                code,
                message,
                level,
                plan,
                spec,
                node_id,
                finding_key=fid,
            )
        )

        enriched_items.append(
            {
                **item,
                "level": display_level,
                "message": display_message,
                "finding_id": fid,
                "finding_key": fid,
                "blocks_approval": blocks,
                "remediations": remediations,
                "resolved": resolved,
                "resolution": resolution,
            }
        )

    pass_count = sum(1 for i in enriched_items if i["level"] == "pass")
    warn_count = sum(1 for i in enriched_items if i["level"] == "warn")
    fail_count = sum(1 for i in enriched_items if i["level"] == "fail")
    overall = "pass"
    if fail_count > 0:
        overall = "fail"
    elif warn_count > 0:
        overall = "warn"

    can_approve = structural_fail == 0 and unresolved_actionable == 0
    if structural_fail > 0:
        approval_hint = (
            f"{structural_fail} structural failure(s) must be fixed — "
            "acknowledge alone does not unblock approval."
        )
    elif unresolved_actionable > 0:
        approval_hint = (
            f"{unresolved_actionable} issue(s) still need a fix or review."
        )
    else:
        approval_hint = "All checks passed or reviewed. You may approve this architecture."

    node_status = dict(raw.get("node_status", {}))
    for item in enriched_items:
        nid = item.get("node_id")
        if not nid or nid not in node_status:
            continue
        lvl = item["level"]
        if lvl == "fail":
            node_status[nid] = "fail"
        elif lvl == "warn" and node_status.get(nid) != "fail":
            node_status[nid] = "warn"

    return {
        **raw,
        "overall": overall,
        "pass_count": pass_count,
        "warn_count": warn_count,
        "fail_count": fail_count,
        "structural_fail_count": structural_fail,
        "unresolved_actionable_count": unresolved_actionable,
        "can_approve": can_approve,
        "approval_hint": approval_hint,
        "items": enriched_items,
        "node_status": node_status,
    }


def _prune_stale_decisions(plan: ArchitecturePlan) -> int:
    node_ids = {n.id for n in plan.graph.nodes}
    before = len(plan.reuse_decisions)
    plan.reuse_decisions = [
        d for d in plan.reuse_decisions if d.node_id in node_ids
    ]
    return before - len(plan.reuse_decisions)


def _remove_specific_edge(graph: GraphDraft, from_id: str, to_id: str) -> bool:
    before = len(graph.edges)
    graph.edges = [
        e
        for e in graph.edges
        if not (e.from_id == from_id and e.to_id == to_id)
    ]
    return len(graph.edges) < before


def _remove_dangling_edges(graph: GraphDraft) -> int:
    node_ids = {n.id for n in graph.nodes}
    before = len(graph.edges)
    graph.edges = [
        e
        for e in graph.edges
        if e.from_id in node_ids and e.to_id in node_ids
    ]
    return before - len(graph.edges)


def _add_human_node(plan: ArchitecturePlan) -> None:
    graph = plan.graph
    node_ids = {n.id for n in graph.nodes}
    in_degree = {nid: 0 for nid in node_ids}
    out_degree = {nid: 0 for nid in node_ids}
    for edge in graph.edges:
        if edge.from_id in out_degree:
            out_degree[edge.from_id] += 1
        if edge.to_id in in_degree:
            in_degree[edge.to_id] += 1

    sinks = [nid for nid in node_ids if out_degree[nid] == 0]
    new_id = _new_node_id("human")
    graph.nodes.append(
        GraphNode(
            id=new_id,
            label="Analyst approval (HITL)",
            type="human",
            description="Human-in-the-loop review per specification.",
        )
    )
    if sinks:
        for sid in sinks[:3]:
            graph.edges.append(GraphEdge(from_id=sid, to_id=new_id, label="review"))
    elif graph.nodes:
        prev = graph.nodes[-2].id if len(graph.nodes) > 1 else graph.nodes[0].id
        if prev != new_id:
            graph.edges.append(GraphEdge(from_id=prev, to_id=new_id))
    _upsert_decision(
        plan,
        new_id,
        "Analyst approval (HITL)",
        "build",
        rationale="Human-in-the-loop step (auto-registered on add).",
    )


def _add_gateway_node(plan: ArchitecturePlan, label: str) -> None:
    graph = plan.graph
    node_ids = {n.id for n in graph.nodes}
    in_degree = {nid: 0 for nid in node_ids}
    for edge in graph.edges:
        if edge.to_id in in_degree:
            in_degree[edge.to_id] += 1

    sources = [nid for nid in node_ids if in_degree[nid] == 0]
    new_id = _new_node_id("gateway")
    graph.nodes.append(
        GraphNode(
            id=new_id,
            label=label,
            type="gateway",
            description="Gateway for integrations / routing.",
        )
    )
    for sid in sources[:5]:
        graph.edges.append(GraphEdge(from_id=new_id, to_id=sid, label="route"))
    _upsert_decision(
        plan,
        new_id,
        label,
        "build",
        rationale="Gateway/routing step (auto-registered on add).",
    )


def _add_entry_gateway(plan: ArchitecturePlan) -> None:
    _add_gateway_node(plan, "Entry / routing")


def _remove_open_question(plan: ArchitecturePlan, finding_id_str: str, message: str) -> None:
    """Remove open question by index, exact text, or fuzzy match."""
    if finding_id_str.startswith("open_question:"):
        suffix = finding_id_str.split(":", 1)[1]
        if suffix.isdigit():
            idx = int(suffix)
            if 0 <= idx < len(plan.open_questions):
                plan.open_questions.pop(idx)
                return
    if message and message in plan.open_questions:
        plan.open_questions = [q for q in plan.open_questions if q != message]
        return
    msg_lower = (message or "").strip().lower()
    if msg_lower:
        plan.open_questions = [
            q
            for q in plan.open_questions
            if q.strip().lower() != msg_lower
            and msg_lower not in q.strip().lower()
            and q.strip().lower() not in msg_lower
        ]


def apply_remediation(
    spec: ArchitectureSpec,
    plan: ArchitecturePlan,
    finding_id_str: str,
    option_id: str,
    settings: Optional[Settings] = None,
) -> ArchitecturePlan:
    """
    Apply a remediation choice, re-validate, and persist resolution metadata on the plan.

    Prefer resolving the option from the plan's validation report (finding_id + option_id).
    """
    params = resolve_remediation_option(plan, finding_id_str, option_id, spec)
    action_id = option_id
    resolutions: dict[str, ResolutionRecord] = _resolutions_as_dicts(plan)

    action = params.get("action") or action_id
    if action_id.startswith("use_catalog_") or action_id.startswith("switch_catalog_"):
        action = "set_decision"
    elif action_id in (
        "adapt_top_catalog",
        "mark_build",
        "acknowledge_fit",
        "acknowledge_hitl",
        "acknowledge_integrations",
        "acknowledge_use_case",
        "acknowledge_flow_shape",
        "acknowledge_regenerate",
        "acknowledge_generic",
        "keep_question",
    ):
        if action_id.startswith("acknowledge") or action_id == "keep_question":
            action = "acknowledge"
        elif action_id == "mark_build":
            action = "set_decision"
        elif action_id == "adapt_top_catalog":
            action = "set_decision"

    if action == "acknowledge":
        resolutions[finding_id_str] = {
            "action": "acknowledge",
            "action_id": action_id,
            "label": params.get("label", action_id),
        }
    elif action == "set_decision":
        node_id = params.get("node_id")
        if not node_id:
            raise ValueError("node_id required for set_decision")
        node = next((n for n in plan.graph.nodes if n.id == node_id), None)
        if not node:
            raise ValueError(f"Unknown node_id: {node_id}")
        decision = params.get("decision", "build")
        agent_id = params.get("agent_id")
        agent_name = params.get("agent_name")
        catalog_score = params.get("catalog_score")
        if decision in ("reuse", "adapt") and agent_id:
            match = next(
                (m for m in plan.catalog_matches if m.agent_id == agent_id),
                None,
            )
            if match:
                agent_name = agent_name or match.name
                catalog_score = catalog_score if catalog_score is not None else match.score
            node.agent_id = agent_id
        else:
            node.agent_id = None
        _upsert_decision(
            plan,
            node_id,
            node.label,
            decision,
            agent_id=agent_id if decision in ("reuse", "adapt") else None,
            agent_name=agent_name,
            rationale=f"Updated via validation fix: {action_id}",
            catalog_score=catalog_score,
        )
        resolutions.pop(finding_id_str, None)
    elif action == "add_human_node":
        _add_human_node(plan)
        resolutions.pop(finding_id_str, None)
    elif action == "add_gateway_node":
        _add_gateway_node(
            plan,
            params.get("gateway_label")
            or params.get("label", "Integration gateway"),
        )
        resolutions.pop(finding_id_str, None)
    elif action == "add_entry_gateway":
        _add_entry_gateway(plan)
        resolutions.pop(finding_id_str, None)
    elif action == "remove_open_question":
        _remove_open_question(
            plan,
            finding_id_str,
            params.get("question_text", "") or "",
        )
        resolutions.pop(finding_id_str, None)
    elif action == "remove_dangling_edges":
        _remove_dangling_edges(plan.graph)
        resolutions.pop(finding_id_str, None)
    elif action == "remove_specific_edge":
        frm = params.get("edge_from", "")
        to = params.get("edge_to", "")
        if not frm and finding_id_str.startswith("dangling_edge:"):
            parts = finding_id_str.split(":")
            if len(parts) >= 3:
                frm, to = parts[1], parts[2]
        _remove_specific_edge(plan.graph, frm, to)
        resolutions.pop(finding_id_str, None)
    elif action == "prune_stale_decisions":
        _prune_stale_decisions(plan)
        resolutions.pop(finding_id_str, None)
    elif action == "refresh_catalog":
        if settings is None:
            raise ValueError("Catalog refresh requires API settings.")
        from services.architecture_planner import refresh_catalog_matches

        plan.catalog_matches = refresh_catalog_matches(spec, settings)
        resolutions.pop(finding_id_str, None)
    else:
        raise ValueError(f"Unknown remediation action: {action}")

    _prune_stale_decisions(plan)
    plan.validation_resolutions = _store_resolutions(resolutions)
    plan.validation = _build_validation_report(spec, plan)
    return plan


def _store_resolutions(
    resolutions: dict[str, ResolutionRecord],
) -> dict[str, Any]:
    from schemas.architecture_plan import ValidationResolution

    return {
        k: ValidationResolution.model_validate(v) for k, v in resolutions.items()
    }


def _build_validation_report(
    spec: ArchitectureSpec,
    plan: ArchitecturePlan,
) -> Any:
    from schemas.architecture_plan import ArchitectureValidationReport

    raw = validate_architecture_plan(spec, plan)
    enriched = enrich_validation_report(spec, plan, raw)
    return ArchitectureValidationReport.model_validate(enriched)


def revalidate_plan(spec: ArchitectureSpec, plan: ArchitecturePlan) -> ArchitecturePlan:
    """Re-run validation and enrichment without mutating the graph."""
    plan.validation = _build_validation_report(spec, plan)
    return plan
