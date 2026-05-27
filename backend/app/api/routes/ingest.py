"""PDF ingestion API routes."""

import uuid

import structlog
from fastapi import APIRouter, File, UploadFile

from typing import Union

from backend.app.api.dependencies import (
    get_catalog_ingestion_service,
    get_ingestion_service,
    get_spec_ingestion_service,
)
from backend.app.core.exceptions import KnowledgeBaseError
from backend.app.core.logging import get_logger
from backend.app.schemas.api import IngestCatalogResponse, IngestPDFResponse
from backend.app.schemas.spec_import import ProjectSpecDocument

logger = get_logger(__name__)
router = APIRouter(prefix="/ingest", tags=["Ingestion"])

MAX_PDF_SIZE_MB = 100


@router.post("/pdf", response_model=Union[IngestPDFResponse, IngestCatalogResponse])
async def ingest_pdf(
    file: UploadFile = File(..., description="Enterprise AI solution PDF"),
) -> Union[IngestPDFResponse, IngestCatalogResponse]:
    """
    Ingest a PDF. Auto-detects solution catalog PDFs (e.g. solution_agents.pdf)
    and indexes all solutions; otherwise runs standard LLM extraction pipeline.
    """
    correlation_id = str(uuid.uuid4())
    structlog.contextvars.bind_contextvars(correlation_id=correlation_id)

    if not file.filename or not file.filename.lower().endswith(".pdf"):
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    content = await file.read()
    size_mb = len(content) / (1024 * 1024)
    if size_mb > MAX_PDF_SIZE_MB:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=413,
            detail=f"PDF exceeds maximum size of {MAX_PDF_SIZE_MB}MB",
        )

    logger.info("pdf_upload_received", filename=file.filename, size_mb=round(size_mb, 2))

    try:
        service = get_ingestion_service()
        return await service.ingest_pdf(
            file_bytes=content,
            filename=file.filename,
            correlation_id=correlation_id,
        )
    except KnowledgeBaseError as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=422, detail=e.message) from e
    except Exception as e:
        logger.exception("ingestion_failed", error=str(e))
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail="Ingestion pipeline failed") from e


@router.post("/spec", response_model=IngestPDFResponse)
async def ingest_spec(
    file: UploadFile | None = File(None, description="Project spec JSON file"),
) -> IngestPDFResponse:
    """
    Ingest a structured project spec JSON (project + agents).
    If no file is uploaded, indexes the bundled data/specs/spec.json.
    """
    correlation_id = str(uuid.uuid4())
    structlog.contextvars.bind_contextvars(correlation_id=correlation_id)

    try:
        service = get_spec_ingestion_service()
        if file and file.filename:
            content = await file.read()
            if not file.filename.lower().endswith(".json"):
                from fastapi import HTTPException
                raise HTTPException(status_code=400, detail="Only JSON spec files are supported")
            return await service.ingest_spec_bytes(
                content, filename=file.filename, correlation_id=correlation_id
            )
        return await service.ingest_spec_file(correlation_id=correlation_id)
    except KnowledgeBaseError as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=422, detail=e.message) from e
    except Exception as e:
        logger.exception("spec_ingestion_failed", error=str(e))
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail="Spec ingestion failed") from e


@router.post("/catalog", response_model=IngestCatalogResponse)
async def ingest_solution_catalog(
    file: UploadFile | None = File(
        None,
        description="Solution catalog PDF (defaults to data/documents/solution_agents.pdf)",
    ),
) -> IngestCatalogResponse:
    """
    Ingest Affine solution catalog PDF — parses all projects and agents,
    skips LLM extraction (rule-based), indexes each project separately.
    """
    correlation_id = str(uuid.uuid4())
    structlog.contextvars.bind_contextvars(correlation_id=correlation_id)

    try:
        service = get_catalog_ingestion_service()
        if file and file.filename:
            content = await file.read()
            if not file.filename.lower().endswith(".pdf"):
                from fastapi import HTTPException
                raise HTTPException(status_code=400, detail="Only PDF files are supported")
            return await service.ingest_catalog_pdf(
                content, file.filename, correlation_id=correlation_id
            )
        return await service.ingest_default_catalog(correlation_id=correlation_id)
    except KnowledgeBaseError as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=422, detail=e.message) from e
    except Exception as e:
        logger.exception("catalog_ingestion_failed", error=str(e))
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail="Catalog ingestion failed") from e


@router.post("/spec/body", response_model=IngestPDFResponse)
async def ingest_spec_body(spec: ProjectSpecDocument) -> IngestPDFResponse:
    """Ingest a project spec from a JSON request body."""
    correlation_id = str(uuid.uuid4())
    try:
        service = get_spec_ingestion_service()
        return await service.ingest_spec(spec, correlation_id=correlation_id)
    except KnowledgeBaseError as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=422, detail=e.message) from e
