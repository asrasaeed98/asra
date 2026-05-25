from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text, func
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
    byte_size: Mapped[int | None] = mapped_column(nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    search_text: Mapped[str] = mapped_column(Text, index=True)
    synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
