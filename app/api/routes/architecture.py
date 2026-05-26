"""Architecture planning API."""

from fastapi import APIRouter, HTTPException

from app.api.dependencies import get_planner_service
from app.core.exceptions import KnowledgeBaseError
from app.schemas.architecture_graph import ArchitecturePlanRequest, ArchitecturePlanResponse

router = APIRouter(prefix="/architecture", tags=["Architecture"])


@router.post("/plan", response_model=ArchitecturePlanResponse)
async def plan_architecture(request: ArchitecturePlanRequest) -> ArchitecturePlanResponse:
    """
    Match spec against agent catalog, decide reuse vs build,
    return graph nodes + edges for canvas rendering.
    """
    try:
        planner = get_planner_service()
        if request.session_id:
            return await planner.plan_from_session(request.session_id)
        if request.spec:
            return await planner.plan(request.spec, request.session_id or "")
        raise HTTPException(
            status_code=400,
            detail="Provide session_id or spec in request body",
        )
    except KnowledgeBaseError as e:
        raise HTTPException(status_code=422, detail=e.message) from e
