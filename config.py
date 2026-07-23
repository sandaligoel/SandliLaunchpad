"""Application settings loaded from environment / .env."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ConfigurationError(Exception):
    """Raised when required configuration is missing or invalid."""


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    gpt4_llm_model_deployment_name: str | None = Field(default=None, alias="GPT4_LLM_MODEL_DEPLOYMENT_NAME")
    azure_openai_api_base: str | None = Field(default=None, alias="AZURE_OPENAI_API_BASE")
    azure_openai_api_key: str | None = Field(default=None, alias="AZURE_OPENAI_API_KEY")
    azure_openai_api_version: str | None = Field(default=None, alias="AZURE_OPENAI_API_VERSION")
    embedding_model_deployment_name: str | None = Field(default=None, alias="EMBEDDING_MODEL_DEPLOYMENT_NAME")
    azure_search_service_endpoint: str | None = Field(default=None, alias="AZURE_SEARCH_SERVICE_ENDPOINT")
    azure_search_api_key: str | None = Field(default=None, alias="AZURE_SEARCH_API_KEY")
    azure_search_index_name: str = Field(default="dupont_email_demo", alias="AZURE_SEARCH_INDEX_NAME")
    eryl_vector_data: str | None = Field(default=None, alias="ERYL_VECTOR_DATA")
    eryl_vector_data_path: str | None = Field(default=None, alias="ERYL_VECTOR_DATA_PATH")
    eryl_local_context_module: str | None = Field(default=None, alias="ERYL_LOCAL_CONTEXT_MODULE")
    dry_run: bool = Field(default=False, alias="DRY_RUN")

    @model_validator(mode="after")
    def validate_required_for_live(self) -> Settings:
        if self.dry_run:
            return self
        required = {
            "GPT4_LLM_MODEL_DEPLOYMENT_NAME": self.gpt4_llm_model_deployment_name,
            "AZURE_OPENAI_API_BASE": self.azure_openai_api_base,
            "AZURE_OPENAI_API_KEY": self.azure_openai_api_key,
            "AZURE_OPENAI_API_VERSION": self.azure_openai_api_version,
            "EMBEDDING_MODEL_DEPLOYMENT_NAME": self.embedding_model_deployment_name,
            "AZURE_SEARCH_SERVICE_ENDPOINT": self.azure_search_service_endpoint,
            "AZURE_SEARCH_API_KEY": self.azure_search_api_key,
        }
        missing = [name for name, value in required.items() if not str(value or "").strip()]
        if missing:
            raise ConfigurationError(f"Missing required env var(s): {', '.join(missing)}")
        if not (self.eryl_vector_data or self.eryl_vector_data_path):
            raise ConfigurationError("Set ERYL_VECTOR_DATA or ERYL_VECTOR_DATA_PATH")
        return self

    def apply_to_process_env(self) -> None:
        """Mirror settings into os.environ for frozen reuse agents."""
        import os

        mapping = {
            "GPT4_LLM_MODEL_DEPLOYMENT_NAME": self.gpt4_llm_model_deployment_name,
            "AZURE_OPENAI_API_BASE": self.azure_openai_api_base,
            "AZURE_OPENAI_API_KEY": self.azure_openai_api_key,
            "AZURE_OPENAI_API_VERSION": self.azure_openai_api_version,
            "EMBEDDING_MODEL_DEPLOYMENT_NAME": self.embedding_model_deployment_name,
            "AZURE_SEARCH_SERVICE_ENDPOINT": self.azure_search_service_endpoint,
            "AZURE_SEARCH_API_KEY": self.azure_search_api_key,
            "AZURE_SEARCH_INDEX_NAME": self.azure_search_index_name,
        }
        if self.eryl_vector_data:
            mapping["ERYL_VECTOR_DATA"] = self.eryl_vector_data
        if self.eryl_vector_data_path:
            mapping["ERYL_VECTOR_DATA_PATH"] = self.eryl_vector_data_path
        if self.eryl_local_context_module:
            mapping["ERYL_LOCAL_CONTEXT_MODULE"] = self.eryl_local_context_module
        for key, value in mapping.items():
            if value is not None and str(value).strip():
                os.environ[key] = str(value)


@lru_cache
def get_settings(*, dry_run: bool = False) -> Settings:
    import os

    if dry_run:
        os.environ["DRY_RUN"] = "true"
        return Settings(dry_run=True)
    return Settings()


def clear_settings_cache() -> None:
    get_settings.cache_clear()
