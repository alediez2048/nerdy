# Ad-Ops-Autopilot — Session schemas (PA-04)
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class SessionCreate(BaseModel):
    """Request body for POST /sessions."""

    config: dict[str, Any] = Field(default_factory=dict)


class ProgressSummary(BaseModel):
    """Progress summary for running sessions (from Redis)."""

    current_cycle: int = 0
    ads_generated: int = 0
    ads_evaluated: int = 0
    ads_published: int = 0
    current_score_avg: float = 0.0
    cost_so_far: float = 0.0


class SessionSummary(BaseModel):
    """Session list item."""

    id: int
    session_id: str
    status: str
    created_at: datetime
    progress_summary: ProgressSummary | None = None

    class Config:
        from_attributes = True


class SessionDetail(BaseModel):
    """Session detail (GET /sessions/{id})."""

    id: int
    session_id: str
    user_id: str
    config: dict[str, Any]
    status: str
    celery_task_id: str | None
    results_summary: dict[str, Any] | None
    created_at: datetime

    class Config:
        from_attributes = True
