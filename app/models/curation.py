# Ad-Ops-Autopilot — Curation models (PA-02)
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class CuratedSet(Base):
    """A curated collection of ads from a session."""

    __tablename__ = "curated_sets"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(Integer, ForeignKey("sessions.id"), index=True)
    name: Mapped[str] = mapped_column(String(256), default="Default Set")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=True
    )

    # Relationships
    session = relationship("Session", back_populates="curated_sets")
    ads = relationship("CuratedAd", back_populates="curated_set", order_by="CuratedAd.position")


class CuratedAd(Base):
    """An ad selected into a curated set — with optional annotation and light edits."""

    __tablename__ = "curated_ads"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    curated_set_id: Mapped[int] = mapped_column(Integer, ForeignKey("curated_sets.id"), index=True)
    ad_id: Mapped[str] = mapped_column(String(64), index=True)
    position: Mapped[int] = mapped_column(Integer, default=0)
    annotation: Mapped[str | None] = mapped_column(Text, nullable=True)
    edited_copy: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    curated_set = relationship("CuratedSet", back_populates="ads")
