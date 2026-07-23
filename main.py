"""CLI and FastAPI entrypoint for the KYC Pipeline workflow."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

import structlog
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from config import ConfigurationError, get_settings
from integrations.local_document_processing import health_check
from run_workflow import run_workflow_from_node, write_manifest

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer(),
    ]
)
logger = structlog.get_logger(__name__)

app = FastAPI(title="KYC Pipeline", version="1.0.0")


class WorkflowPayload(BaseModel):
    data: dict[str, Any] = Field(default_factory=dict)


class IngestRequest(BaseModel):
    document_path: str | None = None
    ingest: dict[str, Any] | None = None
    dry_run: bool = False


class ValidateRequest(BaseModel):
    validate_payload: dict[str, Any] | None = Field(default=None, alias="validate")
    ingest_output: dict[str, Any] | None = None
    dry_run: bool = False


def _build_payload_from_args(args: argparse.Namespace) -> dict[str, Any]:
    payload: dict[str, Any] = {"dry_run": args.dry_run}
    if args.input_json:
        input_path = Path(args.input_json).expanduser().resolve()
        payload.update(json.loads(input_path.read_text(encoding="utf-8")))
    if args.file:
        payload["document_path"] = str(Path(args.file).expanduser().resolve())
    if args.question:
        payload["question"] = args.question
    return payload


def _run_health_checks() -> dict[str, Any]:
    settings = get_settings()
    integration_result = asyncio.run(health_check())
    summary = {
        "app": settings.app_name,
        "status": integration_result["status"],
        "integrations": {
            integration_result["integration"]: integration_result,
        },
    }
    return summary


def _print_json(data: dict[str, Any]) -> None:
    print(json.dumps(data, indent=2, sort_keys=True))


@app.get("/health")
async def http_health() -> dict[str, Any]:
    settings = get_settings()
    integration_result = await health_check()
    return {
        "app": settings.app_name,
        "status": integration_result["status"],
        "integrations": {
            integration_result["integration"]: integration_result,
        },
    }


@app.post("/ingest")
async def http_ingest(request: IngestRequest) -> dict[str, Any]:
    payload: dict[str, Any] = {"dry_run": request.dry_run}
    if request.ingest is not None:
        payload["ingest"] = request.ingest
    elif request.document_path:
        payload["ingest"] = {"document_path": request.document_path}
    else:
        raise HTTPException(status_code=422, detail="Provide document_path or ingest payload")
    return run_workflow_from_node("ingest", payload)


@app.post("/validate")
async def http_validate(request: ValidateRequest) -> dict[str, Any]:
    payload: dict[str, Any] = {"dry_run": request.dry_run}
    if request.validate_payload is not None:
        payload["validate"] = request.validate_payload
    elif request.ingest_output is not None:
        payload["ingest_output"] = request.ingest_output
    else:
        raise HTTPException(status_code=422, detail="Provide validate or ingest_output payload")
    return run_workflow_from_node("validate", payload)


@app.post("/workflow/{node_id}")
async def http_workflow(node_id: str, payload: WorkflowPayload) -> dict[str, Any]:
    return run_workflow_from_node(node_id, payload.data)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the KYC Pipeline workflow")
    parser.add_argument("--file", help="Path to a KYC document to ingest")
    parser.add_argument("--question", help="Optional scalar input for future extensions")
    parser.add_argument("--input-json", help="Path to a JSON payload for the workflow")
    parser.add_argument("--node", default="ingest", help="Workflow node to start from")
    parser.add_argument("--health", action="store_true", help="Run integration health checks")
    parser.add_argument("--dry-run", action="store_true", help="Execute workflow without external I/O")
    parser.add_argument("--serve", action="store_true", help="Start the FastAPI server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    write_manifest()

    if args.health:
        summary = _run_health_checks()
        _print_json(summary)
        return 0 if summary["status"] == "ok" else 1

    if args.serve:
        uvicorn.run("main:app", host=args.host, port=args.port, reload=False)
        return 0

    if args.dry_run and not args.file and not args.input_json:
        sample_path = Path(__file__).resolve().parent / "examples" / "sample_kyc.txt"
        args.file = str(sample_path)

    if not args.dry_run and not args.file and not args.input_json:
        parser.error("Provide --file or --input-json for a live workflow run")

    payload = _build_payload_from_args(args)
    try:
        result = run_workflow_from_node(args.node, payload)
    except ConfigurationError as exc:
        logger.error("configuration.error", message=str(exc))
        print(str(exc), file=sys.stderr)
        return 1

    _print_json(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
