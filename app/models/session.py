# Ad-Ops-Autopilot — Session model (PA-02)
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Session(Base):
    """One pipeline run — immutable after completion."""

    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    # String user_id for dev (mock auth). PA-03 adds FK to users.id.
    user_id: Mapped[str] = mapped_column(String(256), index=True)
    config: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(32), default="pending")
    celery_task_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    results_summary: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    ledger_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    output_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships (activated when FK is added in PA-03)
    curated_sets = relationship("CuratedSet", back_populates="session")
