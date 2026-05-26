"""Interview session and architecture plan persistence (memory + disk)."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from threading import Lock

from app.schemas.architecture_graph import ArchitecturePlanResponse
from app.schemas.architecture_spec import ArchitectureSpec

_DATA_ROOT = Path(__file__).resolve().parents[2] / "data" / "sessions"
_store: dict[str, ArchitectureSpec] = {}
_plan_cache: dict[str, ArchitecturePlanResponse] = {}
_lock = Lock()


def _session_path(session_id: str) -> Path:
    return _DATA_ROOT / f"{session_id}.json"


def _plan_path(session_id: str) -> Path:
    return _DATA_ROOT / f"{session_id}_plan.json"


def _ensure_dir() -> None:
    _DATA_ROOT.mkdir(parents=True, exist_ok=True)


def _write_session(spec: ArchitectureSpec) -> None:
    _ensure_dir()
    _session_path(spec.session_id).write_text(
        spec.model_dump_json(indent=2),
        encoding="utf-8",
    )


def _load_session_from_disk(session_id: str) -> ArchitectureSpec | None:
    path = _session_path(session_id)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return ArchitectureSpec.model_validate(data)
    except (json.JSONDecodeError, ValueError):
        return None


def create_session(spec: ArchitectureSpec) -> str:
    sid = spec.session_id or str(uuid.uuid4())
    spec.session_id = sid
    with _lock:
        _store[sid] = spec
        _write_session(spec)
    return sid


def get_session(session_id: str) -> ArchitectureSpec | None:
    with _lock:
        if session_id in _store:
            return _store[session_id]
        spec = _load_session_from_disk(session_id)
        if spec:
            _store[session_id] = spec
        return spec


def update_session(spec: ArchitectureSpec) -> None:
    with _lock:
        _store[spec.session_id] = spec
        _write_session(spec)


def save_plan(plan: ArchitecturePlanResponse) -> None:
    if not plan.session_id:
        return
    _ensure_dir()
    _plan_path(plan.session_id).write_text(
        plan.model_dump_json(indent=2),
        encoding="utf-8",
    )
    with _lock:
        _plan_cache[plan.session_id] = plan


def get_plan(session_id: str) -> ArchitecturePlanResponse | None:
    with _lock:
        if session_id in _plan_cache:
            return _plan_cache[session_id]
    path = _plan_path(session_id)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        plan = ArchitecturePlanResponse.model_validate(data)
        _plan_cache[session_id] = plan
        return plan
    except (json.JSONDecodeError, ValueError):
        return None


def list_sessions() -> list[str]:
    _ensure_dir()
    ids: set[str] = set(_store.keys())
    for path in _DATA_ROOT.glob("*.json"):
        name = path.stem
        if name.endswith("_plan"):
            continue
        ids.add(name)
    return sorted(ids)
