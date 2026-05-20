"""Agent Launchpad API — Phase 2 requirements interview."""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from api.routes import router
from config import configure_logging, get_settings

STATIC_DIR = Path(__file__).resolve().parent / "static"

settings = get_settings()
configure_logging(settings.log_level)

app = FastAPI(
    title="Affine Agent Launchpad",
    description="Phase 2 smart requirements interview",
    version="0.2.0",
)

_origins = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173",
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _origins if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/")
def root() -> RedirectResponse:
    """Browser entry point — serves the built-in interview UI."""
    return RedirectResponse(url="/ui/")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "phase": 2}


app.mount(
    "/ui",
    StaticFiles(directory=str(STATIC_DIR), html=True),
    name="launchpad-ui",
)
