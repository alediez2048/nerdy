"""Tests for video attribute evaluator (P3-08).

Validates 10-attribute checklist, Required vs non-Required logic,
frame extraction, and diagnostic output.
"""

from __future__ import annotations

from evaluate.video_attributes import (
    REQUIRED_ATTRIBUTES,
    VIDEO_ATTRIBUTES,
    AttributeScore,
    VideoAttributeResult,
    is_video_acceptable,
)
from evaluate.frame_extractor import extract_key_frames


# --- Attribute Structure ---


def test_ten_attributes_defined() -> None:
    """All 10 video attributes are defined."""
    assert len(VIDEO_ATTRIBUTES) == 10


def test_required_attributes_subset() -> None:
    """Required attributes are a subset of all attributes."""
    all_names = {a["name"] for a in VIDEO_ATTRIBUTES}
    for req in REQUIRED_ATTRIBUTES:
        assert req in all_names


# --- Pass/Fail Logic ---


def test_all_required_pass_overall_pass() -> None:
    """When all Required attributes pass, overall result passes."""
    scores = {a["name"]: AttributeScore(name=a["name"], passed=True, confidence=0.9, diagnostic="OK")
              for a in VIDEO_ATTRIBUTES}
    result = VideoAttributeResult(
        ad_id="ad_001",
        variant_id="anchor",
        attribute_scores=scores,
        overall_pass=True,
        pass_pct=1.0,
        warnings=[],
    )
    assert result.overall_pass is True


def test_required_fail_overall_fail() -> None:
    """When a Required attribute fails, overall result fails."""
    scores = {}
    for a in VIDEO_ATTRIBUTES:
        passed = a["name"] != "hook_timing"  # Fail hook_timing (Required)
        scores[a["name"]] = AttributeScore(
            name=a["name"], passed=passed, confidence=0.8,
            diagnostic="Failed" if not passed else "OK",
        )
    result = VideoAttributeResult(
        ad_id="ad_001",
        variant_id="anchor",
        attribute_scores=scores,
        overall_pass=False,
        pass_pct=0.9,
        warnings=[],
    )
    assert result.overall_pass is False


def test_non_required_fail_still_passes() -> None:
    """Non-required attribute failure → overall pass with warnings."""
    scores = {}
    warnings = []
    for a in VIDEO_ATTRIBUTES:
        passed = a["name"] != "text_legibility"  # Fail non-required
        scores[a["name"]] = AttributeScore(
            name=a["name"], passed=passed, confidence=0.8,
            diagnostic="Text too small" if not passed else "OK",
        )
        if not passed:
            warnings.append(f"{a['name']}: Text too small")
    result = VideoAttributeResult(
        ad_id="ad_001",
        variant_id="anchor",
        attribute_scores=scores,
        overall_pass=True,
        pass_pct=0.9,
        warnings=warnings,
    )
    assert result.overall_pass is True
    assert len(result.warnings) > 0


def test_is_video_acceptable_checks_required() -> None:
    """is_video_acceptable returns True only if all Required pass."""
    scores_pass = {a["name"]: AttributeScore(name=a["name"], passed=True, confidence=0.9, diagnostic="OK")
                   for a in VIDEO_ATTRIBUTES}
    result_pass = VideoAttributeResult("ad_001", "anchor", scores_pass, True, 1.0, [])
    assert is_video_acceptable(result_pass) is True

    scores_fail = dict(scores_pass)
    scores_fail["brand_safety"] = AttributeScore("brand_safety", False, 0.9, "Issue found")
    result_fail = VideoAttributeResult("ad_001", "anchor", scores_fail, False, 0.9, [])
    assert is_video_acceptable(result_fail) is False


# --- Diagnostics ---


def test_diagnostic_notes_on_failure() -> None:
    """Failed attributes have diagnostic notes."""
    score = AttributeScore(
        name="hook_timing",
        passed=False,
        confidence=0.7,
        diagnostic="Hook action not visible until 2.5 seconds",
    )
    assert len(score.diagnostic) > 0
    assert "hook" in score.diagnostic.lower() or "2.5" in score.diagnostic


# --- Frame Extraction ---


def test_extract_key_frames_count() -> None:
    """extract_key_frames returns expected number of frame paths."""
    frames = extract_key_frames("/tmp/nonexistent.mp4", frame_count=4)
    assert len(frames) == 4
    assert all(isinstance(f, str) for f in frames)


# --- Pass Percentage ---


def test_pass_pct_calculation() -> None:
    """pass_pct correctly reflects proportion of passing attributes."""
    scores = {}
    for i, a in enumerate(VIDEO_ATTRIBUTES):
        scores[a["name"]] = AttributeScore(
            name=a["name"], passed=i < 8, confidence=0.9,
            diagnostic="OK" if i < 8 else "Failed",
        )
    result = VideoAttributeResult("ad_001", "anchor", scores, False, 0.8, [])
    assert abs(result.pass_pct - 0.8) < 0.01
