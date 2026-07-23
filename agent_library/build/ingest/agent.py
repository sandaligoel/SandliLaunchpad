"""Ingest Docs — extract text and metadata from KYC documents."""

from __future__ import annotations

import mimetypes
from pathlib import Path
from typing import Any

import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from agent_library.base.agent import AgentMetadata, BaseAgent
from agent_library.build.ingest.config import MAX_FILE_SIZE_BYTES, SUPPORTED_EXTENSIONS
from config import ConfigurationError, get_settings

logger = structlog.get_logger(__name__)


class IngestAgent(BaseAgent):
    """Read KYC documents and produce normalized text for downstream validation."""

    metadata = AgentMetadata(
        agent_id="ingest",
        label="Ingest Docs",
        description="Ingest and extract text from KYC documents",
        inputs=["ingest"],
        outputs=["ingest_output"],
    )

    def validate_input(self, payload: dict[str, Any]) -> dict[str, Any]:
        ingest_input = payload.get("ingest")
        if ingest_input is None:
            raise ValueError("Missing required input field: ingest")
        if isinstance(ingest_input, str):
            path = Path(ingest_input)
            if path.exists():
                payload = {"ingest": {"file_path": str(path)}}
            else:
                payload = {
                    "ingest": {
                        "document_text": ingest_input,
                        "filename": "inline.txt",
                    }
                }
        elif isinstance(ingest_input, dict):
            if not ingest_input.get("file_path") and not ingest_input.get("document_text"):
                raise ValueError(
                    "ingest input must include file_path or document_text"
                )
        else:
            raise ValueError("ingest input must be a file path string or object")
        return payload

    def execute(self, payload: dict[str, Any]) -> dict[str, Any]:
        settings = get_settings()
        ingest_input = payload["ingest"]
        if settings.dry_run:
            return self._execute_dry_run(ingest_input)

        if ingest_input.get("document_text"):
            return self._build_output_from_text(
                text=str(ingest_input["document_text"]),
                filename=str(ingest_input.get("filename", "inline.txt")),
                source="inline",
            )

        file_path = Path(str(ingest_input["file_path"]))
        return self._ingest_file(file_path)

    def _execute_dry_run(self, ingest_input: dict[str, Any]) -> dict[str, Any]:
        if ingest_input.get("document_text"):
            text = str(ingest_input["document_text"])
            filename = str(ingest_input.get("filename", "dry_run.txt"))
        else:
            file_path = Path(str(ingest_input.get("file_path", "examples/sample_kyc_document.txt")))
            text = f"[dry-run] Would ingest document at {file_path}"
            filename = file_path.name
        return {
            "ingest_output": {
                "filename": filename,
                "content_type": mimetypes.guess_type(filename)[0] or "text/plain",
                "text_length": len(text),
                "document_text": text,
                "source": "dry_run",
                "dry_run": True,
            }
        }

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
        reraise=True,
    )
    def _ingest_file(self, file_path: Path) -> dict[str, Any]:
        if not file_path.exists():
            raise FileNotFoundError(f"Document not found: {file_path}")
        if not file_path.is_file():
            raise ValueError(f"Path is not a file: {file_path}")

        extension = file_path.suffix.lower()
        if extension not in SUPPORTED_EXTENSIONS:
            raise ValueError(
                f"Unsupported document type '{extension}'. "
                f"Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
            )

        size = file_path.stat().st_size
        if size > MAX_FILE_SIZE_BYTES:
            raise ValueError(
                f"Document exceeds maximum size of {MAX_FILE_SIZE_BYTES} bytes"
            )

        if extension == ".pdf":
            text = self._extract_pdf_text(file_path)
        elif extension == ".docx":
            text = self._extract_docx_text(file_path)
        else:
            text = file_path.read_text(encoding="utf-8", errors="replace")

        if not text.strip():
            raise ValueError(f"No extractable text found in document: {file_path.name}")

        logger.info(
            "ingest.complete",
            filename=file_path.name,
            text_length=len(text),
            extension=extension,
        )
        return self._build_output_from_text(
            text=text,
            filename=file_path.name,
            source=str(file_path.resolve()),
        )

    def _extract_pdf_text(self, file_path: Path) -> str:
        try:
            import fitz
        except ImportError as exc:
            raise ConfigurationError(
                "PyMuPDF is required for PDF ingestion. Install pymupdf."
            ) from exc

        document = fitz.open(file_path)
        try:
            pages = [page.get_text("text") for page in document]
        finally:
            document.close()
        return "\n".join(pages).strip()

    def _extract_docx_text(self, file_path: Path) -> str:
        try:
            from docx import Document
        except ImportError as exc:
            raise ConfigurationError(
                "python-docx is required for DOCX ingestion. Install python-docx."
            ) from exc

        document = Document(str(file_path))
        paragraphs = [paragraph.text for paragraph in document.paragraphs if paragraph.text]
        return "\n".join(paragraphs).strip()

    def _build_output_from_text(
        self,
        *,
        text: str,
        filename: str,
        source: str,
    ) -> dict[str, Any]:
        content_type = mimetypes.guess_type(filename)[0] or "text/plain"
        return {
            "ingest_output": {
                "filename": filename,
                "content_type": content_type,
                "text_length": len(text),
                "document_text": text,
                "source": source,
                "dry_run": False,
            }
        }

    def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        return super().run(payload)


def entrypoint(payload: dict[str, Any]) -> dict[str, Any]:
    return IngestAgent().run(payload)
