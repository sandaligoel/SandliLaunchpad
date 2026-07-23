"""Pure I/O shape adapters between workflow nodes."""

from __future__ import annotations

from typing import Any


def adapt_ingest_output_to_validate_input(ingest_result: dict[str, Any]) -> dict[str, Any]:
    """Map ingest node output to validate node input contract."""
    ingest_output = ingest_result.get("ingest_output")
    if ingest_output is None:
        ingest_output = ingest_result
    return {"validate": ingest_output}


def adapt_graph_input_to_ingest(payload: dict[str, Any]) -> dict[str, Any]:
    """Normalize external workflow input for the ingest node."""
    if "ingest" in payload:
        return payload
    if "file_path" in payload:
        return {"ingest": {"file_path": payload["file_path"]}}
    if "document_path" in payload:
        return {"ingest": {"file_path": payload["document_path"]}}
    if "document_text" in payload:
        return {
            "ingest": {
                "document_text": payload["document_text"],
                "filename": payload.get("filename", "input.txt"),
            }
        }
    return {"ingest": payload}
