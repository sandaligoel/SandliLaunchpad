"""End-to-end PDF ingestion orchestration."""

from __future__ import annotations

import uuid

import structlog

from backend.app.chunkers.semantic_chunker import SemanticChunker
from backend.app.core.config import get_settings
from backend.app.core.logging import get_logger
from backend.app.extractors.llm_extractor import LLMExtractor
from backend.app.parsers.pdf_parser import PDFParser
from backend.app.parsers.solution_document_parser import SolutionDocumentParser
from backend.app.schemas.api import IngestCatalogResponse, IngestPDFResponse
from backend.app.schemas.extraction import SourceDocument
from backend.app.services.catalog_ingestion import CatalogIngestionService
from backend.app.services.indexing import IndexingService
from backend.app.utils.ids import generate_document_id, generate_project_id

logger = get_logger(__name__)


class IngestionService:
    """Orchestrates PDF → parse → chunk → extract → embed → index."""

    def __init__(self) -> None:
        self.parser = PDFParser()
        self.chunker = SemanticChunker()
        self.extractor = LLMExtractor()
        self.indexing = IndexingService()

    async def ingest_pdf(
        self,
        file_bytes: bytes,
        filename: str,
        correlation_id: str | None = None,
    ) -> IngestPDFResponse | IngestCatalogResponse:
        cid = correlation_id or str(uuid.uuid4())
        structlog.contextvars.bind_contextvars(correlation_id=cid)

        parsed = await self.parser.parse(file_bytes, filename)
        settings = get_settings()
        if settings.solution_catalog_auto_detect and SolutionDocumentParser.is_solution_catalog(
            parsed.full_text, filename
        ):
            logger.info("routing_to_catalog_ingestion", filename=filename)
            catalog_service = CatalogIngestionService()
            return await catalog_service.ingest_catalog_pdf(
                file_bytes, filename, correlation_id=cid
            )

        return await self._ingest_standard_pdf(
            file_bytes, filename, correlation_id=cid, parsed=parsed
        )

    async def _ingest_standard_pdf(
        self,
        file_bytes: bytes,
        filename: str,
        correlation_id: str | None = None,
        parsed=None,
    ) -> IngestPDFResponse:
        cid = correlation_id or str(uuid.uuid4())
        structlog.contextvars.bind_contextvars(correlation_id=cid)
        warnings: list[str] = []

        logger.info("ingestion_started", filename=filename, correlation_id=cid)

        if parsed is None:
            parsed = await self.parser.parse(file_bytes, filename)
        document_id = generate_document_id(filename, parsed.content_hash)
        project_id = generate_project_id(filename, parsed.content_hash)

        chunks = self.chunker.chunk_document(parsed, document_id)
        if not chunks:
            warnings.append("No semantic chunks produced; extraction may be sparse")

        partials = await self.extractor.extract_chunks(chunks)
        low_conf = [p for p in partials if p.confidence_score < 0.3]
        if low_conf:
            warnings.append(
                f"{len(low_conf)} chunks had low extraction confidence (<0.3)"
            )

        project = await self.extractor.merge_extractions(
            partials, project_id, filename
        )
        if not project.project_name:
            project.project_name = filename.rsplit(".", 1)[0]

        project.source_document = SourceDocument(
            filename=filename,
            page_count=parsed.page_count,
            content_hash=parsed.content_hash,
        )

        indexed_count, breakdown = await self.indexing.build_and_index(
            project, chunks, filename
        )

        logger.info(
            "ingestion_completed",
            project_id=project_id,
            entities_indexed=indexed_count,
            breakdown=breakdown,
        )

        return IngestPDFResponse(
            success=True,
            project_id=project_id,
            project_name=project.project_name,
            filename=filename,
            pages_processed=parsed.page_count,
            chunks_created=len(chunks),
            entities_indexed=indexed_count,
            entity_breakdown=breakdown,
            project_knowledge=project,
            correlation_id=cid,
            warnings=warnings,
        )
