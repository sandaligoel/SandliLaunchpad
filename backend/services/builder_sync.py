"""Sync interview sessions to persisted builder workflow snapshots."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from schemas.architecture_plan import ArchitecturePlan, ReuseDecision
from schemas.architecture_spec import GraphDraft, InterviewSession
from services.graph_sanitizer import sanitize_graph

logger = logging.getLogger(__name__)


def _title_from_session(session: InterviewSession) -> str:
    ps = (session.spec.problem_statement or "").strip()
    if ps:
        return ps[:72] + ("…" if len(ps) > 72 else "")
    return f"Launchpad workflow {session.id[:8]}"


def _plan_from_graph_draft(session: InterviewSession, graph: GraphDraft) -> dict[str, Any]:
    decisions = [
        ReuseDecision(
            node_id=n.id,
            node_label=n.label,
            decision="reuse" if n.agent_id else "build",
            agent_id=n.agent_id,
            rationale="From interview graph draft.",
        ).model_dump(mode="json")
        for n in graph.nodes
    ]
    return ArchitecturePlan(
        graph=graph,
        reuse_decisions=decisions,
        catalog_matches=[],
        summary_markdown=(session.spec.architecture_blueprint or "")[:4000],
        open_questions=[],
    ).model_dump(mode="json")


def _empty_plan() -> dict[str, Any]:
    return ArchitecturePlan(
        graph=GraphDraft(),
        reuse_decisions=[],
        catalog_matches=[],
        summary_markdown="",
        open_questions=[],
    ).model_dump(mode="json")


def workflow_document_from_session(
    session: InterviewSession,
    *,
    existing: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """
    Build a builder workflow JSON document for blob storage.

    Preserves canvas nodePositions from an existing saved workflow when present.
    """
    existing = existing or {}
    node_positions = existing.get("nodePositions")
    if not isinstance(node_positions, dict):
        node_positions = {}

    selected = existing.get("selectedNodeId")

    if session.architecture_plan is not None:
        graph = sanitize_graph(session.architecture_plan.graph)
        plan_dump = session.architecture_plan.model_copy(
            update={"graph": graph}
        ).model_dump(mode="json")
    elif session.spec.graph_draft and session.spec.graph_draft.nodes:
        graph = sanitize_graph(session.spec.graph_draft)
        plan_dump = _plan_from_graph_draft(session, graph)
    else:
        plan_dump = _empty_plan()

    return {
        "sessionId": session.id,
        "plan": plan_dump,
        "nodePositions": node_positions,
        "selectedNodeId": selected,
        "title": existing.get("title") or _title_from_session(session),
        "problemStatement": session.spec.problem_statement or "",
        "savedAt": datetime.now(timezone.utc).isoformat(),
    }


def sync_workflow_from_session(session: InterviewSession) -> None:
    """Write workflows/{session_id}.json and update the workflow index."""
    from api import builder_store

    try:
        existing = builder_store.load_workflow(session.id)
        doc = workflow_document_from_session(session, existing=existing)
        builder_store.save_workflow(session.id, doc)
        logger.debug("Synced builder workflow for session %s", session.id)
    except Exception as exc:
        logger.warning(
            "Could not sync builder workflow for session %s: %s",
            session.id,
            exc,
        )
