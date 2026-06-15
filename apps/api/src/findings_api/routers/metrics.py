from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from findings_api.db import get_db
from findings_api.models import AppVisit
from findings_api.visitor_ids import normalize_visitor_id

router = APIRouter(prefix="/metrics", tags=["metrics"])


class VisitRequest(BaseModel):
    visitor_id: str = Field(..., min_length=36, max_length=36)
    path: str = Field(..., min_length=1, max_length=512)


class VisitResponse(BaseModel):
    ok: bool = True


@router.post("/visit", response_model=VisitResponse)
def record_visit(body: VisitRequest, db: Session = Depends(get_db)):
    """Record an anonymous page view (browser-generated visitor_id)."""
    visitor_id = normalize_visitor_id(body.visitor_id)
    if not visitor_id:
        raise HTTPException(status_code=400, detail="visitor_id must be a UUID")

    path = body.path.strip()
    if not path.startswith("/"):
        path = f"/{path}"

    db.add(
        AppVisit(
            visitor_id=visitor_id,
            path=path[:512],
            created_at=datetime.now(timezone.utc),
        )
    )
    db.commit()
    return VisitResponse()
