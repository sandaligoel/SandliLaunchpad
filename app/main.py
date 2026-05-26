"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app import __version__
from app.api.routes import architecture, health, ingest, interview, search
from app.core.config import get_settings
from app.core.exceptions import KnowledgeBaseError
from app.core.logging import configure_logging, get_logger
from app.search.index_manager import IndexManager

configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logger.info(
        "application_starting",
        env=settings.app_env,
        index=settings.azure_search_index_name,
    )
    if settings.azure_search_create_index_on_startup:
        try:
            IndexManager().ensure_index_exists()
        except Exception as e:
            logger.warning("index_init_deferred", error=str(e))
    yield
    logger.info("application_shutdown")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Agent Knowledge Retrieval System",
        description=(
            "Enterprise AI architecture memory platform. "
            "Ingest solution PDFs, extract structured knowledge, "
            "and enable semantic retrieval of agents, workflows, and architectures."
        ),
        version=__version__,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    prefix = settings.api_prefix
    app.include_router(health.router, prefix=prefix)
    app.include_router(ingest.router, prefix=prefix)
    app.include_router(search.router, prefix=prefix)
    app.include_router(interview.router, prefix=prefix)
    app.include_router(architecture.router, prefix=prefix)

    static_dir = Path(__file__).parent / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=static_dir), name="static")

        @app.get("/", include_in_schema=False)
        async def ui_home() -> FileResponse:
            return FileResponse(static_dir / "index.html")

    @app.exception_handler(KnowledgeBaseError)
    async def knowledge_base_error_handler(
        request: Request, exc: KnowledgeBaseError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={"error": exc.message, "details": exc.details},
        )

    return app


app = create_app()
