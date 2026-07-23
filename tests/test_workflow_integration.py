"""Integration tests for the Eryl Semantic Search workflow."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from config import ConfigurationError, clear_settings_cache, get_settings
from run_workflow import (
    build_manifest,
    discover_agents,
    get_execution_order,
    reset_chain_cache,
    run_workflow_from_node,
)

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(autouse=True)
def _reset_runtime_state(monkeypatch):
    monkeypatch.delenv("DRY_RUN", raising=False)
    clear_settings_cache()
    reset_chain_cache()
    yield
    clear_settings_cache()
    reset_chain_cache()


def test_discover_reuse_agent():
    agents = discover_agents()
    assert "eryl_semantic_rag_agent_chain" in agents
    assert agents["eryl_semantic_rag_agent_chain"]["category"] == "reuse"
    assert agents["eryl_semantic_rag_agent_chain"]["entrypoint"] == "ErylChainRunner.run"


def test_manifest_step_count_matches_graph():
    manifest = build_manifest()
    workflow = json.loads((ROOT / "workflow.json").read_text(encoding="utf-8"))
    node_count = len(workflow["architecture_plan"]["graph"]["nodes"])
    assert manifest["node_count"] == node_count
    assert len(manifest["steps"]) == node_count
    assert manifest["execution_order"] == get_execution_order()


def test_adapters_require_user_question():
    from agent_runtime.adapters import adapt_graph_input_to_chain

    with pytest.raises(ValueError, match="user_question"):
        adapt_graph_input_to_chain({})


def test_config_raises_configuration_error_when_missing(monkeypatch):
    monkeypatch.delenv("DRY_RUN", raising=False)
    for key in list(os.environ):
        if key.startswith(("AZURE_", "GPT4_", "EMBEDDING_", "ERYL_")):
            monkeypatch.delenv(key, raising=False)
    clear_settings_cache()
    with pytest.raises(ConfigurationError):
        get_settings(dry_run=False)


def test_dry_run_exits_successfully(monkeypatch):
    monkeypatch.setenv("DRY_RUN", "true")
    clear_settings_cache()
    result = run_workflow_from_node(
        "query-transformer",
        {"user_question": "What is the return policy?"},
    )
    assert result.get("dry_run") is True or "node_outputs" in result
    assert "final_answer" in result or "transformed_query" in result


def test_dry_run_node_outputs_shape():
    os.environ["DRY_RUN"] = "true"
    clear_settings_cache()
    result = run_workflow_from_node(
        "query-transformer",
        {"user_question": "Sample policy question"},
    )
    outputs = result.get("node_outputs", {})
    assert "query-transformer" in outputs
    assert outputs["query-transformer"]["transformed_query"] == "Sample policy question"
    assert "critic" in outputs
    assert "final_answer" in outputs["critic"]


def test_fastapi_intake_and_output_endpoints(monkeypatch):
    monkeypatch.setenv("DRY_RUN", "true")
    clear_settings_cache()
    from main import app

    client = TestClient(app)
    intake = client.post(
        "/workflows/query-transformer",
        json={"user_question": "What is the warranty period?"},
    )
    assert intake.status_code == 200
    body = intake.json()
    assert "transformed_query" in body or "node_outputs" in body or "final_answer" in body

    terminal = client.post(
        "/workflows/critic",
        json={"data": {"user_question": "What is the warranty period?"}},
    )
    assert terminal.status_code == 200
    terminal_body = terminal.json()
    assert "final_answer" in terminal_body or "node_outputs" in terminal_body


def test_main_cli_dry_run(tmp_path, monkeypatch):
    monkeypatch.setenv("DRY_RUN", "true")
    clear_settings_cache()
    from main import main

    assert main(["--dry-run", "--input-json", str(ROOT / "examples" / "sample_question.json")]) == 0
