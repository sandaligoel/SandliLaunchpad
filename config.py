"""Application configuration loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ConfigurationError(Exception):
    """Raised when required configuration is missing or invalid."""


class Settings(BaseSettings):
    """Central settings for the KYC pipeline."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    kyc_policy_path: str = Field(
        default="config/kyc_policy.json",
        description="Path to the KYC completeness policy JSON file",
    )
    dry_run: bool = Field(
        default=False,
        description="When true, skip live external I/O boundaries",
    )

    def resolve_policy_path(self) -> Path:
        path = Path(self.kyc_policy_path)
        if not path.is_absolute():
            path = Path(__file__).resolve().parent / path
        if not path.exists():
            raise ConfigurationError(
                f"KYC policy file not found at {path}. "
                "Set KYC_POLICY_PATH to a valid policy JSON file."
            )
        return path


@lru_cache
def get_settings() -> Settings:
    return Settings()
