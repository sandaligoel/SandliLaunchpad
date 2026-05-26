"""Smart interview API — slot-filling spec completion."""

from fastapi import APIRouter, HTTPException

from app.api.dependencies import get_interview_service, get_planner_service
from app.core.exceptions import KnowledgeBaseError
from app.schemas.architecture_graph import ArchitecturePlanRequest, ArchitecturePlanResponse
from app.schemas.interview import (
    InterviewAnswerRequest,
    InterviewAnswerResponse,
    InterviewStartRequest,
    InterviewStartResponse,
    InterviewStatusResponse,
)
from app.services.session_store import get_plan, get_session, list_sessions

router = APIRouter(prefix="/interview", tags=["Interview"])


@router.post("/start", response_model=InterviewStartResponse)
async def start_interview(request: InterviewStartRequest) -> InterviewStartResponse:
    """
    Start a smart interview: extract slots from problem statement,
    return the first targeted question (not free-form chat).
    """
    try:
        return await get_interview_service().start(request.problem_statement)
    except KnowledgeBaseError as e:
        raise HTTPException(status_code=422, detail=e.message) from e


@router.post("/answer", response_model=InterviewAnswerResponse)
async def answer_interview(request: InterviewAnswerRequest) -> InterviewAnswerResponse:
    """Answer the current interview question; receive next question or completion."""
    try:
        return await get_interview_service().answer(
            request.session_id,
            request.answer,
            force_complete=request.force_complete,
        )
    except KnowledgeBaseError as e:
        raise HTTPException(status_code=422, detail=e.message) from e


@router.get("/{session_id}", response_model=InterviewStatusResponse)
async def interview_status(session_id: str) -> InterviewStatusResponse:
    """Get current spec completion status and pending slots."""
    try:
        return get_interview_service().status(session_id)
    except KnowledgeBaseError as e:
        raise HTTPException(status_code=404, detail=e.message) from e


@router.get("/sessions")
async def list_interview_sessions() -> dict[str, list[str]]:
    """List persisted interview session IDs (disk + memory)."""
    return {"session_ids": list_sessions()}


@router.post("/{session_id}/plan", response_model=ArchitecturePlanResponse)
async def plan_from_session(session_id: str) -> ArchitecturePlanResponse:
    """Generate architecture graph from completed interview session (Problem 3)."""
    try:
        return await get_planner_service().plan_from_session(session_id)
    except KnowledgeBaseError as e:
        raise HTTPException(status_code=422, detail=e.message) from e


@router.get("/{session_id}/plan", response_model=ArchitecturePlanResponse)
async def get_saved_plan(session_id: str) -> ArchitecturePlanResponse:
    """Return last generated architecture plan for this session (persisted to disk)."""
    plan = get_plan(session_id)
    if not plan:
        raise HTTPException(
            status_code=404,
            detail="No saved plan for this session. POST .../plan first.",
        )
    return plan
