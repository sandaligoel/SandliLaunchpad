"""Ingest multi-project solution catalog PDFs (solution_agents.pdf)."""

from __future__ import annotations

import uuid
from pathlib import Path

import structlog

from backend.app.chunkers.solution_chunker import SolutionCatalogChunker
from backend.app.core.config import get_settings
from backend.app.core.logging import get_logger
from backend.app.parsers.pdf_parser import PDFParser
from backend.app.parsers.solution_document_parser import SolutionDocumentParser
from backend.app.schemas.api import IngestCatalogResponse, IngestPDFResponse
from backend.app.schemas.extraction import SourceDocument
from backend.app.services.indexing import IndexingService
from backend.app.services.solution_mapper import solution_to_project_knowledge
from backend.app.utils.ids import content_hash, generate_document_id, generate_project_id

logger = get_logger(__name__)


class CatalogIngestionService:
    """Parses solution_agents.pdf-style catalogs and indexes each project."""

    def __init__(self) -> None:
        self.pdf_parser = PDFParser()
        self.solution_parser = SolutionDocumentParser()
        self.chunker = SolutionCatalogChunker()
        self.indexing = IndexingService()

    async def ingest_catalog_pdf(
        self,
        file_bytes: bytes,
        filename: str,
        correlation_id: str | None = None,
    ) -> IngestCatalogResponse:
        cid = correlation_id or str(uuid.uuid4())
        structlog.contextvars.bind_contextvars(correlation_id=cid)

        parsed_pdf = await self.pdf_parser.parse(file_bytes, filename)
        document_id = generate_document_id(filename, parsed_pdf.content_hash)

        catalog = self.solution_parser.parse_full_text(
            parsed_pdf.full_text,
            filename,
            parsed_pdf.page_count,
            parsed_pdf.content_hash,
        )

        logger.info(
            "catalog_parsed",
            filename=filename,
            solutions=len(catalog.solutions),
            pages=parsed_pdf.page_count,
        )

        project_results: list[IngestPDFResponse] = []
        total_indexed = 0
        combined_breakdown: dict[str, int] = {}

        chunks_by_project = self.chunker.chunk_catalog(catalog, document_id)

        for solution in catalog.solutions:
            project_id = generate_project_id(
                filename, parsed_pdf.content_hash, solution.project_name
            )
            project = solution_to_project_knowledge(
                solution,
                project_id,
                filename,
                parsed_pdf.content_hash,
            )
            project.source_document = SourceDocument(
                filename=filename,
                page_count=parsed_pdf.page_count,
                content_hash=parsed_pdf.content_hash,
            )

            chunks = chunks_by_project.get(solution.project_name, [])
            count, breakdown = await self.indexing.build_and_index(
                project, chunks, filename
            )
            total_indexed += count
            for k, v in breakdown.items():
                combined_breakdown[k] = combined_breakdown.get(k, 0) + v

            project_results.append(
                IngestPDFResponse(
                    success=True,
                    project_id=project_id,
                    project_name=project.project_name,
                    filename=filename,
                    pages_processed=parsed_pdf.page_count,
                    chunks_created=len(chunks),
                    entities_indexed=count,
                    entity_breakdown=breakdown,
                    project_knowledge=project,
                    correlation_id=cid,
                    warnings=[],
                )
            )

        return IngestCatalogResponse(
            success=True,
            filename=filename,
            pages_processed=parsed_pdf.page_count,
            solutions_found=len(catalog.solutions),
            solutions_indexed=len(project_results),
            total_entities_indexed=total_indexed,
            entity_breakdown=combined_breakdown,
            projects=project_results,
            correlation_id=cid,
        )

    async def ingest_default_catalog(
        self, correlation_id: str | None = None
    ) -> IngestCatalogResponse:
        settings = get_settings()
        path = Path(settings.default_solution_agents_pdf)
        if not path.exists():
            from backend.app.core.exceptions import KnowledgeBaseError

            raise KnowledgeBaseError(
                f"Default catalog PDF not found: {path}",
                {"path": str(path)},
            )
        return await self.ingest_catalog_pdf(
            path.read_bytes(),
            path.name,
            correlation_id=correlation_id,
        )
