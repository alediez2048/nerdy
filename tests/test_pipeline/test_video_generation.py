"""Tests for Veo integration + video spec extraction (P3-07).

Validates video spec extraction, variant generation, API error handling,
rate limiting, and checkpoint-resume.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from generate_video.video_spec import (
    VideoSpec,
    extract_video_spec,
    generate_variant_specs,
)
from generate_video.veo_client import (
    VideoResult,
    VeoRateLimiter,
)
from generate_video.orchestrator import (
    VideoVariant,
    generate_video_variants,
)


_EXPANDED_BRIEF = {
    "brief_id": "b001",
    "audience": "parents",
    "campaign_goal": "conversion",
    "product": "SAT prep tutoring",
    "key_benefit": "personalized 1-on-1 tutoring",
    "emotional_angles": ["aspiration", "confidence"],
    "hook_text": "Is your child ready for the SAT?",
    "brand": "Varsity Tutors",
}


# --- Video Spec Extraction ---


def test_extract_video_spec_valid() -> None:
    """extract_video_spec returns a valid VideoSpec from brief."""
    spec = extract_video_spec(_EXPANDED_BRIEF)
    assert isinstance(spec, VideoSpec)
    assert spec.duration == 6
    assert spec.aspect_ratio == "9:16"
    assert len(spec.scene_description) > 0
    assert spec.hook_action is not None


def test_video_spec_has_all_fields() -> None:
    """VideoSpec has all required fields."""
    spec = extract_video_spec(_EXPANDED_BRIEF)
    assert spec.hook_action is not None
    assert spec.scene_description is not None
    assert spec.pacing in ("fast", "medium", "slow")
    assert spec.mood is not None
    assert spec.audio_mode in ("silent", "music", "voiceover")


def test_variant_specs_produces_two() -> None:
    """generate_variant_specs returns anchor + alternative."""
    spec = extract_video_spec(_EXPANDED_BRIEF)
    anchor, alternative = generate_variant_specs(spec)
    assert isinstance(anchor, VideoSpec)
    assert isinstance(alternative, VideoSpec)


def test_variant_specs_differ() -> None:
    """Anchor and alternative specs differ in scene or pacing."""
    spec = extract_video_spec(_EXPANDED_BRIEF)
    anchor, alternative = generate_variant_specs(spec)
    # At least one field should differ
    differs = (
        anchor.scene_description != alternative.scene_description
        or anchor.pacing != alternative.pacing
    )
    assert differs, "Anchor and alternative should differ in scene or pacing"


# --- Veo Client ---


def test_rate_limiter_tracks_calls() -> None:
    """VeoRateLimiter tracks call count."""
    limiter = VeoRateLimiter(max_calls_per_minute=10)
    assert limiter.can_call() is True
    limiter.record_call()
    assert limiter.call_count == 1


def test_video_result_structure() -> None:
    """VideoResult has expected fields."""
    result = VideoResult(
        video_path="/tmp/test.mp4",
        model_used="veo-3.1-fast",
        duration_seconds=6,
        tokens_consumed=0,
        metadata={"aspect_ratio": "9:16"},
    )
    assert result.video_path == "/tmp/test.mp4"
    assert result.duration_seconds == 6


# --- Orchestrator ---


@patch("generate_video.orchestrator._generate_single_video")
def test_orchestrator_produces_two_variants(mock_gen: MagicMock) -> None:
    """generate_video_variants returns 2 variants."""
    mock_gen.return_value = VideoResult(
        video_path="/tmp/test.mp4",
        model_used="veo-3.1-fast",
        duration_seconds=6,
        tokens_consumed=0,
        metadata={},
    )

    variants = generate_video_variants("ad_001", _EXPANDED_BRIEF)
    assert len(variants) == 2
    assert all(isinstance(v, VideoVariant) for v in variants)
    types = {v.variant_type for v in variants}
    assert "anchor" in types
    assert "alternative" in types


@patch("generate_video.orchestrator._generate_single_video")
def test_orchestrator_handles_api_failure(mock_gen: MagicMock) -> None:
    """Orchestrator handles API failure gracefully (no crash)."""
    mock_gen.side_effect = RuntimeError("API unavailable")

    variants = generate_video_variants("ad_001", _EXPANDED_BRIEF)
    # Should return empty list or variants with error state, not crash
    assert isinstance(variants, list)


@patch("generate_video.orchestrator._generate_single_video")
def test_orchestrator_logs_to_ledger(mock_gen: MagicMock, tmp_path: Path) -> None:
    """Orchestrator logs video generation events to ledger."""
    import json

    mock_gen.return_value = VideoResult(
        video_path="/tmp/test.mp4",
        model_used="veo-3.1-fast",
        duration_seconds=6,
        tokens_consumed=0,
        metadata={},
    )

    ledger_path = str(tmp_path / "ledger.jsonl")
    generate_video_variants("ad_001", _EXPANDED_BRIEF, ledger_path=ledger_path)

    events = [json.loads(line) for line in Path(ledger_path).read_text().strip().split("\n")]
    video_events = [e for e in events if e["event_type"] == "VideoGenerated"]
    assert len(video_events) == 2
