"""Application configuration loaded from environment variables."""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Must match Azure OpenAI embedding deployment (text-embedding-3-small → 1536; -large → 3072)
EMBEDDING_DIMENSIONS = 1536

_REQUIRED_VARS = (
    "AZURE_OPENAI_ENDPOINT",
    "AZURE_OPENAI_API_KEY",
    "AZURE_OPENAI_API_VERSION",
    "AZURE_OPENAI_CHAT_DEPLOYMENT",
    "AZURE_OPENAI_EMBEDDING_DEPLOYMENT",
    "AZURE_SEARCH_ENDPOINT",
    "AZURE_SEARCH_API_KEY",
    "AZURE_SEARCH_INDEX_NAME",
)


def _mask_secret(value: str, visible: int = 4) -> str:
    """Return a masked representation of a secret, showing only the last N characters."""
    if not value:
        return "(empty)"
    if len(value) <= visible:
        return "*" * len(value)
    return "*" * (len(value) - visible) + value[-visible:]


@dataclass(frozen=True)
class Settings:
    """Typed configuration for the agent catalog pipeline."""

    azure_openai_endpoint: str
    azure_openai_api_key: str
    azure_openai_api_version: str
    azure_openai_chat_deployment: str
    azure_openai_embedding_deployment: str
    azure_search_endpoint: str
    azure_search_api_key: str
    azure_search_index_name: str
    pdf_path: str
    log_level: str

    @classmethod
    def from_env(cls) -> Settings:
        """Load settings from environment variables."""
        return cls(
            azure_openai_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT", "").strip(),
            azure_openai_api_key=os.getenv("AZURE_OPENAI_API_KEY", "").strip(),
            azure_openai_api_version=os.getenv("AZURE_OPENAI_API_VERSION", "").strip(),
            azure_openai_chat_deployment=os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT", "").strip(),
            azure_openai_embedding_deployment=os.getenv(
                "AZURE_OPENAI_EMBEDDING_DEPLOYMENT", ""
            ).strip(),
            azure_search_endpoint=os.getenv("AZURE_SEARCH_ENDPOINT", "").strip(),
            azure_search_api_key=os.getenv("AZURE_SEARCH_API_KEY", "").strip(),
            azure_search_index_name=os.getenv("AZURE_SEARCH_INDEX_NAME", "").strip(),
            pdf_path=os.getenv(
                "PDF_PATH", "./data/spec.json"
            ).strip(),  # .json (direct) or .pdf (LLM extract)
            log_level=os.getenv("LOG_LEVEL", "INFO").strip().upper(),
        )

    def validate(self) -> None:
        """Raise ValueError if any required environment variable is missing."""
        missing = []
        for var in _REQUIRED_VARS:
            if not getattr(self, _field_name(var)):
                missing.append(var)
        if missing:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing)}. "
                "Copy .env.example to .env and fill in your Azure credentials."
            )

    def print_masked_summary(self) -> None:
        """Log a masked summary of configuration (endpoints visible, keys masked)."""
        logger.info("Configuration loaded:")
        logger.info("  AZURE_OPENAI_ENDPOINT: %s", self.azure_openai_endpoint)
        logger.info("  AZURE_OPENAI_API_KEY: %s", _mask_secret(self.azure_openai_api_key))
        logger.info("  AZURE_OPENAI_API_VERSION: %s", self.azure_openai_api_version)
        logger.info("  AZURE_OPENAI_CHAT_DEPLOYMENT: %s", self.azure_openai_chat_deployment)
        logger.info(
            "  AZURE_OPENAI_EMBEDDING_DEPLOYMENT: %s",
            self.azure_openai_embedding_deployment,
        )
        logger.info("  AZURE_SEARCH_ENDPOINT: %s", self.azure_search_endpoint)
        logger.info("  AZURE_SEARCH_API_KEY: %s", _mask_secret(self.azure_search_api_key))
        logger.info("  AZURE_SEARCH_INDEX_NAME: %s", self.azure_search_index_name)
        logger.info("  PDF_PATH: %s", self.pdf_path)
        logger.info("  LOG_LEVEL: %s", self.log_level)


def _field_name(env_var: str) -> str:
    """Map an environment variable name to a Settings field name."""
    return env_var.lower()


def get_settings() -> Settings:
    """Load, validate, and return application settings."""
    settings = Settings.from_env()
    settings.validate()
    return settings


def configure_logging(level: str | None = None) -> None:
    """Configure root logging from settings or an explicit level."""
    log_level = (level or os.getenv("LOG_LEVEL", "INFO")).upper()
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
