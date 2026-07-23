"""Integration tests for the KYC Pipeline workflow."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import config
from config import ConfigurationError, Settings
from main import app
from run_workflow import discover_agents, load_workflow_graph, run_workflow_from_node, write_manifest


ROOT = Path(__file__).resolve().parent.parent
SAMPLE_DOC = ROOT / "examples" / "sample_kyc.txt"


def test_discover_build_and_reuse_packages():
    agents = discover_agents()
    assert "ingest" in agents
    assert "validate" in agents
    assert any("build" in info["path"] for info in agents.values())
    assert (ROOT / "agent_library" / "reuse").exists()


def test_manifest_matches_graph():
    manifest = write_manifest()
    graph = load_workflow_graph()
    assert len(manifest["nodes"]) == len(graph["nodes"])
    assert manifest["execution_order"] == graph["execution_order"]


def test_adapters_and_wiring_contract():
    payload = {"document_path": str(SAMPLE_DOC), "dry_run": True}
    result = run_workflow_from_node("ingest", payload)
    assert "ingest_output" in result
    ingest_output = result["ingest_output"]
    assert ingest_output["document_type"] == "txt"
    assert ingest_output["extracted_fields"]["full_name"] == "Jane Doe"

    validate_result = run_workflow_from_node(
        "validate",
        {"ingest_output": ingest_output, "dry_run": True},
    )
    assert validate_result["validate_output"]["status"] == "pass"


def test_config_loads_without_required_secrets():
    settings = Settings()
    assert settings.app_name
    assert settings.required_field_names()


def test_dry_run_cli_exits_successfully():
    import main

    exit_code = main.main(["--dry-run"])
    assert exit_code == 0


def test_ingest_execute_real_fixture():
    from agent_library.build.ingest.agent import execute

    result = execute({"ingest": {"document_path": str(SAMPLE_DOC)}}, Settings())
    output = result["ingest_output"]
    assert output["text_content"]
    assert output["extracted_fields"]["government_id"] == "AB1234567"


def test_validate_execute_real_fixture():
    from agent_library.build.ingest.agent import execute as ingest_execute
    from agent_library.build.validate.agent import execute as validate_execute

    ingest_output = ingest_execute({"ingest": {"document_path": str(SAMPLE_DOC)}}, Settings())[
        "ingest_output"
    ]
    result = validate_execute({"validate": ingest_output}, Settings())
    validation = result["validate_output"]
    assert validation["status"] == "pass"
    assert validation["missing_fields"] == []


def test_http_intake_and_output_endpoints():
    client = TestClient(app)
    ingest_response = client.post(
        "/ingest",
        json={"document_path": str(SAMPLE_DOC), "dry_run": True},
    )
    assert ingest_response.status_code == 200
    ingest_body = ingest_response.json()
    assert ingest_body["ingest_output"]["extracted_fields"]["full_name"] == "Jane Doe"

    validate_response = client.post(
        "/validate",
        json={"ingest_output": ingest_body["ingest_output"], "dry_run": True},
    )
    assert validate_response.status_code == 200
    validate_body = validate_response.json()
    assert validate_body["validate_output"]["status"] == "pass"


def test_health_endpoint():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert "integrations" in body


def test_configuration_error_message():
    with pytest.raises(ConfigurationError) as exc:
        config.require_setting("EXAMPLE_SECRET", "")
    assert "Set EXAMPLE_SECRET" in str(exc.value)
