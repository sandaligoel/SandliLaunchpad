"""Application configuration for the KYC Pipeline workflow."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ConfigurationError(RuntimeError):
    """Raised when required configuration is missing or invalid."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = Field(default="KYC Pipeline", alias="APP_NAME")
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(
        default="INFO",
        alias="LOG_LEVEL",
    )
    kyc_required_fields: str = Field(
        default="full_name,government_id,date_of_birth,address",
        alias="KYC_REQUIRED_FIELDS",
    )
    kyc_id_pattern: str = Field(
        default=r"^[A-Z0-9-]{6,20}$",
        alias="KYC_ID_PATTERN",
    )
    kyc_min_document_text_length: int = Field(
        default=20,
        alias="KYC_MIN_DOCUMENT_TEXT_LENGTH",
    )

    def required_field_names(self) -> list[str]:
        return [field.strip() for field in self.kyc_required_fields.split(",") if field.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


def require_setting(name: str, value: str | None) -> str:
    if value is None or not str(value).strip():
        raise ConfigurationError(f"Set {name}")
    return str(value).strip()
