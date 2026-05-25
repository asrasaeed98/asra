from uuid import uuid4

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter(prefix="/sessions", tags=["sessions"])


class CreateSessionRequest(BaseModel):
    resource_ids: list[str] = Field(..., min_length=1, max_length=2)
    user_intent: str | None = None


class SessionResponse(BaseModel):
    id: str
    status: str
    resource_ids: list[str]


@router.post("", response_model=SessionResponse)
def create_session(body: CreateSessionRequest):
    """Create analysis session — stub until DB + ingest (slice 3)."""
    session_id = str(uuid4())
    return SessionResponse(
        id=session_id,
        status="created",
        resource_ids=body.resource_ids,
    )


@router.get("/{session_id}/status")
def session_status(session_id: str):
    return {
        "session_id": session_id,
        "phase": "pending",
        "message": "Analysis worker not connected yet.",
        "percent": 0,
    }


@router.get("/{session_id}/results")
def session_results(session_id: str):
    return {
        "session_id": session_id,
        "findings": [],
        "charts": [],
        "ai_summary": None,
        "message": "Run analysis after ingest (slices 4–7).",
    }
