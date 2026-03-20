# PC-04: Campaign schemas
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


class CampaignCreate(BaseModel):
    """Request schema for creating a campaign."""

    name: str = Field(..., min_length=1, max_length=256)
    description: str | None = Field(default=None, max_length=2000)
    audience: str | None = Field(default=None, max_length=32)
    campaign_goal: str | None = Field(default=None, max_length=32)
    default_config: dict[str, Any] = Field(default_factory=dict)

    @field_validator("name")
    @classmethod
    def validate_name_not_whitespace(cls, v: str) -> str:
        """Reject whitespace-only names."""
        if not v or not v.strip():
            raise ValueError("Campaign name cannot be empty or whitespace-only")
        return v.strip()


class CampaignUpdate(BaseModel):
    """Request schema for updating a campaign."""

    name: str | None = Field(default=None, min_length=1, max_length=256)
    description: str | None = Field(default=None, max_length=2000)
    status: str | None = Field(default=None, pattern="^(active|archived)$")

    @field_validator("name")
    @classmethod
    def validate_name_not_whitespace(cls, v: str | None) -> str | None:
        """Reject whitespace-only names."""
        if v is not None:
            if not v or not v.strip():
                raise ValueError("Campaign name cannot be empty or whitespace-only")
            return v.strip()
        return v


class CampaignStats(BaseModel):
    """Aggregate statistics for a campaign (PC-11)."""

    total_sessions: int = 0
    sessions_by_status: dict[str, int] = {}
    total_ads_generated: int = 0
    total_ads_published: int = 0
    avg_quality_score: float = 0.0
    total_cost: float = 0.0
    session_types: dict[str, int] = {}


class CampaignSummary(BaseModel):
    """Summary schema for campaign list items."""

    id: int
    campaign_id: str
    name: str
    description: str | None
    audience: str | None
    campaign_goal: str | None
    status: str
    created_at: datetime
    session_count: int
    # PC-11: Lightweight summary stats
    total_ads_published: int = 0
    avg_quality_score: float = 0.0


class CampaignDetail(BaseModel):
    """Detail schema for single campaign view."""

    id: int
    campaign_id: str
    name: str
    description: str | None
    audience: str | None
    campaign_goal: str | None
    default_config: dict[str, Any]
    status: str
    created_at: datetime
    updated_at: datetime | None
    session_count: int
    # PC-11: Full stats
    stats: CampaignStats


class CampaignListResponse(BaseModel):
    """Response schema for paginated campaign list."""

    campaigns: list[CampaignSummary]
    total: int
    offset: int
    limit: int
