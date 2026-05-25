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


class SessionConfigUpdate(BaseModel):
    user_intent: str | None = None
    ml_enabled: bool | None = None
    filters: dict[str, str] | None = None
    join_keys: list[str] | None = None


class CreateSessionRequest(BaseModel):
    resource_ids: list[str] = Field(..., min_length=1, max_length=2)
    user_intent: str | None = None
    ml_enabled: bool = True


class SessionDatasetPreview(BaseModel):
    resource_id: str
    title: str
    row_count: int
    analysis_n: int | None = None
    filtered_row_count: int | None = None
    columns: list[dict] = Field(default_factory=list)


class SessionDetail(BaseModel):
    id: str
    status: str
    phase: str
    message: str | None = None
    percent: int
    resource_ids: list[str]
    user_intent: str | None = None
    config: dict = Field(default_factory=dict)
    row_counts: dict[str, int] | None = None
    preview: dict | None = None
    error: str | None = None
    catalogs: list[CatalogResult] = Field(default_factory=list)


class SessionStatusResponse(BaseModel):
    session_id: str
    status: str
    phase: str
    message: str | None = None
    percent: int
    row_counts: dict[str, int] | None = None
    estimate_remaining_sec: int | None = None


class SessionResponse(BaseModel):
    id: str
    status: str
    resource_ids: list[str]
