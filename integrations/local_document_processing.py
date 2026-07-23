"""Local integration health checks for the KYC pipeline."""

from __future__ import annotations

import importlib
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


async def health_check() -> dict[str, Any]:
    """Verify local document-processing dependencies are importable."""
    checks: dict[str, str] = {}
    for module_name in ("fitz", "docx", "tenacity", "structlog"):
        try:
            importlib.import_module(module_name)
            checks[module_name] = "ok"
        except ImportError as exc:
            checks[module_name] = f"error: {exc}"
            logger.error("health.import_failed", module=module_name, error=str(exc))

    status = "ok" if all(value == "ok" for value in checks.values()) else "degraded"
    return {"integration": "local_document_processing", "status": status, "checks": checks}
