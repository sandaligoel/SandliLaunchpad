"""FastAPI routes for the Phase 2 requirements interview."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from api import session_store
from config import get_settings
from schemas.architecture_spec import InterviewSession
from services.interview import run_interview_turn, start_session

router = APIRouter(prefix="/api")


class StartSessionRequest(BaseModel):
    problem_statement: str = Field(..., min_length=10, max_length=8000)


class TurnRequest(BaseModel):
    answer: str = Field(..., min_length=1, max_length=2000)


class SessionResponse(BaseModel):
    session: InterviewSession


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


@router.get("/sessions/{session_id}", response_model=SessionResponse)
def get_session(session_id: str) -> SessionResponse:
    """Return full session state (spec + messages + pending question)."""
    session = session_store.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return SessionResponse(session=session)


@router.post("/sessions/{session_id}/turn", response_model=SessionResponse)
def submit_turn(session_id: str, body: TurnRequest) -> SessionResponse:
    """Submit an answer to the current question and advance the interview."""
    session = session_store.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
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

    session_store.save(session)
    return SessionResponse(session=session)


@router.delete("/sessions/{session_id}", status_code=204)
def remove_session(session_id: str) -> None:
    if not session_store.delete(session_id):
        raise HTTPException(status_code=404, detail="Session not found")
