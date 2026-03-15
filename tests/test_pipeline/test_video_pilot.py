"""Tests for video pilot run configuration (P3-13).

Validates pilot config, ad spec generation, budget compliance,
audience/goal balancing, and result summary calculations.
"""

from __future__ import annotations

from iterate.pilot_config import (
    PILOT_AD_COUNT,
    PILOT_BUDGET_CAP_PER_AD,
    PILOT_VIDEO_VARIANTS,
    PilotAdSpec,
    PilotConfig,
    PilotResult,
    build_pilot_ad_specs,
    check_budget_compliance,
)


# --- Config Validation ---


def test_default_config_is_valid() -> None:
    """Default PilotConfig passes validation."""
    config = PilotConfig()
    assert config.is_valid
    assert config.ad_count == PILOT_AD_COUNT
    assert config.video_variants_per_ad == PILOT_VIDEO_VARIANTS
    assert config.budget_cap_per_ad == PILOT_BUDGET_CAP_PER_AD
    assert config.video_enabled is True


def test_invalid_config_zero_ads() -> None:
    """Config with 0 ads fails validation."""
    config = PilotConfig(ad_count=0)
    assert not config.is_valid
    errors = config.validate()
    assert any("ad_count" in e for e in errors)


def test_invalid_config_empty_segments() -> None:
    """Config with no audience segments fails validation."""
    config = PilotConfig(audience_segments=[])
    assert not config.is_valid


# --- Ad Spec Generation ---


def test_build_pilot_ad_specs_count() -> None:
    """build_pilot_ad_specs returns correct number of specs."""
    config = PilotConfig(ad_count=10)
    specs = build_pilot_ad_specs(config)
    assert len(specs) == 10
    assert all(isinstance(s, PilotAdSpec) for s in specs)


def test_ad_specs_alternate_segments() -> None:
    """Ad specs alternate audience segments for balanced mix."""
    config = PilotConfig(ad_count=10)
    specs = build_pilot_ad_specs(config)
    parent_count = sum(1 for s in specs if s.audience_segment == "parent-facing")
    student_count = sum(1 for s in specs if s.audience_segment == "student-facing")
    assert parent_count == 5
    assert student_count == 5


def test_ad_specs_alternate_goals() -> None:
    """Ad specs alternate campaign goals for balanced mix."""
    config = PilotConfig(ad_count=10)
    specs = build_pilot_ad_specs(config)
    awareness = sum(1 for s in specs if s.campaign_goal == "awareness")
    conversion = sum(1 for s in specs if s.campaign_goal == "conversion")
    assert awareness == 5
    assert conversion == 5


def test_ad_specs_unique_ids() -> None:
    """Each ad spec has a unique ad_id."""
    config = PilotConfig(ad_count=10)
    specs = build_pilot_ad_specs(config)
    ids = [s.ad_id for s in specs]
    assert len(ids) == len(set(ids))


# --- Budget Compliance ---


def test_budget_within_cap() -> None:
    """Cost within budget cap passes."""
    assert check_budget_compliance(15.00, 20.00) is True


def test_budget_exceeds_cap() -> None:
    """Cost exceeding budget cap fails."""
    assert check_budget_compliance(25.00, 20.00) is False


# --- Pilot Result ---


def test_pilot_result_metrics() -> None:
    """PilotResult computes derived metrics correctly."""
    result = PilotResult(
        total_ads=10,
        ads_with_video=8,
        ads_degraded=2,
        total_video_cost_usd=16.00,
        avg_attribute_pass_rate=0.85,
        avg_coherence_score=7.2,
        regen_triggered=3,
        regen_succeeded=2,
    )
    assert result.video_success_rate == 80.0
    assert result.degradation_rate == 20.0
    assert result.cost_per_ad_with_video == 2.00


def test_pilot_result_zero_ads() -> None:
    """PilotResult handles zero ads without division error."""
    result = PilotResult(
        total_ads=0,
        ads_with_video=0,
        ads_degraded=0,
        total_video_cost_usd=0.0,
        avg_attribute_pass_rate=0.0,
        avg_coherence_score=0.0,
        regen_triggered=0,
        regen_succeeded=0,
    )
    assert result.video_success_rate == 0.0
    assert result.degradation_rate == 0.0
    assert result.cost_per_ad_with_video == 0.0
