from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from findings_api.db import Base

JsonType = JSON().with_variant(JSONB(), "postgresql")


class CatalogResource(Base):
    __tablename__ = "catalog_resources"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    portal: Mapped[str] = mapped_column(String(32), index=True)
    title: Mapped[str] = mapped_column(String(512))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    organization: Mapped[str | None] = mapped_column(String(512), nullable=True)
    tags: Mapped[list | None] = mapped_column(JsonType, nullable=True)
    format: Mapped[str | None] = mapped_column(String(32), nullable=True)
    license_normalized: Mapped[str] = mapped_column(String(32), index=True)
    license_raw: Mapped[str | None] = mapped_column(String(255), nullable=True)
    license_display: Mapped[str] = mapped_column(String(128))
    attribution_required: Mapped[bool] = mapped_column(Boolean, default=False)
    attribution_text: Mapped[str] = mapped_column(Text)
    publisher: Mapped[str] = mapped_column(String(512))
    source_url: Mapped[str] = mapped_column(String(1024))
    resource_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    columns: Mapped[list | None] = mapped_column(JsonType, nullable=True)
    row_count_hint: Mapped[int | None] = mapped_column(nullable=True)
    byte_size: Mapped[int | None] = mapped_column(nullable=True)
    ingestible: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    ingest_block_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    detected_format: Mapped[str | None] = mapped_column(String(32), nullable=True)
    probed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    search_text: Mapped[str] = mapped_column(Text, index=True)
    synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class AppVisit(Base):
    """Anonymous page view — one row per navigation (visitor_id from browser localStorage)."""

    __tablename__ = "app_visits"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    visitor_id: Mapped[str] = mapped_column(String(36), index=True)
    path: Mapped[str] = mapped_column(String(512))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )


class AnalysisSession(Base):
    __tablename__ = "analysis_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    visitor_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(32), default="created", index=True)
    phase: Mapped[str] = mapped_column(String(32), default="pending")
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    percent: Mapped[int] = mapped_column(default=0)
    resource_ids: Mapped[list] = mapped_column(JsonType)
    user_intent: Mapped[str | None] = mapped_column(Text, nullable=True)
    config: Mapped[dict] = mapped_column(JsonType, default=dict)
    row_counts: Mapped[dict | None] = mapped_column(JsonType, nullable=True)
    preview: Mapped[dict | None] = mapped_column(JsonType, nullable=True)
    duckdb_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ApiUsage(Base):
    """Monthly ledger of Anthropic token spend, keyed by YYYY-MM (UTC)."""

    __tablename__ = "api_usage"

    month: Mapped[str] = mapped_column(String(7), primary_key=True)
    tokens_in: Mapped[int] = mapped_column(default=0)
    tokens_out: Mapped[int] = mapped_column(default=0)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    calls: Mapped[int] = mapped_column(default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
