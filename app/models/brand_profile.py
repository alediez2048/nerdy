# Ad-Ops-Autopilot — Per-user brand profile (PJ-01)
"""One row per Clerk user — the typed-core + extras bag the pipeline reads.

Sessions are gated on ``good_enough_at IS NOT NULL`` (mirror of the BYO
Keys gate). Typed-core fields are what ``brief_expansion`` will read
directly; ``extras`` is the LLM's scratchpad for industry-specific facts
that would otherwise require a schema migration.
"""
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class BrandProfile(Base):
    """Per-user brand context. PK on Clerk user_id."""

    __tablename__ = "brand_profile"

    user_id: Mapped[str] = mapped_column(String(256), primary_key=True)

    # Typed core — the pipeline reads these directly
    business_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    industry: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    audience: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    mission: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    # Arrays stored as JSON lists for SQLite/Postgres portability.
    value_props: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    tone_descriptors: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    avoid_phrases: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    do_dont_rules: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    palette_primary_hex: Mapped[str | None] = mapped_column(String(7), nullable=True)
    palette_secondary_hex: Mapped[str | None] = mapped_column(String(7), nullable=True)
    palette_accent_hex: Mapped[str | None] = mapped_column(String(7), nullable=True)
    # Loose reference to brand_assets.id — no FK constraint to avoid the
    # create_all ordering circularity flagged in PJ-01 §Edge cases.
    logo_asset_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    # Open extension — LLM-driven, industry-specific keys
    extras: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    # Lifecycle
    onboarding_phase: Mapped[str] = mapped_column(
        String(32), nullable=False, default="identify"
    )
    good_enough_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
