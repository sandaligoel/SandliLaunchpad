"""In-memory interview session store (Phase 2; replace with Redis/DB for production)."""

from __future__ import annotations

from threading import Lock
from typing import Dict, Optional

from schemas.architecture_spec import InterviewSession

_lock = Lock()
_sessions: Dict[str, InterviewSession] = {}


def save(session: InterviewSession) -> None:
    with _lock:
        _sessions[session.id] = session


def get(session_id: str) -> Optional[InterviewSession]:
    with _lock:
        return _sessions.get(session_id)


def delete(session_id: str) -> bool:
    with _lock:
        return _sessions.pop(session_id, None) is not None
