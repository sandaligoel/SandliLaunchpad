"""Interview session store — memory cache with JSON persistence (local or Azure Blob)."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from threading import Lock
from typing import Dict, Optional

from schemas.architecture_spec import InterviewSession
from services.data_storage import blob_storage_configured, get_data_storage

logger = logging.getLogger(__name__)

_lock = Lock()
_sessions: Dict[str, InterviewSession] = {}

SESSIONS_DIR = Path(__file__).resolve().parent.parent / "data" / "sessions"
SESSION_STORAGE_KEY = "sessions/{session_id}.json"


def _session_storage_key(session_id: str) -> str:
    safe = session_id.replace("/", "_").replace("..", "_")
    return SESSION_STORAGE_KEY.format(session_id=safe)


def _legacy_session_path(session_id: str) -> Path:
    safe = session_id.replace("/", "_").replace("..", "_")
    return SESSIONS_DIR / f"{safe}.json"


def _persist(session: InterviewSession) -> None:
    payload = json.loads(session.model_dump_json())
    try:
        get_data_storage().write_json(_session_storage_key(session.id), payload)
    except Exception as exc:
        logger.warning("Could not persist session %s to storage: %s", session.id, exc)

    if not blob_storage_configured():
        try:
            SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
            _legacy_session_path(session.id).write_text(
                session.model_dump_json(indent=2),
                encoding="utf-8",
            )
        except OSError as exc:
            logger.warning("Could not persist session %s to disk: %s", session.id, exc)


def _load_from_storage(session_id: str) -> Optional[InterviewSession]:
    raw = get_data_storage().read_json(_session_storage_key(session_id))
    if raw:
        try:
            return InterviewSession.model_validate(raw)
        except Exception as exc:
            logger.warning(
                "Could not parse session %s from storage: %s", session_id, exc
            )

    path = _legacy_session_path(session_id)
    if path.is_file():
        try:
            legacy = json.loads(path.read_text(encoding="utf-8"))
            session = InterviewSession.model_validate(legacy)
            _persist(session)
            return session
        except Exception as exc:
            logger.warning(
                "Could not load legacy session %s from disk: %s", session_id, exc
            )
    return None


def save(session: InterviewSession) -> None:
    with _lock:
        _sessions[session.id] = session
    _persist(session)
    try:
        from services.builder_sync import sync_workflow_from_session

        sync_workflow_from_session(session)
    except Exception as exc:
        logger.warning(
            "Builder workflow sync after session save failed for %s: %s",
            session.id,
            exc,
        )


def get(session_id: str) -> Optional[InterviewSession]:
    with _lock:
        cached = _sessions.get(session_id)
    if cached is not None:
        return cached

    loaded = _load_from_storage(session_id)
    if loaded is not None:
        with _lock:
            _sessions[session_id] = loaded
        return loaded
    return None


def _session_rank(raw: dict) -> tuple:
    """Newest / most complete sessions first."""
    spec = raw.get("spec") or {}
    status = str(spec.get("status") or "")
    status_rank = {"ready": 3, "sufficient": 2}.get(status, 1)
    return (
        status_rank,
        len(raw.get("messages") or []),
        1 if raw.get("architecture_plan") else 0,
    )


def list_session_summaries(*, limit: int = 50) -> list[dict]:
    """List saved interviews from Azure Blob (or local mirror), newest first."""
    storage = get_data_storage()
    keys = storage.list_keys_by_mtime("sessions", newest_first=True)
    rows: list[tuple[tuple, dict]] = []
    for key in keys:
        if not key.startswith("sessions/") or not key.endswith(".json"):
            continue
        session_id = key.split("/")[-1].replace(".json", "")
        raw = storage.read_json(_session_storage_key(session_id))
        if not raw:
            continue
        spec = raw.get("spec") or {}
        problem = str(spec.get("problem_statement") or "").strip()
        summary = {
            "id": raw.get("id") or session_id,
            "status": spec.get("status"),
            "problem_statement": problem,
            "message_count": len(raw.get("messages") or []),
            "has_architecture_plan": bool(raw.get("architecture_plan")),
        }
        rows.append((_session_rank(raw), summary))

    rows.sort(key=lambda item: item[0], reverse=True)
    return [summary for _, summary in rows[:limit]]


def delete(session_id: str) -> bool:
    from api import builder_store

    with _lock:
        removed = _sessions.pop(session_id, None) is not None
    removed = get_data_storage().delete(_session_storage_key(session_id)) or removed
    path = _legacy_session_path(session_id)
    if path.is_file():
        try:
            path.unlink()
            removed = True
        except OSError as exc:
            logger.warning("Could not delete session file %s: %s", session_id, exc)
    builder_store.delete_workflow(session_id)
    return removed
