from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from findings_api.db import get_db
from findings_api.models import CatalogResource
from findings_api.routers.search import _to_result
from findings_api.schemas import CatalogResult

router = APIRouter(prefix="/datasets", tags=["datasets"])


@router.get("/{resource_id}", response_model=CatalogResult)
def get_dataset(resource_id: str, db: Session = Depends(get_db)):
    row = db.get(CatalogResource, resource_id)
    if not row:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return _to_result(row)
