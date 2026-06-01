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
    row_count_hint: int | None = None
    columns: list[dict] = Field(default_factory=list)
    relevance_score: float | None = None
    quality_score: float | None = None
    match_reason: str | None = None


class SearchTopicOut(BaseModel):
    id: str
    title: str
    description: str
    icon: str = "chart"
    dataset_count: int = 0
    path_count: int = 0


class GuidedTopicOut(BaseModel):
    id: str
    title: str
    description: str
    icon: str = "chart"
    path_count: int = 0


class GuidedPathPair(BaseModel):
    path_id: str
    title: str
    topic: str
    quality: str
    description: str
    user_intent: str
    resource_ids: list[str]
    join_hint: list[dict[str, str]] = Field(default_factory=list)
    why: str
    datasets: list[CatalogResult] = Field(default_factory=list)


class GuidedSuggestResponse(BaseModel):
    query: str
    topic: str | None = None
    paraphrase: str | None = None
    recommended_pairs: list[GuidedPathPair] = Field(default_factory=list)
    datasets: list[CatalogResult] = Field(default_factory=list)
    fallback_message: str | None = None


class SearchResponse(BaseModel):
    query: str
    topic: str | None = None
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
    join_on: list[dict[str, str]] | None = None


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
    updated_at: datetime | None = None


class SessionResponse(BaseModel):
    id: str
    status: str
    resource_ids: list[str]


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)


class ChatTurn(BaseModel):
    role: str
    content: str


class ChatResponse(BaseModel):
    reply: str
    questions_used: int
    questions_remaining: int
    limit_reached: bool
    grounded: bool = True
    ai_paused: bool = False
    messages: list[ChatTurn] = Field(default_factory=list)
