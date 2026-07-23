"""Workflow orchestration for the Eryl Semantic Search graph."""

from __future__ import annotations

import importlib
import json
from pathlib import Path
from typing import Any

from agent_runtime.adapters import (
    adapt_chain_output_to_node,
    adapt_dry_run_node_output,
    adapt_graph_input_to_chain,
    build_terminal_payload,
    merge_node_output_into_state,
)
from config import ConfigurationError, Settings, clear_settings_cache, get_settings

ROOT = Path(__file__).resolve().parent
WORKFLOW_PATH = ROOT / "workflow.json"
MANIFEST_PATH = ROOT / "workflow_manifest.json"

REUSE_AGENT_ID = "eryl_semantic_rag_agent_chain"
REUSE_ENTRYPOINT = "ErylChainRunner.run"

NODE_AGENT_MAP: dict[str, str] = {
    "query-transformer": REUSE_AGENT_ID,
    "eryl-selector": REUSE_AGENT_ID,
    "retriever": REUSE_AGENT_ID,
    "llm-answer-maker": REUSE_AGENT_ID,
    "critic": REUSE_AGENT_ID,
}

_chain_cache: dict[str, Any] | None = None


def load_workflow() -> dict[str, Any]:
    return json.loads(WORKFLOW_PATH.read_text(encoding="utf-8"))


def get_execution_order() -> list[str]:
    graph = load_workflow()["architecture_plan"]["graph"]
    return list(graph.get("execution_order") or [n["id"] for n in graph["nodes"]])


def discover_agents() -> dict[str, dict[str, Any]]:
    """Scan agent_library/reuse and agent_library/build for contract.json."""
    discovered: dict[str, dict[str, Any]] = {}
    for category in ("reuse", "build"):
        base = ROOT / "agent_library" / category
        if not base.is_dir():
            continue
        for agent_dir in sorted(base.iterdir()):
            contract_path = agent_dir / "contract.json"
            if not contract_path.is_file():
                continue
            contract = json.loads(contract_path.read_text(encoding="utf-8"))
            agent_id = contract.get("agent_id") or agent_dir.name
            module_path = f"agent_library.{category}.{agent_dir.name}.agent"
            discovered[agent_id] = {
                "agent_id": agent_id,
                "category": category,
                "path": str(agent_dir),
                "contract": contract,
                "module_path": module_path,
                "entrypoint": contract.get("entrypoint", REUSE_ENTRYPOINT),
            }
    return discovered


def build_manifest() -> dict[str, Any]:
    workflow = load_workflow()
    graph = workflow["architecture_plan"]["graph"]
    agents = discover_agents()
    steps = []
    for node_id in get_execution_order():
        agent_id = NODE_AGENT_MAP.get(node_id, "")
        agent_info = agents.get(agent_id, {})
        steps.append(
            {
                "node_id": node_id,
                "agent_id": agent_id,
                "entrypoint": agent_info.get("entrypoint", REUSE_ENTRYPOINT),
                "module_path": agent_info.get("module_path"),
                "type": "reuse" if agent_id in agents and agents[agent_id]["category"] == "reuse" else "build",
            }
        )
    manifest = {
        "title": workflow.get("title"),
        "execution_order": get_execution_order(),
        "steps": steps,
        "edges": graph.get("edges", []),
        "node_count": len(graph.get("nodes", [])),
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def _resolve_entrypoint_callable(module_path: str, entrypoint: str) -> Any:
    module = importlib.import_module(module_path)
    if "." in entrypoint:
        cls_name, method_name = entrypoint.split(".", 1)
        cls = getattr(module, cls_name)
        instance = cls()
        return getattr(instance, method_name)
    return getattr(module, entrypoint)


def _execute_chain(settings: Settings, payload: dict[str, Any]) -> dict[str, Any]:
    global _chain_cache
    if _chain_cache is not None:
        return _chain_cache

    settings.apply_to_process_env()
    chain_input = adapt_graph_input_to_chain(payload)
    agents = discover_agents()
    agent_info = agents[REUSE_AGENT_ID]
    run_fn = _resolve_entrypoint_callable(agent_info["module_path"], agent_info["entrypoint"])
    _chain_cache = run_fn(**chain_input)
    return _chain_cache


def _run_dry_workflow(start_node: str, payload: dict[str, Any]) -> dict[str, Any]:
    order = get_execution_order()
    if start_node not in order:
        raise ValueError(f"Unknown node_id: {start_node}")

    state: dict[str, Any] = dict(payload or {})
    state["dry_run"] = True
    start_idx = order.index(start_node)

    for node_id in order[start_idx:]:
        node_output = adapt_dry_run_node_output(node_id, state)
        merge_node_output_into_state(state, node_id, node_output)

    if start_node == order[0]:
        return build_terminal_payload(state)
    if start_node == order[-1]:
        return build_terminal_payload(state)
    return {"node_id": start_node, **state.get("node_outputs", {}).get(start_node, {})}


def _run_live_workflow(start_node: str, payload: dict[str, Any], settings: Settings) -> dict[str, Any]:
    order = get_execution_order()
    if start_node not in order:
        raise ValueError(f"Unknown node_id: {start_node}")

    state: dict[str, Any] = dict(payload or {})
    start_idx = order.index(start_node)
    chain_result = _execute_chain(settings, state)

    for node_id in order[start_idx:]:
        node_output = adapt_chain_output_to_node(node_id, chain_result)
        merge_node_output_into_state(state, node_id, node_output)

    if start_node == order[-1] or start_node == order[0]:
        return build_terminal_payload(state)
    return {"node_id": start_node, **state.get("node_outputs", {}).get(start_node, {})}


def run_workflow_from_node(node_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Execute the workflow starting at node_id with optional payload."""
    import os

    data = dict(payload or {})
    dry_run = os.environ.get("DRY_RUN", "").lower() in {"1", "true", "yes"}
    clear_settings_cache()

    try:
        settings = get_settings(dry_run=dry_run)
    except ConfigurationError:
        raise

    build_manifest()

    if dry_run:
        return _run_dry_workflow(node_id, data)

    return _run_live_workflow(node_id, data, settings)


def reset_chain_cache() -> None:
    global _chain_cache
    _chain_cache = None


if __name__ == "__main__":
    import os
    import sys

    os.environ.setdefault("DRY_RUN", "true")
    result = run_workflow_from_node("query-transformer", {"user_question": "What is the return policy?"})
    print(json.dumps(result, indent=2))
    sys.exit(0)
