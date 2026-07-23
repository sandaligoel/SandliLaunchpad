"""Workflow orchestration for the KYC Pipeline."""

from __future__ import annotations

import importlib
import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable

import structlog

from agent_runtime import adapters
from config import Settings, get_settings

logger = structlog.get_logger(__name__)

WORKFLOW_PATH = Path(__file__).resolve().parent / "workflow.json"
MANIFEST_PATH = Path(__file__).resolve().parent / "workflow_manifest.json"
AGENT_ROOTS = (
    Path(__file__).resolve().parent / "agent_library" / "build",
    Path(__file__).resolve().parent / "agent_library" / "reuse",
)

GraphPayload = dict[str, Any]
NodeHandler = Callable[[dict[str, Any], Settings], dict[str, Any]]


@lru_cache
def load_workflow_graph() -> GraphPayload:
    with WORKFLOW_PATH.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    return payload["architecture_plan"]["graph"]


def discover_agents() -> dict[str, dict[str, Any]]:
    """Scan build and reuse packages for contract.json entrypoints."""
    discovered: dict[str, dict[str, Any]] = {}
    for root in AGENT_ROOTS:
        if not root.exists():
            continue
        for contract_path in root.glob("*/contract.json"):
            with contract_path.open(encoding="utf-8") as handle:
                contract = json.load(handle)
            agent_id = contract.get("agent_id") or contract_path.parent.name
            entrypoint = contract["entrypoint"]
            module_name, function_name = entrypoint.rsplit(".", 1)
            module = importlib.import_module(module_name)
            handler = getattr(module, function_name)
            discovered[agent_id] = {
                "contract": contract,
                "handler": handler,
                "path": str(contract_path.parent),
            }
    return discovered


def _execution_steps(graph: GraphPayload) -> list[str]:
    execution_order = graph.get("execution_order")
    if execution_order:
        return list(execution_order)
    nodes = [node["id"] for node in graph.get("nodes", [])]
    edges = graph.get("edges", [])
    incoming = {edge["target"] for edge in edges}
    ordered = [node_id for node_id in nodes if node_id not in incoming]
    ordered.extend(node_id for node_id in nodes if node_id not in ordered)
    return ordered


def _prepare_node_input(
    node_id: str,
    payload: dict[str, Any],
    context: dict[str, Any],
) -> dict[str, Any]:
    dry_run = bool(context.get("dry_run", False))
    node_payload = dict(payload or {})
    node_payload.setdefault("dry_run", dry_run)

    if node_id == "ingest":
        if "ingest" not in node_payload and context.get("ingest_input"):
            node_payload["ingest"] = context["ingest_input"]
        adapted = adapters.adapt_graph_input_to_ingest(node_payload)
        adapted["dry_run"] = dry_run
        return adapted

    if node_id == "validate":
        if "validate" not in node_payload and "ingest_output" in context:
            adapted = adapters.adapt_ingest_output_to_validate(
                {"ingest_output": context["ingest_output"]}
            )
            adapted["dry_run"] = dry_run
            return adapted
        adapted = adapters.adapt_graph_input_to_validate(node_payload)
        adapted["dry_run"] = dry_run
        return adapted

    return node_payload


def run_workflow_from_node(
    node_id: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Execute the workflow starting from the requested node."""
    settings = get_settings()
    graph = load_workflow_graph()
    agents = discover_agents()
    steps = _execution_steps(graph)
    if node_id not in steps:
        raise ValueError(f"Unknown node_id '{node_id}'. Known nodes: {steps}")

    start_index = steps.index(node_id)
    context: dict[str, Any] = {
        "dry_run": bool((payload or {}).get("dry_run", False)),
    }
    if payload:
        context.update(payload)

    last_result: dict[str, Any] = {}
    for step_id in steps[start_index:]:
        if step_id not in agents:
            raise RuntimeError(f"No implementation discovered for node '{step_id}'")
        node_input = _prepare_node_input(step_id, payload or {}, context)
        handler = agents[step_id]["handler"]
        logger.info("workflow.execute_node", node_id=step_id)
        result = handler(node_input, settings)
        last_result = result
        if step_id == "ingest" and "ingest_output" in result:
            context["ingest_output"] = result["ingest_output"]
        if step_id == "validate" and "validate_output" in result:
            context["validate_output"] = result["validate_output"]

    return {
        "node_id": node_id,
        "execution_order": steps[start_index:],
        "result": last_result,
        "ingest_output": context.get("ingest_output"),
        "validate_output": context.get("validate_output"),
    }


def write_manifest() -> dict[str, Any]:
    graph = load_workflow_graph()
    agents = discover_agents()
    manifest = {
        "title": "KYC Pipeline",
        "execution_order": _execution_steps(graph),
        "nodes": [],
        "edges": graph.get("edges", []),
    }
    for node in graph.get("nodes", []):
        node_id = node["id"]
        agent_info = agents.get(node_id)
        manifest["nodes"].append(
            {
                "id": node_id,
                "label": node.get("label", node_id),
                "type": node.get("type", "agent"),
                "implementation": agent_info["path"] if agent_info else None,
                "entrypoint": agent_info["contract"]["entrypoint"] if agent_info else None,
            }
        )
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


if __name__ == "__main__":
    write_manifest()
    print(json.dumps(run_workflow_from_node("ingest", {"ingest": {"document_path": "examples/sample_kyc.txt"}}), indent=2))
