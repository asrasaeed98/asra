from datetime import datetime

from pydantic import BaseModel, Field


class CatalogResult(BaseModel):
    id: str
    portal: str
    title: str
    description: str | None = None
    organization: str | None = None
    tags: list[str] = Field(default_factory=list)
    format: str | None = None
    license_normalized: str
    license_display: str
    attribution_required: bool
    attribution_text: str
    publisher: str
    source_url: str
    resource_url: str | None = None
    byte_size: int | None = None


class SearchResponse(BaseModel):
    query: str
    page: int
    limit: int
    total: int
    results: list[CatalogResult]


class SyncResponse(BaseModel):
    indexed: dict[str, int]
    message: str
