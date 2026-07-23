"""CLI and FastAPI entrypoint for the KYC pipeline."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import structlog
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from config import ConfigurationError, Settings, get_settings
from run_workflow import run_workflow_from_node

structlog.configure(
    processors=[
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ]
)
logger = structlog.get_logger(__name__)

app = FastAPI(
    title="KYC Pipeline",
    description="Automate document KYC checks",
    version="1.0.0",
)


class WorkflowPayload(BaseModel):
    data: dict[str, Any] = Field(default_factory=dict)


class HealthStatus(BaseModel):
    status: str
    details: dict[str, Any] = Field(default_factory=dict)


def _set_dry_run(enabled: bool) -> None:
    import os

    os.environ["DRY_RUN"] = "true" if enabled else "false"
    get_settings.cache_clear()


def run_health_checks() -> dict[str, Any]:
    settings = get_settings()
    checks: dict[str, Any] = {}

    try:
        policy_path = settings.resolve_policy_path()
        checks["kyc_policy"] = {
            "status": "ok",
            "path": str(policy_path),
        }
    except ConfigurationError as exc:
        checks["kyc_policy"] = {"status": "error", "error": str(exc)}

    overall = "ok" if all(item.get("status") == "ok" for item in checks.values()) else "error"
    return {"status": overall, "integrations": checks}


def _load_input_json(path: str) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _build_cli_payload(args: argparse.Namespace) -> dict[str, Any]:
    if args.input_json:
        return _load_input_json(args.input_json)
    if args.file:
        return {"file_path": args.file}
    if args.document_text:
        return {
            "document_text": args.document_text,
            "filename": args.filename or "cli_input.txt",
        }
    return {}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="KYC Pipeline — ingest and validate KYC documents"
    )
    parser.add_argument("--file", help="Path to a KYC document (PDF, DOCX, TXT)")
    parser.add_argument(
        "--document-text",
        dest="document_text",
        help="Inline document text instead of a file path",
    )
    parser.add_argument(
        "--filename",
        default="cli_input.txt",
        help="Filename label when using --document-text",
    )
    parser.add_argument("--input-json", help="Path to JSON workflow input")
    parser.add_argument("--health", action="store_true", help="Run integration health checks")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Execute workflow wiring without live external I/O",
    )
    parser.add_argument(
        "--serve",
        action="store_true",
        help="Start the FastAPI server with uvicorn",
    )
    parser.add_argument("--host", default="0.0.0.0", help="Uvicorn host")
    parser.add_argument("--port", type=int, default=8000, help="Uvicorn port")
    return parser.parse_args(argv)


@app.get("/health", response_model=HealthStatus)
async def health_endpoint() -> HealthStatus:
    result = run_health_checks()
    return HealthStatus(status=result["status"], details=result["integrations"])


@app.post("/workflows/ingest")
async def ingest_endpoint(payload: WorkflowPayload) -> dict[str, Any]:
    try:
        return run_workflow_from_node("ingest", payload.data)
    except ConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("ingest.failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/workflows/validate")
async def validate_endpoint(payload: WorkflowPayload) -> dict[str, Any]:
    try:
        return run_workflow_from_node("validate", payload.data)
    except ConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("validate.failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    if args.health:
        result = run_health_checks()
        print(json.dumps(result, indent=2))
        return 0 if result["status"] == "ok" else 1

    if args.dry_run:
        _set_dry_run(True)

    if args.serve:
        uvicorn.run("main:app", host=args.host, port=args.port, reload=False)
        return 0

    if args.dry_run and not (args.file or args.input_json or args.document_text):
        result = run_workflow_from_node("ingest", {})
        print(json.dumps(result, indent=2))
        return 0

    payload = _build_cli_payload(args)
    if not payload and not args.dry_run:
        print("Provide --file, --document-text, or --input-json", file=sys.stderr)
        return 1

    try:
        result = run_workflow_from_node("ingest", payload)
    except ConfigurationError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
