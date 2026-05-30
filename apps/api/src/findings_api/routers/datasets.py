from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from findings_api.db import get_db
from findings_api.models import CatalogResource
from findings_api.routers.search import _to_result
from findings_api.schemas import CatalogResult

router = APIRouter(prefix="/datasets", tags=["datasets"])

_MAX_BATCH = 2


@router.get("/batch", response_model=list[CatalogResult])
def get_datasets_batch(
    ids: str = Query(..., description="Comma-separated catalog resource ids (max 2)"),
    db: Session = Depends(get_db),
):
    """Fetch catalog metadata for review before ingest."""
    id_list = [part.strip() for part in ids.split(",") if part.strip()]
    if not id_list:
        raise HTTPException(status_code=422, detail="At least one id is required")
    if len(id_list) > _MAX_BATCH:
        raise HTTPException(status_code=422, detail=f"At most {_MAX_BATCH} datasets allowed")

    out: list[CatalogResult] = []
    for resource_id in id_list:
        row = db.get(CatalogResource, resource_id)
        if not row:
            raise HTTPException(status_code=404, detail=f"Unknown resource: {resource_id}")
        if not row.ingestible:
            raise HTTPException(status_code=400, detail=f"Dataset not available for analysis: {resource_id}")
        out.append(_to_result(row))
    return out


@router.get("/{resource_id}", response_model=CatalogResult)
def get_dataset(resource_id: str, db: Session = Depends(get_db)):
    row = db.get(CatalogResource, resource_id)
    if not row:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return _to_result(row)
