"""Pure I/O shape adapters between workflow nodes."""

from __future__ import annotations

from typing import Any


def adapt_graph_input_to_ingest(payload: dict[str, Any]) -> dict[str, Any]:
    """Normalize caller payload into the ingest node input contract."""
    if "ingest" in payload:
        ingest_value = payload["ingest"]
        if isinstance(ingest_value, dict):
            return {"ingest": ingest_value}
        if isinstance(ingest_value, str):
            return {"ingest": {"document_path": ingest_value}}
    if "document_path" in payload:
        return {"ingest": {"document_path": payload["document_path"]}}
    if "file_path" in payload:
        return {"ingest": {"document_path": payload["file_path"]}}
    return {"ingest": dict(payload)}


def adapt_ingest_output_to_validate(ingest_result: dict[str, Any]) -> dict[str, Any]:
    """Map ingest node output to validate node input."""
    ingest_output = ingest_result.get("ingest_output")
    if ingest_output is None:
        ingest_output = {
            key: value
            for key, value in ingest_result.items()
            if key not in {"ingest", "ingest_output", "dry_run"}
        }
    return {"validate": ingest_output}


def adapt_graph_input_to_validate(payload: dict[str, Any]) -> dict[str, Any]:
    """Normalize direct validate invocations."""
    if "validate" in payload:
        return {"validate": payload["validate"]}
    if "ingest_output" in payload:
        return {"validate": payload["ingest_output"]}
    return {"validate": dict(payload)}
