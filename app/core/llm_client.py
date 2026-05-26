"""Shared Azure OpenAI client for structured JSON completions."""

from __future__ import annotations

import json
from typing import TypeVar

from openai import AsyncAzureOpenAI
from pydantic import BaseModel, ValidationError

from app.core.config import get_settings
from app.core.exceptions import ConfigurationError, ExtractionError
from app.core.retry import llm_retry

T = TypeVar("T", bound=BaseModel)


class AzureLLMClient:
    def __init__(self) -> None:
        settings = get_settings()
        if not settings.azure_openai_endpoint or not settings.azure_openai_api_key:
            raise ConfigurationError("Azure OpenAI credentials required")
        self.client = AsyncAzureOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            api_version=settings.azure_openai_api_version,
        )
        self.deployment = settings.azure_openai_chat_deployment
        self.temperature = settings.extraction_temperature

    @llm_retry()
    async def complete_structured(
        self,
        system: str,
        user: str,
        response_model: type[T],
        temperature: float | None = None,
    ) -> T:
        schema = response_model.model_json_schema()
        response = await self.client.chat.completions.create(
            model=self.deployment,
            temperature=temperature if temperature is not None else self.temperature,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": response_model.__name__,
                    "schema": schema,
                    "strict": False,
                },
            },
        )
        content = response.choices[0].message.content
        if not content:
            raise ExtractionError("Empty LLM response")
        try:
            return response_model.model_validate(json.loads(content))
        except (json.JSONDecodeError, ValidationError) as e:
            raise ExtractionError(
                f"Invalid LLM JSON for {response_model.__name__}",
                {"error": str(e), "raw": content[:500]},
            ) from e
