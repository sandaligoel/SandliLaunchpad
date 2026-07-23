"""Document ingestion build node for the KYC pipeline."""

from __future__ import annotations

import json
import mimetypes
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import structlog
from docx import Document
from tenacity import retry, stop_after_attempt, wait_exponential

from agent_library.base.agent import AgentMetadata, BaseAgent
from config import Settings

logger = structlog.get_logger(__name__)

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt", ".json"}


@dataclass
class ExtractedDocument:
    document_path: str
    document_type: str
    text_content: str
    metadata: dict[str, Any]
    extracted_fields: dict[str, str]


class IngestDocsAgent(BaseAgent):
    """Read KYC documents from disk and extract structured content."""

    metadata = AgentMetadata(
        agent_id="ingest",
        label="Ingest Docs",
        description="Parse KYC documents and extract text plus candidate identity fields.",
    )

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or Settings()

    def validate_input(self, data: dict[str, Any]) -> dict[str, Any]:
        ingest_payload = data.get("ingest")
        if not isinstance(ingest_payload, dict):
            raise ValueError("ingest input must be an object with document_path")
        document_path = ingest_payload.get("document_path")
        if not document_path or not str(document_path).strip():
            raise ValueError("ingest.document_path is required")
        return data

    def execute(self, data: dict[str, Any]) -> dict[str, Any]:
        ingest_payload = data["ingest"]
        document_path = Path(str(ingest_payload["document_path"])).expanduser().resolve()
        dry_run = bool(data.get("dry_run", False))
        extracted = self._ingest_document(document_path, dry_run=dry_run)
        return {"ingest_output": asdict(extracted)}

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.5, min=0.5, max=4))
    def _ingest_document(self, document_path: Path, *, dry_run: bool) -> ExtractedDocument:
        if not document_path.exists():
            raise FileNotFoundError(f"Document not found: {document_path}")
        suffix = document_path.suffix.lower()
        if suffix not in SUPPORTED_EXTENSIONS:
            raise ValueError(
                f"Unsupported document type '{suffix}'. Supported: {sorted(SUPPORTED_EXTENSIONS)}"
            )

        logger.info("ingest.start", path=str(document_path), dry_run=dry_run)
        if suffix == ".pdf":
            text_content, metadata = self._read_pdf(document_path)
        elif suffix == ".docx":
            text_content, metadata = self._read_docx(document_path)
        elif suffix == ".txt":
            text_content, metadata = self._read_text(document_path)
        else:
            text_content, metadata = self._read_json(document_path)

        extracted_fields = self._extract_identity_fields(text_content, metadata)
        return ExtractedDocument(
            document_path=str(document_path),
            document_type=suffix.lstrip("."),
            text_content=text_content,
            metadata=metadata,
            extracted_fields=extracted_fields,
        )

    def _read_pdf(self, document_path: Path) -> tuple[str, dict[str, Any]]:
        import fitz

        with fitz.open(document_path) as pdf:
            pages = [page.get_text("text") for page in pdf]
            metadata = {
                "page_count": pdf.page_count,
                "mime_type": mimetypes.guess_type(document_path.name)[0] or "application/pdf",
            }
        return "\n".join(pages).strip(), metadata

    def _read_docx(self, document_path: Path) -> tuple[str, dict[str, Any]]:
        document = Document(document_path)
        paragraphs = [paragraph.text for paragraph in document.paragraphs if paragraph.text.strip()]
        metadata = {
            "paragraph_count": len(paragraphs),
            "mime_type": mimetypes.guess_type(document_path.name)[0]
            or "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        }
        return "\n".join(paragraphs).strip(), metadata

    def _read_text(self, document_path: Path) -> tuple[str, dict[str, Any]]:
        text_content = document_path.read_text(encoding="utf-8").strip()
        metadata = {
            "byte_length": document_path.stat().st_size,
            "mime_type": mimetypes.guess_type(document_path.name)[0] or "text/plain",
        }
        return text_content, metadata

    def _read_json(self, document_path: Path) -> tuple[str, dict[str, Any]]:
        payload = json.loads(document_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("JSON KYC documents must contain an object at the root")
        text_content = json.dumps(payload, indent=2, sort_keys=True)
        metadata = {
            "mime_type": "application/json",
            "keys": sorted(payload.keys()),
        }
        return text_content, metadata

    def _extract_identity_fields(
        self,
        text_content: str,
        metadata: dict[str, Any],
    ) -> dict[str, str]:
        fields: dict[str, str] = {}
        for line in text_content.splitlines():
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            normalized_key = key.strip().lower().replace(" ", "_")
            cleaned_value = value.strip()
            if cleaned_value:
                fields[normalized_key] = cleaned_value

        if "keys" in metadata and isinstance(metadata["keys"], list):
            for key in metadata["keys"]:
                if isinstance(key, str) and key not in fields:
                    fields[key] = fields.get(key, "")

        alias_map = {
            "name": "full_name",
            "customer_name": "full_name",
            "id": "government_id",
            "id_number": "government_id",
            "dob": "date_of_birth",
            "birth_date": "date_of_birth",
            "residential_address": "address",
        }
        normalized: dict[str, str] = {}
        for key, value in fields.items():
            target = alias_map.get(key, key)
            if value and target not in normalized:
                normalized[target] = value
        return normalized


def build_agent(settings: Settings | None = None) -> IngestDocsAgent:
    return IngestDocsAgent(settings=settings)


def execute(payload: dict[str, Any], settings: Settings | None = None) -> dict[str, Any]:
    return build_agent(settings).run(payload)
