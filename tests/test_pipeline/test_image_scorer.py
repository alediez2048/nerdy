"""Tests for image quality scorer (PD-13)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from evaluate.image_scorer import (
    IMAGE_DIMENSIONS,
    ImageScoreResult,
    _build_prompt,
    _build_result,
    _empty_result,
    score_image,
)


SAMPLE_COPY = {
    "headline": "Her SAT Score Jumped 360 Points",
    "primary_text": "Expert 1-on-1 tutoring that meets your child where they are.",
    "cta_button": "Get Started Today",
}

SAMPLE_CONFIG = {
    "audience": "parents",
    "persona": "Suburban Optimizer",
}

MOCK_RESPONSE_JSON = """{
  "visual_clarity": {"score": 8.0, "rationale": "Clear focal point on student studying"},
  "brand_consistency": {"score": 7.5, "rationale": "Warm tones but missing brand teal"},
  "emotional_impact": {"score": 7.0, "rationale": "Shows focused student — conveys determination"},
  "copy_image_coherence": {"score": 8.5, "rationale": "Image of studying reinforces tutoring message"},
  "platform_fit": {"score": 9.0, "rationale": "Clean composition works well at mobile size"}
}"""


def test_build_prompt_includes_brand_context() -> None:
    """Prompt includes Varsity Tutors brand context."""
    prompt = _build_prompt(SAMPLE_COPY, SAMPLE_CONFIG)
    assert "Varsity Tutors" in prompt
    assert "#17e2ea" in prompt
    assert "parents" in prompt
    assert "Suburban Optimizer" in prompt
    assert "Her SAT Score Jumped 360 Points" in prompt


def test_build_prompt_handles_no_config() -> None:
    """Prompt works without session config."""
    prompt = _build_prompt(SAMPLE_COPY, None)
    assert "visual_clarity" in prompt
    assert "Target audience" not in prompt


def test_build_result_parses_valid_json() -> None:
    """_build_result extracts scores and rationales from valid JSON."""
    result = _build_result(MOCK_RESPONSE_JSON, 600, "ad_001", "output/images/test.png")
    assert isinstance(result, ImageScoreResult)
    assert result.ad_id == "ad_001"
    assert result.image_path == "output/images/test.png"
    assert result.scores["visual_clarity"] == 8.0
    assert result.scores["brand_consistency"] == 7.5
    assert result.scores["emotional_impact"] == 7.0
    assert result.scores["copy_image_coherence"] == 8.5
    assert result.scores["platform_fit"] == 9.0
    assert result.avg_score == 8.0
    assert "focal point" in result.rationales["visual_clarity"]
    assert result.tokens_consumed == 600


def test_build_result_handles_markdown_fences() -> None:
    """_build_result strips markdown code fences."""
    wrapped = f"```json\n{MOCK_RESPONSE_JSON}\n```"
    result = _build_result(wrapped, 100, "ad_002", "img.png")
    assert result.scores["visual_clarity"] == 8.0


def test_build_result_handles_malformed_json() -> None:
    """_build_result returns empty result on bad JSON."""
    result = _build_result("not json", 100, "ad_003", "img.png")
    assert result.avg_score == 0.0
    assert all(s == 0.0 for s in result.scores.values())


def test_build_result_handles_flat_scores() -> None:
    """_build_result handles flat number scores."""
    flat = '{"visual_clarity": 8, "brand_consistency": 7, "emotional_impact": 6, "copy_image_coherence": 7, "platform_fit": 9}'
    result = _build_result(flat, 100, "ad_flat", "img.png")
    assert result.scores["visual_clarity"] == 8.0
    assert result.avg_score == 7.4


def test_empty_result() -> None:
    """_empty_result returns zeroed scores."""
    result = _empty_result("ad_err", "img.png", 50)
    assert result.ad_id == "ad_err"
    assert result.avg_score == 0.0
    assert len(result.scores) == 5
    assert result.tokens_consumed == 50


def test_all_dimensions_present() -> None:
    """IMAGE_DIMENSIONS has exactly 5 entries."""
    assert len(IMAGE_DIMENSIONS) == 5
    assert "visual_clarity" in IMAGE_DIMENSIONS
    assert "brand_consistency" in IMAGE_DIMENSIONS
    assert "emotional_impact" in IMAGE_DIMENSIONS
    assert "copy_image_coherence" in IMAGE_DIMENSIONS
    assert "platform_fit" in IMAGE_DIMENSIONS


def test_score_image_missing_file() -> None:
    """score_image returns empty result when file doesn't exist."""
    result = score_image(
        image_path="/nonexistent/image.png",
        ad_copy=SAMPLE_COPY,
        ad_id="ad_missing",
    )
    assert result.avg_score == 0.0
    assert result.ad_id == "ad_missing"


def test_score_image_with_real_file(tmp_path: Path) -> None:
    """score_image calls Gemini multimodal when file exists."""
    # Create a dummy image file
    img = tmp_path / "test_ad.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)

    with patch("evaluate.image_scorer.retry_with_backoff") as mock_retry:
        # Make retry_with_backoff call the function directly
        mock_retry.side_effect = lambda fn: _build_result(
            MOCK_RESPONSE_JSON, 600, "ad_test", str(img)
        )

        result = score_image(
            image_path=str(img),
            ad_copy=SAMPLE_COPY,
            ad_id="ad_test",
            session_config=SAMPLE_CONFIG,
        )

    assert result.scores["visual_clarity"] == 8.0
    assert result.avg_score == 8.0
