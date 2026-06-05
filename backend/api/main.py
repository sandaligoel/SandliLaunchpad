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
    """Log storage connectivity; rebuild workflow index only when missing."""
    from api import builder_store

    try:
        storage = get_data_storage()
        index_raw = storage.read_json(builder_store.WORKFLOW_INDEX_KEY)
        if index_raw and index_raw.get("entries"):
            count = len(index_raw["entries"])
        else:
            count = builder_store.rebuild_workflow_index()
        st = get_storage_status()
        logger.info(
            "Launchpad storage=%s sessions=%s workflows=%s",
            st.get("backend", "unknown"),
            st.get("session_blob_count", "?"),
            count,
        )
    except Exception as exc:
        logger.warning("Startup storage check failed: %s", exc)


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
