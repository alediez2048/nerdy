# Ad-Ops-Autopilot — Session schemas (PA-04)
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Audience(str, Enum):
    parents = "parents"
    students = "students"


class CampaignGoal(str, Enum):
    awareness = "awareness"
    conversion = "conversion"


class DimensionWeights(str, Enum):
    awareness_profile = "awareness_profile"
    conversion_profile = "conversion_profile"
    equal = "equal"


class ModelTier(str, Enum):
    standard = "standard"
    premium = "premium"


class AspectRatio(str, Enum):
    square = "1:1"
    portrait = "4:5"
    story = "9:16"


class Persona(str, Enum):
    auto = "auto"
    athlete_recruit = "athlete_recruit"
    suburban_optimizer = "suburban_optimizer"
    immigrant_navigator = "immigrant_navigator"
    cultural_investor = "cultural_investor"
    system_optimizer = "system_optimizer"
    neurodivergent_advocate = "neurodivergent_advocate"
    burned_returner = "burned_returner"


class SessionConfig(BaseModel):
    """Typed session configuration — matches PRD Section 4.7.2 + PB-07."""

    audience: Audience
    campaign_goal: CampaignGoal
    ad_count: int = Field(default=50, ge=1, le=200)
    cycle_count: int = Field(default=3, ge=1, le=10)
    quality_threshold: float = Field(default=7.0, ge=5.0, le=10.0)
    dimension_weights: DimensionWeights = DimensionWeights.equal
    model_tier: ModelTier = ModelTier.standard
    budget_cap_usd: float | None = Field(default=None, ge=1.0)
    image_enabled: bool = True
    aspect_ratios: list[AspectRatio] = Field(default_factory=lambda: [AspectRatio.square])
    persona: Persona = Persona.auto
    # PB-11: Creative direction fields
    key_message: str = ""
    creative_brief: str = "auto"
    copy_on_image: bool = False


class SessionCreate(BaseModel):
    """Request body for POST /sessions."""

    name: str | None = None
    config: SessionConfig


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

    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: str
    name: str | None = None
    status: str
    config: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    progress_summary: ProgressSummary | None = None


class SessionDetail(BaseModel):
    """Session detail (GET /sessions/{id})."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: str
    name: str | None = None
    user_id: str
    config: dict[str, Any]
    status: str
    celery_task_id: str | None = None
    results_summary: dict[str, Any] | None = None
    ledger_path: str | None = None
    output_path: str | None = None
    created_at: datetime
    updated_at: datetime | None = None
    completed_at: datetime | None = None


class SessionListResponse(BaseModel):
    """Paginated session list response."""

    sessions: list[SessionSummary]
    total: int
    offset: int
    limit: int
