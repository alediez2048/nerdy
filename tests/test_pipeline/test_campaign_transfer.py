"""Tests for cross-campaign transfer (P4-04).

Validates campaign scope classification, pattern library CRUD,
win rate aggregation, and transfer recommendations.
"""

from __future__ import annotations

from pathlib import Path

from iterate.campaign_transfer import (
    UNIVERSAL,
    PatternLibrary,
    PatternRecord,
    classify_scope,
    get_transfer_recommendations,
)


# --- Scope Classification ---


def test_structural_patterns_are_universal() -> None:
    """Hook type, CTA style, etc. are universal (transferable)."""
    assert classify_scope({"pattern_type": "hook_type"}) == UNIVERSAL
    assert classify_scope({"pattern_type": "cta_style"}) == UNIVERSAL
    assert classify_scope({"pattern_type": "emotional_angle"}) == UNIVERSAL
    assert classify_scope({"pattern_type": "body_structure"}) == UNIVERSAL
    assert classify_scope({"pattern_type": "composition"}) == UNIVERSAL
    assert classify_scope({"pattern_type": "color_palette"}) == UNIVERSAL


def test_content_patterns_are_campaign_specific() -> None:
    """Claims, proof points, pricing are campaign-specific."""
    assert classify_scope({"pattern_type": "claims"}) != UNIVERSAL
    assert classify_scope({"pattern_type": "proof_points"}) != UNIVERSAL
    assert classify_scope({"pattern_type": "pricing"}) != UNIVERSAL
    assert classify_scope({"pattern_type": "testimonials"}) != UNIVERSAL


# --- Pattern Library ---


def test_pattern_library_add_and_get(tmp_path: Path) -> None:
    """PatternLibrary stores and retrieves patterns."""
    lib = PatternLibrary()
    lib.add_pattern(PatternRecord(
        pattern_type="hook_type",
        pattern_value="question",
        campaign_scope=UNIVERSAL,
        win_rate=0.65,
        sample_size=10,
        audience="parents",
        source="ab_test",
    ))
    universal = lib.get_universal_patterns()
    assert len(universal) == 1
    assert universal[0].pattern_value == "question"


def test_pattern_library_universal_vs_campaign() -> None:
    """Universal and campaign-specific patterns are isolated."""
    lib = PatternLibrary()
    lib.add_pattern(PatternRecord(
        pattern_type="hook_type", pattern_value="question",
        campaign_scope=UNIVERSAL, win_rate=0.6, sample_size=5,
        audience="parents", source="test",
    ))
    lib.add_pattern(PatternRecord(
        pattern_type="claims", pattern_value="200+ point improvement",
        campaign_scope="campaign:sat_prep", win_rate=0.7, sample_size=8,
        audience="parents", source="test",
    ))
    assert len(lib.get_universal_patterns()) == 1
    assert len(lib.get_campaign_patterns("sat_prep")) == 1
    assert len(lib.get_campaign_patterns("other_campaign")) == 0


def test_pattern_library_audience_filter() -> None:
    """Patterns can be filtered by audience."""
    lib = PatternLibrary()
    lib.add_pattern(PatternRecord(
        pattern_type="hook_type", pattern_value="question",
        campaign_scope=UNIVERSAL, win_rate=0.6, sample_size=5,
        audience="parents", source="test",
    ))
    lib.add_pattern(PatternRecord(
        pattern_type="hook_type", pattern_value="statistic",
        campaign_scope=UNIVERSAL, win_rate=0.5, sample_size=5,
        audience="students", source="test",
    ))
    parent_patterns = lib.get_universal_patterns(audience="parents")
    assert len(parent_patterns) == 1
    assert parent_patterns[0].pattern_value == "question"


def test_pattern_library_save_load(tmp_path: Path) -> None:
    """PatternLibrary persists to and loads from JSON."""
    lib = PatternLibrary()
    lib.add_pattern(PatternRecord(
        pattern_type="hook_type", pattern_value="question",
        campaign_scope=UNIVERSAL, win_rate=0.65, sample_size=10,
        audience="parents", source="test",
    ))
    path = str(tmp_path / "patterns.json")
    lib.save(path)

    lib2 = PatternLibrary()
    lib2.load(path)
    assert len(lib2.get_universal_patterns()) == 1


# --- Transfer Recommendations ---


def test_transfer_recommendations_ranked() -> None:
    """Recommendations sorted by win rate, filtered by min sample size."""
    lib = PatternLibrary()
    lib.add_pattern(PatternRecord(
        pattern_type="hook_type", pattern_value="question",
        campaign_scope=UNIVERSAL, win_rate=0.8, sample_size=10,
        audience="parents", source="test",
    ))
    lib.add_pattern(PatternRecord(
        pattern_type="hook_type", pattern_value="statistic",
        campaign_scope=UNIVERSAL, win_rate=0.5, sample_size=10,
        audience="parents", source="test",
    ))
    lib.add_pattern(PatternRecord(
        pattern_type="hook_type", pattern_value="low_sample",
        campaign_scope=UNIVERSAL, win_rate=0.9, sample_size=1,
        audience="parents", source="test",
    ))
    recs = get_transfer_recommendations(lib, target_audience="parents")
    # low_sample excluded (sample_size < 3), question first (higher win rate)
    assert len(recs) == 2
    assert recs[0].pattern_value == "question"


def test_transfer_excludes_campaign_specific() -> None:
    """Transfer recommendations only include universal patterns."""
    lib = PatternLibrary()
    lib.add_pattern(PatternRecord(
        pattern_type="hook_type", pattern_value="question",
        campaign_scope=UNIVERSAL, win_rate=0.6, sample_size=5,
        audience="parents", source="test",
    ))
    lib.add_pattern(PatternRecord(
        pattern_type="claims", pattern_value="specific claim",
        campaign_scope="campaign:sat", win_rate=0.9, sample_size=20,
        audience="parents", source="test",
    ))
    recs = get_transfer_recommendations(lib, target_audience="parents")
    assert all(r.campaign_scope == UNIVERSAL for r in recs)
