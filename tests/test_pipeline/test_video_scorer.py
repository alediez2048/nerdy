"""Tests for video quality scorer (PD-14)."""

from __future__ import annotations

from pathlib import Path

from evaluate.video_scorer import (
    VIDEO_DIMENSIONS,
    VideoScoreResult,
    _build_prompt,
    _build_result,
    _empty_result,
    score_video,
)


SAMPLE_COPY = {
    "headline": "Her SAT Score Jumped 360 Points",
    "primary_text": "Expert 1-on-1 tutoring that meets your child where they are.",
    "cta_button": "Get Started Today",
}

SAMPLE_CONFIG = {
    "audience": "parents",
    "persona": "Burned Returner",
}

MOCK_RESPONSE_JSON = """{
  "hook_strength": {"score": 7.5, "rationale": "Opens with student celebrating — immediate emotional hook"},
  "visual_quality": {"score": 8.0, "rationale": "Smooth motion, natural lighting, no artifacts"},
  "narrative_flow": {"score": 6.5, "rationale": "Clear start but ending feels abrupt"},
  "copy_video_coherence": {"score": 7.0, "rationale": "Student studying matches tutoring message"},
  "ugc_authenticity": {"score": 6.0, "rationale": "Looks somewhat generated — motion is too smooth for real UGC"}
}"""


def test_build_prompt_includes_brand_and_platform_context() -> None:
    """Prompt includes Varsity Tutors brand and platform context."""
    prompt = _build_prompt(SAMPLE_COPY, SAMPLE_CONFIG)
    assert "Varsity Tutors" in prompt
    assert "Facebook/Instagram" in prompt
    assert "4-10 seconds" in prompt
    assert "parents" in prompt
    assert "Burned Returner" in prompt
    assert "Her SAT Score Jumped 360 Points" in prompt


def test_build_prompt_handles_no_config() -> None:
    """Prompt works without session config."""
    prompt = _build_prompt(SAMPLE_COPY, None)
    assert "hook_strength" in prompt
    assert "Target audience" not in prompt


def test_build_result_parses_valid_json() -> None:
    """_build_result extracts scores and rationales."""
    result = _build_result(MOCK_RESPONSE_JSON, 800, "ad_001", "output/videos/test.mp4")
    assert isinstance(result, VideoScoreResult)
    assert result.ad_id == "ad_001"
    assert result.video_path == "output/videos/test.mp4"
    assert result.scores["hook_strength"] == 7.5
    assert result.scores["visual_quality"] == 8.0
    assert result.scores["narrative_flow"] == 6.5
    assert result.scores["copy_video_coherence"] == 7.0
    assert result.scores["ugc_authenticity"] == 6.0
    assert result.avg_score == 7.0
    assert "celebrating" in result.rationales["hook_strength"]
    assert result.tokens_consumed == 800


def test_build_result_handles_markdown_fences() -> None:
    """_build_result strips markdown code fences."""
    wrapped = f"```json\n{MOCK_RESPONSE_JSON}\n```"
    result = _build_result(wrapped, 100, "ad_002", "vid.mp4")
    assert result.scores["hook_strength"] == 7.5


def test_build_result_handles_malformed_json() -> None:
    """_build_result returns empty result on bad JSON."""
    result = _build_result("garbage", 100, "ad_003", "vid.mp4")
    assert result.avg_score == 0.0
    assert all(s == 0.0 for s in result.scores.values())


def test_build_result_handles_flat_scores() -> None:
    """_build_result handles flat number scores."""
    flat = '{"hook_strength": 7, "visual_quality": 8, "narrative_flow": 6, "copy_video_coherence": 7, "ugc_authenticity": 5}'
    result = _build_result(flat, 100, "ad_flat", "vid.mp4")
    assert result.scores["hook_strength"] == 7.0
    assert result.avg_score == 6.6


def test_empty_result() -> None:
    """_empty_result returns zeroed scores."""
    result = _empty_result("ad_err", "vid.mp4", 50)
    assert result.ad_id == "ad_err"
    assert result.video_path == "vid.mp4"
    assert result.avg_score == 0.0
    assert len(result.scores) == 5
    assert result.tokens_consumed == 50


def test_all_dimensions_present() -> None:
    """VIDEO_DIMENSIONS has exactly 5 entries."""
    assert len(VIDEO_DIMENSIONS) == 5
    assert "hook_strength" in VIDEO_DIMENSIONS
    assert "visual_quality" in VIDEO_DIMENSIONS
    assert "narrative_flow" in VIDEO_DIMENSIONS
    assert "copy_video_coherence" in VIDEO_DIMENSIONS
    assert "ugc_authenticity" in VIDEO_DIMENSIONS


def test_score_video_missing_file() -> None:
    """score_video returns empty result when file doesn't exist."""
    result = score_video(
        video_path="/nonexistent/video.mp4",
        ad_copy=SAMPLE_COPY,
        ad_id="ad_missing",
    )
    assert result.avg_score == 0.0
    assert result.ad_id == "ad_missing"
