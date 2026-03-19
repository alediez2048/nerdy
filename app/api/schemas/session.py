# Ad-Ops-Autopilot — Session schemas (PA-04, PC-00)
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


class SessionType(str, Enum):
    image = "image"
    video = "video"


class SessionConfig(BaseModel):
    """Typed session configuration — matches PRD Section 4.7.2 + PB-07 + PC-00."""

    session_type: SessionType = SessionType.image
    audience: Audience
    campaign_goal: CampaignGoal
    ad_count: int = Field(default=50, ge=1, le=200)
    cycle_count: int = Field(default=3, ge=1, le=10)
    quality_threshold: float = Field(default=7.0, ge=5.0, le=10.0)
    dimension_weights: DimensionWeights = DimensionWeights.equal
    model_tier: ModelTier = ModelTier.standard
    budget_cap_usd: float | None = Field(default=None, ge=1.0)
    image_enabled: bool = True
    aspect_ratio: AspectRatio = AspectRatio.square
    persona: Persona = Persona.auto
    # PB-11: Creative direction fields
    key_message: str = ""
    creative_brief: str = "auto"
    copy_on_image: bool = False
    # PC-00: Video session fields (ignored when session_type=image)
    video_count: int = Field(default=3, ge=1, le=20)
    video_duration: int = Field(default=10, ge=5, le=10)
    video_audio_mode: str = "silent"
    video_aspect_ratio: str = "9:16"
    video_scene: str = ""
    video_visual_style: str = ""
    video_camera_movement: str = ""
    video_subject_action: str = ""
    video_setting: str = ""
    video_lighting_mood: str = ""
    video_audio_detail: str = ""
    video_color_palette: str = ""
    video_negative_prompt: str = ""


class SessionCreate(BaseModel):
    """Request body for POST /sessions."""

    name: str | None = None
    config: SessionConfig


class SessionUpdate(BaseModel):
    """Request body for PATCH /sessions/{id}."""

    name: str = Field(min_length=1, max_length=256)


class ProgressSummary(BaseModel):
    """Progress summary for running sessions (from Redis)."""

    current_cycle: int = 0
    ads_generated: int = 0
    ads_evaluated: int = 0
    ads_published: int = 0
    current_score_avg: float = 0.0
    cost_so_far: float = 0.0


class SessionAdPreview(BaseModel):
    """Lightweight first-ad preview for session cards."""

    ad_id: str = ""
    image_url: str | None = None
    primary_text: str = ""
    headline: str = ""
    cta_button: str | None = None
    status: str = "in_progress"
    aggregate_score: float = 0.0


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
    results_summary: dict[str, Any] | None = None
    ad_preview: SessionAdPreview | None = None


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
