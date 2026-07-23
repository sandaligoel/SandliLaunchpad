"""Azure OpenAI integration client."""

from __future__ import annotations

from typing import Any

from openai import AzureOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from config import Settings


class AzureOpenAIIntegration:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client: AzureOpenAI | None = None

    def get_client(self) -> AzureOpenAI:
        if self._client is None:
            self._client = AzureOpenAI(
                api_key=self._settings.azure_openai_api_key,
                api_version=self._settings.azure_openai_api_version,
                azure_endpoint=self._settings.azure_openai_api_base,
            )
        return self._client

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
    def _list_models(self) -> Any:
        client = self.get_client()
        return client.models.list()

    async def health_check(self) -> dict[str, str]:
        try:
            self._list_models()
            return {"status": "ok", "integration": "azure_openai"}
        except Exception as exc:
            return {"status": "error", "integration": "azure_openai", "detail": str(exc)}
