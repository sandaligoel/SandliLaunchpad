"""Validate KYC build node for the KYC pipeline."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any

import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from agent_library.base.agent import AgentMetadata, BaseAgent
from config import Settings

logger = structlog.get_logger(__name__)


@dataclass
class ValidationCheck:
    name: str
    passed: bool
    message: str


@dataclass
class ValidationResult:
    status: str
    checks: list[ValidationCheck]
    missing_fields: list[str]
    issues: list[str]
    extracted_fields: dict[str, str]


class ValidateKycAgent(BaseAgent):
    """Apply deterministic KYC completeness and format checks."""

    metadata = AgentMetadata(
        agent_id="validate",
        label="Validate KYC",
        description="Validate ingested KYC documents against required fields and formats.",
    )

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or Settings()

    def validate_input(self, data: dict[str, Any]) -> dict[str, Any]:
        validate_payload = data.get("validate")
        if not isinstance(validate_payload, dict):
            raise ValueError("validate input must be an object produced by ingest")
        if not validate_payload.get("text_content") and not validate_payload.get("extracted_fields"):
            raise ValueError("validate input must include text_content or extracted_fields")
        return data

    def execute(self, data: dict[str, Any]) -> dict[str, Any]:
        validate_payload = data["validate"]
        result = self._validate_payload(validate_payload)
        return {"validate_output": asdict(result)}

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.5, min=0.5, max=4))
    def _validate_payload(self, payload: dict[str, Any]) -> ValidationResult:
        text_content = str(payload.get("text_content", ""))
        extracted_fields = {
            str(key): str(value)
            for key, value in dict(payload.get("extracted_fields", {})).items()
            if value
        }
        checks: list[ValidationCheck] = []
        issues: list[str] = []

        min_length = self.settings.kyc_min_document_text_length
        length_ok = len(text_content.strip()) >= min_length
        checks.append(
            ValidationCheck(
                name="document_text_length",
                passed=length_ok,
                message=(
                    f"Document contains at least {min_length} characters"
                    if length_ok
                    else f"Document text shorter than required minimum of {min_length} characters"
                ),
            )
        )
        if not length_ok:
            issues.append(checks[-1].message)

        missing_fields: list[str] = []
        for field_name in self.settings.required_field_names():
            value = extracted_fields.get(field_name, "").strip()
            passed = bool(value)
            checks.append(
                ValidationCheck(
                    name=f"required_field:{field_name}",
                    passed=passed,
                    message=(
                        f"Required field '{field_name}' is present"
                        if passed
                        else f"Required field '{field_name}' is missing"
                    ),
                )
            )
            if not passed:
                missing_fields.append(field_name)
                issues.append(checks[-1].message)

        government_id = extracted_fields.get("government_id", "").strip()
        id_pattern = re.compile(self.settings.kyc_id_pattern)
        id_ok = bool(government_id) and bool(id_pattern.match(government_id))
        checks.append(
            ValidationCheck(
                name="government_id_format",
                passed=id_ok,
                message=(
                    "Government ID matches configured format"
                    if id_ok
                    else "Government ID is missing or does not match configured format"
                ),
            )
        )
        if not id_ok:
            issues.append(checks[-1].message)

        dob = extracted_fields.get("date_of_birth", "").strip()
        dob_ok = self._is_valid_date(dob)
        checks.append(
            ValidationCheck(
                name="date_of_birth_format",
                passed=dob_ok,
                message=(
                    "Date of birth is a valid ISO date"
                    if dob_ok
                    else "Date of birth is missing or not a valid ISO date (YYYY-MM-DD)"
                ),
            )
        )
        if not dob_ok:
            issues.append(checks[-1].message)

        failed_checks = [check for check in checks if not check.passed]
        if not failed_checks:
            status = "pass"
        elif missing_fields:
            status = "fail"
        else:
            status = "review"

        logger.info(
            "validate.complete",
            status=status,
            failed_checks=len(failed_checks),
            missing_fields=missing_fields,
        )
        return ValidationResult(
            status=status,
            checks=checks,
            missing_fields=missing_fields,
            issues=issues,
            extracted_fields=extracted_fields,
        )

    def _is_valid_date(self, value: str) -> bool:
        if not value:
            return False
        try:
            datetime.strptime(value, "%Y-%m-%d")
        except ValueError:
            return False
        return True


def build_agent(settings: Settings | None = None) -> ValidateKycAgent:
    return ValidateKycAgent(settings=settings)


def execute(payload: dict[str, Any], settings: Settings | None = None) -> dict[str, Any]:
    return build_agent(settings).run(payload)
