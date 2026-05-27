"""Domain-specific exceptions mapped to HTTP responses."""

from typing import Any


class KnowledgeBaseError(Exception):
    """Base exception for the knowledge retrieval system."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class PDFParseError(KnowledgeBaseError):
    """PDF could not be parsed or contains insufficient extractable text."""


class ExtractionError(KnowledgeBaseError):
    """LLM structured extraction failed after retries."""


class EmbeddingError(KnowledgeBaseError):
    """Embedding generation failed."""


class SearchIndexError(KnowledgeBaseError):
    """Azure AI Search operation failed."""


class ConfigurationError(KnowledgeBaseError):
    """Required configuration is missing or invalid."""
