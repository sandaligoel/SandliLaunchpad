"""Application configuration via environment variables."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "agent-knowledge-retrieval"
    app_env: Literal["development", "staging", "production"] = "development"
    log_level: str = "INFO"
    api_prefix: str = "/api/v1"
    cors_origins: list[str] = Field(default_factory=lambda: ["*"])

    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = ""
    azure_openai_api_version: str = "2024-12-01-preview"
    azure_openai_chat_deployment: str = "gpt-5.4"
    azure_openai_embedding_deployment: str = "text-embedding-3-large"
    azure_openai_embedding_dimensions: int = 3072

    azure_search_endpoint: str = ""
    azure_search_api_key: str = ""
    azure_search_index_name: str = "ai-architecture-knowledge"
    azure_search_create_index_on_startup: bool = True
    azure_search_semantic_config_name: str = "architecture-semantic"

    max_chunk_chars: int = 6000
    chunk_overlap_chars: int = 400
    extraction_max_retries: int = 3
    extraction_temperature: float = 0.1
    embedding_batch_size: int = 16
    pdf_parse_page_batch_size: int = 50

    default_search_top_k: int = 10
    hybrid_vector_weight: float = 0.6

    schema_version: str = "1.0.0"
    default_solution_agents_pdf: str = "data/documents/solution_agents.pdf"
    solution_catalog_auto_detect: bool = True

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors(cls, v: object) -> list[str]:
        if isinstance(v, str):
            import json

            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v  # type: ignore[return-value]

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
