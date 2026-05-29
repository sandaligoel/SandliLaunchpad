"""FastAPI routes for the Phase 2 requirements interview."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from api import builder_store, session_store
from config import get_settings
from schemas.architecture_plan import ArchitecturePlan
from schemas.architecture_spec import InterviewSession
from services.architecture_planner import plan_architecture
from services.architecture_remediation import apply_remediation, revalidate_plan
from schemas.agent_record import AgentRecord
from services.catalog_interview_context import load_all_catalog_agents
from services.data_storage import storage_backend_name
from services.interview import run_interview_turn, start_session

router = APIRouter(prefix="/api")


class CatalogAgentsResponse(BaseModel):
    agents: list[AgentRecord]
    count: int


class StartSessionRequest(BaseModel):
    problem_statement: str = Field(..., min_length=10, max_length=8000)


class TurnRequest(BaseModel):
    answer: str = Field(..., min_length=1, max_length=2000)


class SessionResponse(BaseModel):
    session: InterviewSession


class SessionSummary(BaseModel):
    id: str
    status: Optional[str] = None
    problem_statement: str = ""
    message_count: int = 0
    has_architecture_plan: bool = False


class SessionListResponse(BaseModel):
    sessions: list[SessionSummary]
    storage_backend: str


class ArchitectureResponse(BaseModel):
    """Phase 3 planned architecture for a session."""

    session_id: str
    plan: ArchitecturePlan


class ApplyRemediationRequest(BaseModel):
    """Apply a user-selected fix by finding + option id (server resolves full action)."""

    finding_id: str = Field(..., min_length=3, max_length=128)
    option_id: str = Field(..., min_length=1, max_length=128)


class WorkflowsIndexResponse(BaseModel):
    workflows: list[dict]


class BuilderWorkflowResponse(BaseModel):
    workflow: dict


@router.get("/catalog/agents", response_model=CatalogAgentsResponse)
def list_catalog_agents() -> CatalogAgentsResponse:
    """All Affine built agents from data/spec.json (Agent Library)."""
    settings = get_settings()
    agents = load_all_catalog_agents(settings)
    return CatalogAgentsResponse(agents=agents, count=len(agents))


@router.post("/sessions", response_model=SessionResponse)
def create_session(body: StartSessionRequest) -> SessionResponse:
    """Start a smart interview from the user's problem statement."""
    settings = get_settings()
    try:
        session = start_session(body.problem_statement, settings)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Interview start failed: {exc}") from exc

    session_store.save(session)
    return SessionResponse(session=session)


@router.get("/sessions", response_model=SessionListResponse)
def list_sessions() -> SessionListResponse:
    """Recent interviews from Azure Blob (or local mirror)."""
    rows = session_store.list_session_summaries()
    return SessionListResponse(
        sessions=[SessionSummary(**row) for row in rows],
        storage_backend=storage_backend_name(),
    )


@router.get("/sessions/{session_id}", response_model=SessionResponse)
def get_session(session_id: str) -> SessionResponse:
    """Return full session state (spec + messages + pending question)."""
    session = session_store.get(session_id)
    if session is None:
        raise HTTPException(
            status_code=404,
            detail=(
                "Session not found. Start a new interview or use a session id "
                "saved in Azure Blob (launchpad/sessions/) or data/sessions/."
            ),
        )
    return SessionResponse(session=session)


@router.post("/sessions/{session_id}/turn", response_model=SessionResponse)
def submit_turn(session_id: str, body: TurnRequest) -> SessionResponse:
    """Submit an answer to the current question and advance the interview."""
    session = session_store.get(session_id)
    if session is None:
        raise HTTPException(
            status_code=404,
            detail=(
                "Session not found. Start a new interview or use a session id "
                "saved in Azure Blob (launchpad/sessions/) or data/sessions/."
            ),
        )
    if session.spec.status == "ready":
        raise HTTPException(status_code=409, detail="Specification is already complete")
    if session.pending_question is None:
        raise HTTPException(status_code=409, detail="No question is pending for this session")

    settings = get_settings()
    try:
        session = run_interview_turn(session, settings, user_answer=body.answer)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Interview turn failed: {exc}") from exc

    # Fast response path: keep turn-to-turn updates in memory, persist fully
    # only when interview reaches sufficient/ready milestones.
    is_milestone = session.spec.status == "ready"
    session_store.save(session, lightweight=not is_milestone)
    return SessionResponse(session=session)


@router.post(
    "/sessions/{session_id}/architecture",
    response_model=ArchitectureResponse,
)
def generate_architecture(
    session_id: str,
    force: bool = False,
) -> ArchitectureResponse:
    """
    Generate Phase 3 architecture graph with catalog reuse decisions.

    Requires spec status ``sufficient`` or ``ready``. Caches plan on the session
    unless ``force=true``.
    """
    session = session_store.get(session_id)
    if session is None:
        raise HTTPException(
            status_code=404,
            detail=(
                "Session not found. Start a new interview or use a session id "
                "saved in Azure Blob (launchpad/sessions/) or data/sessions/."
            ),
        )

    if session.spec.status not in ("sufficient", "ready"):
        raise HTTPException(
            status_code=409,
            detail=(
                f"Specification must be sufficient or ready before planning "
                f"(current: {session.spec.status})."
            ),
        )

    if session.architecture_plan is not None and not force:
        return ArchitectureResponse(session_id=session_id, plan=session.architecture_plan)

    settings = get_settings()
    try:
        plan = plan_architecture(session, settings)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Architecture planning failed: {exc}",
        ) from exc

    session.architecture_plan = plan
    session_store.save(session)
    return ArchitectureResponse(session_id=session_id, plan=plan)


@router.get(
    "/sessions/{session_id}/architecture",
    response_model=ArchitectureResponse,
)
def get_architecture(session_id: str) -> ArchitectureResponse:
    """Return cached architecture plan if one was generated."""
    session = session_store.get(session_id)
    if session is None:
        raise HTTPException(
            status_code=404,
            detail=(
                "Session not found. Start a new interview or use a session id "
                "saved in Azure Blob (launchpad/sessions/) or data/sessions/."
            ),
        )
    if session.architecture_plan is None:
        raise HTTPException(
            status_code=404,
            detail="No architecture plan yet. POST /architecture to generate.",
        )
    return ArchitectureResponse(session_id=session_id, plan=session.architecture_plan)


@router.post(
    "/sessions/{session_id}/architecture/remediate",
    response_model=ArchitectureResponse,
)
def remediate_architecture(
    session_id: str,
    body: ApplyRemediationRequest,
) -> ArchitectureResponse:
    """
    Apply a validation remediation choice, update the plan, and re-validate.
    """
    session = session_store.get(session_id)
    if session is None:
        raise HTTPException(
            status_code=404,
            detail=(
                "Session not found. Start a new interview or use a session id "
                "saved in Azure Blob (launchpad/sessions/) or data/sessions/."
            ),
        )
    if session.architecture_plan is None:
        raise HTTPException(
            status_code=404,
            detail="Generate architecture first (POST /architecture).",
        )

    settings = get_settings()
    try:
        plan = apply_remediation(
            session.spec,
            session.architecture_plan.model_copy(deep=True),
            body.finding_id,
            body.option_id,
            settings,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Remediation failed: {exc}",
        ) from exc

    session.architecture_plan = plan
    session_store.save(session)
    return ArchitectureResponse(session_id=session_id, plan=plan)


@router.post(
    "/sessions/{session_id}/architecture/approve",
    response_model=ArchitectureResponse,
)
def approve_architecture(session_id: str) -> ArchitectureResponse:
    """Mark architecture approved when validation allows it."""
    session = session_store.get(session_id)
    if session is None:
        raise HTTPException(
            status_code=404,
            detail=(
                "Session not found. Start a new interview or use a session id "
                "saved in Azure Blob (launchpad/sessions/) or data/sessions/."
            ),
        )
    if session.architecture_plan is None:
        raise HTTPException(status_code=404, detail="No architecture plan yet.")

    plan = session.architecture_plan
    v = plan.validation
    if v is None:
        from services.architecture_remediation import revalidate_plan

        plan = revalidate_plan(
            session.spec, plan.model_copy(deep=True)
        )
    elif not v.can_approve:
        raise HTTPException(
            status_code=409,
            detail=v.approval_hint or "Resolve structural failures before approval.",
        )

    plan.architecture_approved = True
    session.architecture_plan = plan
    session_store.save(session)
    return ArchitectureResponse(session_id=session_id, plan=plan)


@router.post(
    "/sessions/{session_id}/architecture/validate",
    response_model=ArchitectureResponse,
)
def validate_architecture(session_id: str) -> ArchitectureResponse:
    """Re-run validation on the current plan without regenerating."""
    session = session_store.get(session_id)
    if session is None:
        raise HTTPException(
            status_code=404,
            detail=(
                "Session not found. Start a new interview or use a session id "
                "saved in Azure Blob (launchpad/sessions/) or data/sessions/."
            ),
        )
    if session.architecture_plan is None:
        raise HTTPException(status_code=404, detail="No architecture plan yet.")

    plan = revalidate_plan(session.spec, session.architecture_plan.model_copy(deep=True))
    session.architecture_plan = plan
    session_store.save(session)
    return ArchitectureResponse(session_id=session_id, plan=plan)


@router.get("/catalog/agents", response_model=CatalogAgentsResponse)
def get_catalog_agents() -> CatalogAgentsResponse:
    """All Affine built agents from data/spec.json (Agent Library)."""
    settings = get_settings()
    agents = load_all_catalog_agents(settings)
    return CatalogAgentsResponse(agents=agents, count=len(agents))


@router.get("/workflows", response_model=WorkflowsIndexResponse)
@router.get("/launchpad/workflows", response_model=WorkflowsIndexResponse)
def list_launchpad_workflows() -> WorkflowsIndexResponse:
    """Saved workflow builder snapshots (Azure Blob or local mirror)."""
    return WorkflowsIndexResponse(workflows=builder_store.list_workflow_index())


@router.get(
    "/sessions/{session_id}/builder",
    response_model=BuilderWorkflowResponse,
)
def get_builder_workflow(session_id: str) -> BuilderWorkflowResponse:
    workflow = builder_store.load_workflow(session_id)
    if workflow is None:
        session = session_store.get(session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="Builder workflow not found.")
        from services.builder_sync import sync_workflow_from_session

        sync_workflow_from_session(session)
        workflow = builder_store.load_workflow(session_id)
    if workflow is None:
        raise HTTPException(status_code=404, detail="Builder workflow not found.")
    return BuilderWorkflowResponse(workflow=workflow)


@router.put(
    "/sessions/{session_id}/builder",
    response_model=BuilderWorkflowResponse,
)
def save_builder_workflow(
    session_id: str,
    body: dict,
) -> BuilderWorkflowResponse:
    """Persist canvas + plan JSON to shared storage."""
    builder_store.save_workflow(session_id, body)
    loaded = builder_store.load_workflow(session_id)
    return BuilderWorkflowResponse(workflow=loaded or body)


@router.delete("/sessions/{session_id}", status_code=204)
def remove_session(session_id: str) -> None:
    if not session_store.delete(session_id):
        raise HTTPException(
            status_code=404,
            detail=(
                "Session not found. Start a new interview or use a session id "
                "saved in Azure Blob (launchpad/sessions/) or data/sessions/."
            ),
        )
