"""Video pilot run configuration (P3-13, PRD 4.9.9).

Defines the 10-ad pilot run parameters for validating the full
video sub-pipeline end-to-end before scaling to 50+ ads.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

PILOT_AD_COUNT = 10
PILOT_VIDEO_VARIANTS = 2
PILOT_BUDGET_CAP_PER_AD = 20.00  # USD
PILOT_VIDEO_TOGGLE = True

AUDIENCE_SEGMENTS = ["parent-facing", "student-facing"]
CAMPAIGN_GOALS = ["awareness", "conversion"]


@dataclass
class PilotConfig:
    """Configuration for a video pilot run."""

    ad_count: int = PILOT_AD_COUNT
    video_variants_per_ad: int = PILOT_VIDEO_VARIANTS
    budget_cap_per_ad: float = PILOT_BUDGET_CAP_PER_AD
    video_enabled: bool = PILOT_VIDEO_TOGGLE
    audience_segments: list[str] = field(default_factory=lambda: list(AUDIENCE_SEGMENTS))
    campaign_goals: list[str] = field(default_factory=lambda: list(CAMPAIGN_GOALS))

    def validate(self) -> list[str]:
        """Validate pilot config. Returns list of error strings (empty = valid)."""
        errors: list[str] = []
        if self.ad_count < 1:
            errors.append("ad_count must be >= 1")
        if self.video_variants_per_ad < 1:
            errors.append("video_variants_per_ad must be >= 1")
        if self.budget_cap_per_ad <= 0:
            errors.append("budget_cap_per_ad must be > 0")
        if not self.audience_segments:
            errors.append("audience_segments must not be empty")
        if not self.campaign_goals:
            errors.append("campaign_goals must not be empty")
        return errors

    @property
    def is_valid(self) -> bool:
        return len(self.validate()) == 0


@dataclass
class PilotAdSpec:
    """Specification for a single ad in the pilot run."""

    ad_id: str
    audience_segment: str
    campaign_goal: str


def build_pilot_ad_specs(config: PilotConfig) -> list[PilotAdSpec]:
    """Generate ad specs for the pilot run.

    Alternates audience segments and campaign goals to ensure
    a balanced mix (~50/50 split for each).

    Args:
        config: The pilot run configuration.

    Returns:
        List of PilotAdSpec, one per ad.
    """
    specs: list[PilotAdSpec] = []
    for i in range(config.ad_count):
        segment = config.audience_segments[i % len(config.audience_segments)]
        goal = config.campaign_goals[i % len(config.campaign_goals)]
        specs.append(PilotAdSpec(
            ad_id=f"pilot_{i:03d}",
            audience_segment=segment,
            campaign_goal=goal,
        ))

    logger.info(
        "Built %d pilot ad specs (%d segments, %d goals)",
        len(specs),
        len(config.audience_segments),
        len(config.campaign_goals),
    )
    return specs


@dataclass
class PilotResult:
    """Results summary from a pilot run."""

    total_ads: int
    ads_with_video: int
    ads_degraded: int
    total_video_cost_usd: float
    avg_attribute_pass_rate: float
    avg_coherence_score: float
    regen_triggered: int
    regen_succeeded: int

    @property
    def video_success_rate(self) -> float:
        """Percentage of ads that successfully got video."""
        if self.total_ads == 0:
            return 0.0
        return self.ads_with_video / self.total_ads * 100

    @property
    def degradation_rate(self) -> float:
        """Percentage of ads that degraded to image-only."""
        if self.total_ads == 0:
            return 0.0
        return self.ads_degraded / self.total_ads * 100

    @property
    def cost_per_ad_with_video(self) -> float:
        """Average video cost per ad that has video."""
        if self.ads_with_video == 0:
            return 0.0
        return self.total_video_cost_usd / self.ads_with_video


def check_budget_compliance(
    cost_usd: float,
    budget_cap: float,
) -> bool:
    """Check if a cost is within the budget cap."""
    return cost_usd <= budget_cap
