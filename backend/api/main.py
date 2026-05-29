"""Agent Launchpad API — Phase 2 requirements interview."""

from __future__ import annotations

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from api.routes import router
from config import configure_logging, get_settings
from services.data_storage import get_data_storage, get_storage_status

STATIC_DIR = Path(__file__).resolve().parent / "static"

settings = get_settings()
configure_logging(settings.log_level)
get_data_storage()

app = FastAPI(
    title="Affine Agent Launchpad",
    description="Agent Launchpad — requirements interview and architecture planning",
    version="0.3.0",
)

_origins = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174",
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _origins if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.on_event("startup")
def _on_startup() -> None:
    """Ensure workflow index matches Azure Blob and log storage connectivity."""
    from api import builder_store

    try:
        count = builder_store.rebuild_workflow_index()
        st = get_storage_status()
        logger.info(
            "Launchpad storage=%s sessions=%s workflows=%s (index rebuilt)",
            st.get("backend", "unknown"),
            st.get("session_blob_count", "?"),
            st.get("workflow_blob_count", count),
        )
    except Exception as exc:
        logger.warning("Workflow index rebuild on startup failed: %s", exc)


@app.get("/")
def root() -> RedirectResponse:
    """Browser entry point — serves the built-in interview UI."""
    return RedirectResponse(url="/ui/")


@app.get("/health")
def health() -> dict:
    storage = get_storage_status()
    ok = storage.get("backend") == "local" or storage.get("reachable") is True
    return {
        "status": "ok" if ok else "degraded",
        "phase": 3,
        "features": ["interview", "architecture_plan"],
        "storage": storage,
    }


app.mount(
    "/ui",
    StaticFiles(directory=str(STATIC_DIR), html=True),
    name="launchpad-ui",
)

ARCHITECTURE_STATIC = STATIC_DIR / "architecture"
if ARCHITECTURE_STATIC.is_dir():
    app.mount(
        "/static/architecture",
        StaticFiles(directory=str(ARCHITECTURE_STATIC), html=True),
        name="architecture-flow",
    )
