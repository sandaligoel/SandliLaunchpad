"""Integration tests for the KYC pipeline."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from config import ConfigurationError, Settings, get_settings
from main import app, run_health_checks
from run_workflow import discover_agents, load_manifest, run_workflow_from_node

REPO_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_DOC = REPO_ROOT / "examples" / "sample_kyc_document.txt"


@pytest.fixture(autouse=True)
def reset_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DRY_RUN", raising=False)
    get_settings.cache_clear()


@pytest.fixture
def dry_run_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DRY_RUN", "true")
    get_settings.cache_clear()


def test_discover_build_and_reuse_paths() -> None:
    agents = discover_agents()
    assert "ingest" in agents
    assert "validate" in agents
    assert agents["ingest"]["type"] == "build"
    assert agents["validate"]["type"] == "build"
    assert (REPO_ROOT / "agent_library" / "build" / "ingest" / "contract.json").exists()
    assert (REPO_ROOT / "agent_library" / "build" / "validate" / "contract.json").exists()
    reuse_root = REPO_ROOT / "agent_library" / "reuse"
    assert reuse_root.exists()


def test_manifest_step_count_matches_graph() -> None:
    manifest = load_manifest()
    workflow = json.loads((REPO_ROOT / "workflow.json").read_text(encoding="utf-8"))
    graph_nodes = workflow["architecture_plan"]["graph"]["nodes"]
    assert len(manifest["nodes"]) == len(graph_nodes)
    assert manifest["execution_order"] == ["ingest", "validate"]


def test_adapter_wiring_required_inputs_present(dry_run_env: None) -> None:
    result = run_workflow_from_node("ingest", {"file_path": str(SAMPLE_DOC)})
    assert "ingest_output" in result
    assert "validate_output" in result
    assert result["executed_nodes"] == ["ingest", "validate"]
    validate_output = result["validate_output"]
    assert "status" in validate_output
    assert "missing_items" in validate_output


def test_config_raises_for_missing_policy(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KYC_POLICY_PATH", "/nonexistent/policy.json")
    get_settings.cache_clear()
    settings = Settings()
    with pytest.raises(ConfigurationError, match="KYC policy file not found"):
        settings.resolve_policy_path()


def test_dry_run_exits_successfully(dry_run_env: None) -> None:
    result = run_workflow_from_node("ingest", {})
    assert result["dry_run"] is True
    assert result["validate_output"]["dry_run"] is True


def test_ingest_execute_real_fixture() -> None:
    from agent_library.build.ingest.agent import IngestAgent

    agent = IngestAgent()
    result = agent.run({"ingest": {"file_path": str(SAMPLE_DOC)}})
    output = result["ingest_output"]
    assert output["filename"] == "sample_kyc_document.txt"
    assert output["text_length"] > 100
    assert "Acme Global Holdings Ltd." in output["document_text"]


def test_validate_execute_real_fixture() -> None:
    from agent_library.build.ingest.agent import IngestAgent
    from agent_library.build.validate.agent import ValidateAgent

    ingest_result = IngestAgent().run({"ingest": {"file_path": str(SAMPLE_DOC)}})
    validate_result = ValidateAgent().run({"validate": ingest_result["ingest_output"]})
    output = validate_result["validate_output"]
    assert output["status"] == "pass"
    assert output["is_blocking"] is False
    assert not output["missing_items"]
    assert output["extracted_fields"]["entity_name"] == "Acme Global Holdings Ltd."


def test_health_check_reports_policy_status() -> None:
    result = run_health_checks()
    assert result["status"] == "ok"
    assert result["integrations"]["kyc_policy"]["status"] == "ok"


def test_fastapi_intake_and_terminal_endpoints(dry_run_env: None) -> None:
    client = TestClient(app)
    ingest_response = client.post(
        "/workflows/ingest",
        json={"data": {"file_path": str(SAMPLE_DOC)}},
    )
    assert ingest_response.status_code == 200
    ingest_body = ingest_response.json()
    assert "ingest_output" in ingest_body

    validate_response = client.post(
        "/workflows/validate",
        json={"data": ingest_body["node_results"]["ingest"]},
    )
    assert validate_response.status_code == 200
    validate_body = validate_response.json()
    assert "validate_output" in validate_body
