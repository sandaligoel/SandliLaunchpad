"""Workflow orchestration for the KYC pipeline."""

from __future__ import annotations

import importlib
import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable

import structlog

from agent_runtime.adapters import (
    adapt_graph_input_to_ingest,
    adapt_ingest_output_to_validate_input,
)
from config import get_settings

logger = structlog.get_logger(__name__)

REPO_ROOT = Path(__file__).resolve().parent
MANIFEST_PATH = REPO_ROOT / "workflow_manifest.json"
WORKFLOW_PATH = REPO_ROOT / "workflow.json"

ADAPTERS: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
    "adapt_ingest_output_to_validate_input": adapt_ingest_output_to_validate_input,
    "adapt_graph_input_to_ingest": adapt_graph_input_to_ingest,
}


@lru_cache
def load_manifest() -> dict[str, Any]:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


@lru_cache
def load_workflow_graph() -> dict[str, Any]:
    workflow = json.loads(WORKFLOW_PATH.read_text(encoding="utf-8"))
    return workflow["architecture_plan"]["graph"]


def discover_agents() -> dict[str, dict[str, Any]]:
    manifest = load_manifest()
    discovered: dict[str, dict[str, Any]] = {}
    for node_id, node_info in manifest["nodes"].items():
        discovered[node_id] = {
            "node_id": node_id,
            "type": node_info["type"],
            "entrypoint": node_info["entrypoint"],
            "contract_path": REPO_ROOT / node_info["contract"],
            "inputs": node_info["inputs"],
            "outputs": node_info["outputs"],
        }
    return discovered


def _resolve_entrypoint(entrypoint: str) -> Callable[[dict[str, Any]], dict[str, Any]]:
    module_path, function_name = entrypoint.split(":")
    module = importlib.import_module(module_path)
    function = getattr(module, function_name)
    return function


def _run_node(node_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    manifest = load_manifest()
    node_info = manifest["nodes"][node_id]
    entrypoint = _resolve_entrypoint(node_info["entrypoint"])
    logger.info("workflow.node.start", node_id=node_id)
    result = entrypoint(payload)
    logger.info("workflow.node.complete", node_id=node_id)
    return result


def _execution_order() -> list[str]:
    manifest = load_manifest()
    graph = load_workflow_graph()
    order = manifest.get("execution_order") or graph.get("execution_order")
    if not order:
        raise ValueError("Workflow execution order is not defined")
    return list(order)


def _edge_adapters() -> dict[tuple[str, str], str]:
    manifest = load_manifest()
    mapping: dict[tuple[str, str], str] = {}
    for edge in manifest.get("edges", []):
        mapping[(edge["source"], edge["target"])] = edge["adapter"]
    return mapping


def _enable_dry_run() -> None:
    import os

    os.environ["DRY_RUN"] = "true"
    get_settings.cache_clear()


def run_workflow_from_node(
    node_id: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Execute the workflow starting at the given node."""
    payload = payload or {}
    settings = get_settings()
    order = _execution_order()
    if node_id not in order:
        raise ValueError(f"Unknown workflow node: {node_id}")

    start_index = order.index(node_id)
    active_order = order[start_index:]
    adapters = _edge_adapters()
    node_outputs: dict[str, dict[str, Any]] = {}

    if node_id == "ingest":
        current_payload = adapt_graph_input_to_ingest(payload)
        ingest_input = current_payload.get("ingest", {})
        if settings.dry_run and not ingest_input.get("file_path") and not ingest_input.get(
            "document_text"
        ):
            current_payload = {
                "ingest": {"file_path": str(REPO_ROOT / "examples" / "sample_kyc_document.txt")}
            }
    elif node_id == "validate":
        if "validate" in payload:
            current_payload = payload
        elif "ingest_output" in payload:
            current_payload = {"validate": payload["ingest_output"]}
        else:
            current_payload = payload
    else:
        current_payload = payload

    for index, current_node in enumerate(active_order):
        if index > 0:
            previous_node = active_order[index - 1]
            adapter_name = adapters.get((previous_node, current_node))
            if adapter_name is None:
                current_payload = node_outputs[previous_node]
            else:
                adapter = ADAPTERS[adapter_name]
                current_payload = adapter(node_outputs[previous_node])

        if settings.dry_run:
            current_payload = {**current_payload, "dry_run": True}

        node_outputs[current_node] = _run_node(current_node, current_payload)

    final_node = active_order[-1]
    final_result = node_outputs[final_node]
    manifest = load_manifest()
    terminal_outputs = manifest.get("terminal_outputs", [])
    response: dict[str, Any] = {
        "workflow": manifest["title"],
        "dry_run": settings.dry_run,
        "executed_nodes": active_order,
        "node_results": node_outputs,
    }
    for node_output in node_outputs.values():
        for output_key, output_value in node_output.items():
            response[output_key] = output_value
    for output_key in terminal_outputs:
        if output_key in final_result:
            response[output_key] = final_result[output_key]
    return response


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Run the KYC workflow directly")
    parser.add_argument("--node", default="ingest", help="Start node id")
    parser.add_argument("--file", dest="file_path", help="Path to KYC document")
    parser.add_argument("--input-json", dest="input_json", help="JSON input file")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.dry_run:
        _enable_dry_run()

    input_payload: dict[str, Any] = {}
    if args.input_json:
        input_payload = json.loads(Path(args.input_json).read_text(encoding="utf-8"))
    elif args.file_path:
        input_payload = {"file_path": args.file_path}

    result = run_workflow_from_node(args.node, input_payload)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
