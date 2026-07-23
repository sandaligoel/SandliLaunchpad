"""Azure AI Search integration client."""

from __future__ import annotations

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from tenacity import retry, stop_after_attempt, wait_exponential

from config import Settings


class AzureSearchIntegration:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client: SearchClient | None = None

    def get_client(self) -> SearchClient:
        if self._client is None:
            self._client = SearchClient(
                endpoint=self._settings.azure_search_service_endpoint,
                index_name=self._settings.azure_search_index_name,
                credential=AzureKeyCredential(self._settings.azure_search_api_key),
            )
        return self._client

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
    def _search_probe(self) -> int:
        client = self.get_client()
        results = client.search(search_text="*", top=1)
        return sum(1 for _ in results)

    async def health_check(self) -> dict[str, str]:
        try:
            self._search_probe()
            return {"status": "ok", "integration": "azure_search"}
        except Exception as exc:
            return {"status": "error", "integration": "azure_search", "detail": str(exc)}
