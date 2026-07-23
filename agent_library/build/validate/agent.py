"""Validate KYC — policy-driven completeness checks on ingested documents."""

from __future__ import annotations

import json
import re
from typing import Any

import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from agent_library.base.agent import AgentMetadata, BaseAgent
from agent_library.build.validate.config import (
    VALIDATION_STATUS_FAIL,
    VALIDATION_STATUS_INCOMPLETE,
    VALIDATION_STATUS_PASS,
)
from config import get_settings

logger = structlog.get_logger(__name__)


class ValidateAgent(BaseAgent):
    """Validate KYC document completeness using configurable policy rules."""

    metadata = AgentMetadata(
        agent_id="validate",
        label="Validate KYC",
        description="Validate ingested KYC documents against policy",
        inputs=["validate"],
        outputs=["validate_output"],
    )

    def validate_input(self, payload: dict[str, Any]) -> dict[str, Any]:
        validate_input = payload.get("validate")
        if validate_input is None:
            raise ValueError("Missing required input field: validate")
        if isinstance(validate_input, dict) and "ingest_output" in validate_input:
            payload = {"validate": validate_input["ingest_output"]}
        return payload

    def execute(self, payload: dict[str, Any]) -> dict[str, Any]:
        settings = get_settings()
        document = payload["validate"]
        document_text = str(document.get("document_text", ""))
        filename = str(document.get("filename", "unknown"))

        policy = self._load_policy(settings.resolve_policy_path())
        if settings.dry_run or document.get("dry_run"):
            return self._validate_dry_run(document, policy)

        return self._validate_document(document_text, filename, policy)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
        reraise=True,
    )
    def _validate_document(
        self,
        document_text: str,
        filename: str,
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        minimum_length = int(policy.get("minimum_text_length", 100))
        if len(document_text.strip()) < minimum_length:
            return self._build_output(
                filename=filename,
                status=VALIDATION_STATUS_FAIL,
                is_blocking=True,
                reason=f"Document text shorter than minimum {minimum_length} characters",
                extracted_fields={},
                missing_items=list(policy.get("required_sections", [])),
            )

        extracted_fields = self._extract_fields(document_text, policy)
        required_sections = list(policy.get("required_sections", []))
        missing_items = [
            field_name
            for field_name in required_sections
            if not extracted_fields.get(field_name)
        ]

        if missing_items:
            status = VALIDATION_STATUS_INCOMPLETE
            is_blocking = True
            reason = (
                f"KYC document missing required fields: {', '.join(missing_items)}"
            )
        else:
            status = VALIDATION_STATUS_PASS
            is_blocking = False
            reason = "All required KYC fields detected in document"

        logger.info(
            "validate.complete",
            filename=filename,
            status=status,
            missing_count=len(missing_items),
        )
        return self._build_output(
            filename=filename,
            status=status,
            is_blocking=is_blocking,
            reason=reason,
            extracted_fields=extracted_fields,
            missing_items=missing_items,
        )

    def _validate_dry_run(
        self,
        document: dict[str, Any],
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        filename = str(document.get("filename", "dry_run.txt"))
        required_sections = list(policy.get("required_sections", []))
        return self._build_output(
            filename=filename,
            status=VALIDATION_STATUS_PASS,
            is_blocking=False,
            reason="Dry-run validation completed without live document parsing",
            extracted_fields={field: "[dry-run]" for field in required_sections},
            missing_items=[],
            dry_run=True,
        )

    def _load_policy(self, policy_path: Any) -> dict[str, Any]:
        text = policy_path.read_text(encoding="utf-8")
        policy = json.loads(text)
        if not isinstance(policy, dict):
            raise ValueError("KYC policy must be a JSON object")
        return policy

    def _extract_fields(
        self,
        document_text: str,
        policy: dict[str, Any],
    ) -> dict[str, str]:
        field_patterns = policy.get("field_patterns", {})
        extracted: dict[str, str] = {}
        for field_name, patterns in field_patterns.items():
            value = self._match_first_pattern(document_text, patterns)
            if value:
                extracted[field_name] = value.strip()
        return extracted

    def _match_first_pattern(self, text: str, patterns: list[str]) -> str | None:
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.MULTILINE)
            if match:
                group = match.group(1) if match.lastindex else match.group(0)
                cleaned = group.strip().strip('"').strip("'")
                if cleaned:
                    return cleaned
        return None

    def _build_output(
        self,
        *,
        filename: str,
        status: str,
        is_blocking: bool,
        reason: str,
        extracted_fields: dict[str, str],
        missing_items: list[str],
        dry_run: bool = False,
    ) -> dict[str, Any]:
        return {
            "validate_output": {
                "filename": filename,
                "status": status,
                "is_blocking": is_blocking,
                "reason": reason,
                "extracted_fields": extracted_fields,
                "missing_items": missing_items,
                "dry_run": dry_run,
            }
        }

    def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        return super().run(payload)


def entrypoint(payload: dict[str, Any]) -> dict[str, Any]:
    return ValidateAgent().run(payload)
