"""Ingest pre-structured project spec JSON (no PDF / LLM extraction)."""

from __future__ import annotations

import json
import uuid
from pathlib import Path

import structlog

from backend.app.core.logging import get_logger
from backend.app.schemas.api import IngestPDFResponse
from backend.app.schemas.spec_import import ProjectSpecDocument
from backend.app.services.indexing import IndexingService
from backend.app.services.spec_mapper import spec_to_project_knowledge
from backend.app.utils.ids import content_hash, generate_project_id

logger = get_logger(__name__)

DEFAULT_SPEC_PATH = Path(__file__).resolve().parents[3] / "data" / "specs" / "spec.json"


class SpecIngestionService:
    """Loads structured spec JSON and indexes into Azure AI Search."""

    def __init__(self) -> None:
        self.indexing = IndexingService()

    async def ingest_spec(
        self,
        spec: ProjectSpecDocument,
        source_filename: str = "spec.json",
        correlation_id: str | None = None,
    ) -> IngestPDFResponse:
        cid = correlation_id or str(uuid.uuid4())
        structlog.contextvars.bind_contextvars(correlation_id=cid)

        raw = spec.model_dump_json()
        file_hash = content_hash(raw)
        project_id = generate_project_id(
            source_filename, file_hash, spec.project.name
        )

        logger.info(
            "spec_ingestion_started",
            project=spec.project.name,
            agents=len(spec.agents),
            correlation_id=cid,
        )

        project = spec_to_project_knowledge(spec, project_id, source_filename)
        indexed_count, breakdown = await self.indexing.build_and_index(
            project, chunks=[], filename=source_filename
        )

        logger.info(
            "spec_ingestion_completed",
            project_id=project_id,
            entities_indexed=indexed_count,
        )

        return IngestPDFResponse(
            success=True,
            project_id=project_id,
            project_name=project.project_name,
            filename=source_filename,
            pages_processed=0,
            chunks_created=0,
            entities_indexed=indexed_count,
            entity_breakdown=breakdown,
            project_knowledge=project,
            correlation_id=cid,
            warnings=[],
        )

    async def ingest_spec_file(
        self,
        path: Path | None = None,
        correlation_id: str | None = None,
    ) -> IngestPDFResponse:
        spec_path = path or DEFAULT_SPEC_PATH
        if not spec_path.exists():
            from backend.app.core.exceptions import KnowledgeBaseError

            raise KnowledgeBaseError(
                f"Spec file not found: {spec_path}",
                {"path": str(spec_path)},
            )
        data = json.loads(spec_path.read_text(encoding="utf-8"))
        spec = ProjectSpecDocument.model_validate(data)
        return await self.ingest_spec(
            spec,
            source_filename=spec_path.name,
            correlation_id=correlation_id,
        )

    async def ingest_spec_bytes(
        self,
        content: bytes,
        filename: str = "spec.json",
        correlation_id: str | None = None,
    ) -> IngestPDFResponse:
        data = json.loads(content.decode("utf-8"))
        spec = ProjectSpecDocument.model_validate(data)
        return await self.ingest_spec(
            spec, source_filename=filename, correlation_id=correlation_id
        )
