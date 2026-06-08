# Ad-Ops-Autopilot — Brand assets (PJ-01)
"""Uploaded brand assets: logos, style guide PDFs, fonts, references.

Files live on the Railway volume at
``output/brand_assets/<user_id>/<asset_uuid>.<ext>``. The ``extracted_facts``
column stores what the Gemini multimodal vision pass found (palette hex
codes, detected fonts, mood descriptors) once PJ-03's Celery task has
processed the upload.
"""
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


def _new_uuid() -> str:
    """Generate a UUID as string for SQLite/Postgres portability."""
    return str(uuid.uuid4())


class BrandAsset(Base):
    """Single uploaded asset for a user."""

    __tablename__ = "brand_assets"

    # String UUIDs for portability (SQLite has no native UUID type).
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    user_id: Mapped[str] = mapped_column(String(256), nullable=False)
    # 'logo' | 'style_guide' | 'font' | 'reference' | 'other'
    asset_type: Mapped[str] = mapped_column(String(32), nullable=False)
    original_filename: Mapped[str | None] = mapped_column(String(512), nullable=True)
    # Relative to output/brand_assets/ (i.e. "<user_id>/<uuid>.<ext>").
    storage_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Set by the PJ-03 vision-pass Celery task. Null until extracted.
    extracted_facts: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        Index("ix_brand_assets_user", "user_id"),
    )
