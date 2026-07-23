"""CLI and FastAPI entrypoint for the Eryl Semantic Search workflow."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from config import ConfigurationError, Settings, clear_settings_cache, get_settings
from integrations.azure_openai import AzureOpenAIIntegration
from integrations.azure_search import AzureSearchIntegration
from run_workflow import run_workflow_from_node

ROOT = Path(__file__).resolve().parent

app = FastAPI(title="Eryl Semantic Search", version="1.0.0")


class IntakePayload(BaseModel):
    user_question: str = Field(..., min_length=1)
    analysis_type: str | None = None


class WorkflowPayload(BaseModel):
    data: dict[str, Any] = Field(default_factory=dict)


@app.get("/health")
async def health_endpoint() -> dict[str, Any]:
    return await run_health_checks()


@app.post("/workflows/query-transformer")
async def intake_query_transformer(payload: IntakePayload) -> dict[str, Any]:
    data = payload.model_dump(exclude_none=True)
    return run_workflow_from_node("query-transformer", data)


@app.post("/workflows/critic")
async def output_critic(payload: WorkflowPayload) -> dict[str, Any]:
    return run_workflow_from_node("critic", payload.data)


def load_input_json(path: Path) -> dict[str, Any]:
    content = path.read_text(encoding="utf-8").strip()
    if path.suffix.lower() == ".json":
        parsed = json.loads(content)
        if isinstance(parsed, dict):
            return parsed
        return {"user_question": str(parsed)}
    return {"user_question": content}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Eryl Semantic Search — query transform, retrieve, answer, critic evaluation.",
    )
    parser.add_argument("--health", action="store_true", help="Run integration health checks")
    parser.add_argument("--dry-run", action="store_true", help="Exercise orchestration without live external calls")
    parser.add_argument("--file", type=Path, help="Path to input file (JSON or plain text question)")
    parser.add_argument("--question", type=str, help="User question text")
    parser.add_argument("--input-json", type=Path, help="Path to JSON payload for the workflow")
    parser.add_argument("--node", type=str, default="query-transformer", help="Workflow node to start from")
    parser.add_argument("--serve", action="store_true", help="Start FastAPI via uvicorn")
    parser.add_argument("--host", type=str, default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    return parser.parse_args(argv)


async def run_health_checks() -> dict[str, Any]:
    clear_settings_cache()
    try:
        settings = get_settings(dry_run=False)
    except ConfigurationError as exc:
        raise SystemExit(str(exc)) from exc

    settings.apply_to_process_env()
    openai_integration = AzureOpenAIIntegration(settings)
    search_integration = AzureSearchIntegration(settings)
    results = await asyncio.gather(
        openai_integration.health_check(),
        search_integration.health_check(),
    )
    summary = {item["integration"]: item["status"] for item in results}
    return {"integrations": results, "summary": summary}


def build_payload(args: argparse.Namespace) -> dict[str, Any]:
    if args.input_json:
        return load_input_json(args.input_json)
    if args.file:
        return load_input_json(args.file)
    if args.question:
        return {"user_question": args.question}
    return {}


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    if args.serve:
        import uvicorn

        uvicorn.run("main:app", host=args.host, port=args.port, reload=False)
        return 0

    if args.health:
        result = asyncio.run(run_health_checks())
        print(json.dumps(result, indent=2))
        if any(item.get("status") != "ok" for item in result.get("integrations", [])):
            return 1
        return 0

    import os

    if args.dry_run:
        os.environ["DRY_RUN"] = "true"

    payload = build_payload(args)
    if not payload and not args.dry_run:
        print("Provide --question, --file, or --input-json", file=sys.stderr)
        return 2

    try:
        result = run_workflow_from_node(args.node, payload or {"user_question": "dry-run probe"})
        print(json.dumps(result, indent=2))
        return 0
    except ConfigurationError as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
