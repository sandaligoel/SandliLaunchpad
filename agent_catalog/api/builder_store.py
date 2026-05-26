"""Workflow builder snapshots (canvas layout + plan) in shared data storage."""

from __future__ import annotations

import logging
from typing import Any, Optional

from services.data_storage import get_data_storage

logger = logging.getLogger(__name__)

WORKFLOW_INDEX_KEY = "workflows/_index.json"


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
    """Build workflow list from interview sessions when no index file exists yet."""
    from api import session_store

    entries: list[dict[str, Any]] = []
    for row in session_store.list_session_summaries(limit=30):
        sid = row["id"]
        ps = str(row.get("problem_statement") or "").strip()
        title = ps[:72] + ("…" if len(ps) > 72 else "") if ps else f"Launchpad {sid[:8]}"
        entries.append(
            {
                "sessionId": sid,
                "title": title,
                "savedAt": "",
                "stepCount": 0,
                "agentCount": 0,
                "hasPlan": bool(row.get("has_architecture_plan")),
            }
        )
    return entries


def list_workflow_index() -> list[dict[str, Any]]:
    raw = get_data_storage().read_json(WORKFLOW_INDEX_KEY)
    if raw:
        entries = raw.get("entries")
        if isinstance(entries, list) and entries:
            return entries
    blob_entries = _index_from_blob_workflows()
    if blob_entries:
        return blob_entries
    return _index_from_sessions()


def _index_from_blob_workflows() -> list[dict[str, Any]]:
    storage = get_data_storage()
    keys = sorted(storage.list_keys("workflows"), reverse=True)
    entries: list[dict[str, Any]] = []
    for key in keys:
        if key == "workflows/_index.json" or not key.endswith(".json"):
            continue
        session_id = key.split("/")[-1].replace(".json", "")
        doc = storage.read_json(f"workflows/{session_id}.json")
        if not doc:
            continue
        plan = doc.get("plan") or {}
        graph = plan.get("graph") or {}
        nodes = graph.get("nodes") or []
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
                "stepCount": len(nodes) if isinstance(nodes, list) else 0,
                "agentCount": len(plan.get("reuse_decisions") or nodes),
                "hasPlan": bool(nodes),
            }
        )
    return entries


def _upsert_index_entry(session_id: str, document: dict[str, Any]) -> None:
    plan = document.get("plan") or {}
    graph = plan.get("graph") or {}
    nodes = graph.get("nodes") or []
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
    entries = [e for e in list_workflow_index() if e.get("sessionId") != session_id]
    entries.insert(0, entry)
    get_data_storage().write_json(WORKFLOW_INDEX_KEY, {"entries": entries})


def _remove_index_entry(session_id: str) -> None:
    entries = [
        e for e in list_workflow_index() if e.get("sessionId") != session_id
    ]
    get_data_storage().write_json(WORKFLOW_INDEX_KEY, {"entries": entries})
