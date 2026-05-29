"""Workflow builder snapshots (canvas layout + plan) in shared data storage."""

from __future__ import annotations

import logging
from typing import Any, Optional

from services.data_storage import get_data_storage

logger = logging.getLogger(__name__)

WORKFLOW_INDEX_KEY = "workflows/_index.json"


def _entry_has_plan(entry: dict[str, Any]) -> bool:
    """Workflows list only includes sessions with a non-empty architecture graph."""
    if not entry.get("hasPlan"):
        return False
    try:
        return int(entry.get("stepCount") or 0) > 0
    except (TypeError, ValueError):
        return False


def _filter_planned(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [e for e in entries if _entry_has_plan(e)]


def _workflow_key(session_id: str) -> str:
    safe = session_id.replace("/", "_").replace("..", "_")
    return f"workflows/{safe}.json"


def load_workflow(session_id: str) -> Optional[dict[str, Any]]:
    return get_data_storage().read_json(_workflow_key(session_id))


def save_workflow(session_id: str, document: dict[str, Any]) -> None:
    doc = dict(document)
    doc["sessionId"] = session_id
    get_data_storage().write_json(_workflow_key(session_id), doc)
    _upsert_index_entry(session_id, doc)


def delete_workflow(session_id: str) -> bool:
    removed = get_data_storage().delete(_workflow_key(session_id))
    _remove_index_entry(session_id)
    return removed


def _index_from_sessions() -> list[dict[str, Any]]:
    """Sessions with a non-empty architecture graph (when no workflow blobs exist)."""
    from api import session_store

    entries: list[dict[str, Any]] = []
    for row in session_store.list_session_summaries(limit=50):
        if not row.get("has_architecture_plan"):
            continue
        sid = row["id"]
        session = session_store.get(sid)
        if session is None or session.architecture_plan is None:
            continue
        nodes = session.architecture_plan.graph.nodes or []
        if not nodes:
            continue
        ps = str(row.get("problem_statement") or "").strip()
        title = ps[:72] + ("…" if len(ps) > 72 else "") if ps else f"Launchpad {sid[:8]}"
        plan = session.architecture_plan
        entries.append(
            {
                "sessionId": sid,
                "title": title,
                "savedAt": "",
                "stepCount": len(nodes),
                "agentCount": len(plan.reuse_decisions) or len(nodes),
                "hasPlan": True,
            }
        )
    return entries


def _sort_workflow_entries(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        entries,
        key=lambda e: e.get("savedAt") or "",
        reverse=True,
    )


def rebuild_workflow_index() -> int:
    """Rebuild workflows/_index.json from workflow blobs that have a plan (newest first)."""
    entries = _sort_workflow_entries(_filter_planned(_index_from_blob_workflows()))
    if not entries:
        entries = _sort_workflow_entries(_index_from_sessions())
    get_data_storage().write_json(
        WORKFLOW_INDEX_KEY,
        {"entries": entries},
    )
    return len(entries)


def list_workflow_index() -> list[dict[str, Any]]:
    raw = get_data_storage().read_json(WORKFLOW_INDEX_KEY)
    if raw:
        entries = raw.get("entries")
        if isinstance(entries, list) and entries:
            return _sort_workflow_entries(_filter_planned(entries))
    blob_entries = _filter_planned(_index_from_blob_workflows())
    if blob_entries:
        return _sort_workflow_entries(blob_entries)
    return _sort_workflow_entries(_index_from_sessions())


def _index_from_blob_workflows(*, max_items: int = 60) -> list[dict[str, Any]]:
    storage = get_data_storage()
    keys = storage.list_keys_by_mtime("workflows", newest_first=True)
    entries: list[dict[str, Any]] = []
    for key in keys:
        if len(entries) >= max_items:
            break
        if key == "workflows/_index.json" or not key.endswith(".json"):
            continue
        session_id = key.split("/")[-1].replace(".json", "")
        doc = storage.read_json(f"workflows/{session_id}.json")
        if not doc:
            continue
        plan = doc.get("plan") or {}
        graph = plan.get("graph") or {}
        nodes = graph.get("nodes") or []
        if not isinstance(nodes, list) or len(nodes) == 0:
            continue
        title = (
            (doc.get("title") or "").strip()
            or (doc.get("problemStatement") or "").strip()[:72]
            or f"Launchpad workflow {session_id[:8]}"
        )
        entries.append(
            {
                "sessionId": session_id,
                "title": title[:72] + ("…" if len(title) > 72 else ""),
                "savedAt": doc.get("savedAt") or "",
                "stepCount": len(nodes),
                "agentCount": len(plan.get("reuse_decisions") or nodes),
                "hasPlan": True,
            }
        )
    return entries


def _upsert_index_entry(session_id: str, document: dict[str, Any]) -> None:
    plan = document.get("plan") or {}
    graph = plan.get("graph") or {}
    nodes = graph.get("nodes") or []
    if not isinstance(nodes, list) or len(nodes) == 0:
        _remove_index_entry(session_id)
        return
    title = (
        (document.get("title") or "").strip()
        or (document.get("problemStatement") or "").strip()[:72]
        or f"Launchpad workflow {session_id[:8]}"
    )
    entry = {
        "sessionId": session_id,
        "title": title[:72] + ("…" if len(title) > 72 else ""),
        "savedAt": document.get("savedAt") or "",
        "stepCount": len(nodes) if isinstance(nodes, list) else 0,
        "agentCount": len(plan.get("reuse_decisions") or nodes),
        "hasPlan": bool(nodes),
    }
    entries = [
        e
        for e in list_workflow_index()
        if e.get("sessionId") != session_id
    ]
    entries.insert(0, entry)
    get_data_storage().write_json(
        WORKFLOW_INDEX_KEY,
        {"entries": _filter_planned(entries)},
    )


def _remove_index_entry(session_id: str) -> None:
    entries = [
        e for e in list_workflow_index() if e.get("sessionId") != session_id
    ]
    get_data_storage().write_json(WORKFLOW_INDEX_KEY, {"entries": entries})
