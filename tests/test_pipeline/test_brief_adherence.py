"""Tests for brief adherence scorer (PD-12)."""

from __future__ import annotations

from unittest.mock import patch

from evaluate.brief_adherence import (
    ADHERENCE_DIMENSIONS,
    BriefAdherenceResult,
    _build_prompt,
    _build_result,
    _empty_result,
    score_brief_adherence,
)


SAMPLE_CONFIG = {
    "audience": "parents",
    "campaign_goal": "conversion",
    "persona": "Burned Returner",
    "key_message": "This time will be different — here's why",
    "creative_brief": "ugc_testimonial",
}

SAMPLE_COPY = {
    "headline": "Her SAT Score Jumped 360 Points",
    "primary_text": (
        "Is your child's SAT score not reflecting their true potential? "
        "This time will be different. Varsity Tutors provides personalized "
        "1-on-1 tutoring that meets your child exactly where they are."
    ),
    "description": "Expert SAT tutoring",
    "cta_button": "Get Started Today",
}

MOCK_RESPONSE_JSON = """{
  "audience_match": {"score": 9.0, "rationale": "Uses 'your child' language — clearly parent-facing"},
  "goal_alignment": {"score": 8.5, "rationale": "Strong CTA with 'Get Started Today' drives conversion"},
  "persona_fit": {"score": 7.0, "rationale": "Fresh-start tone with 'This time will be different' matches Burned Returner"},
  "message_delivery": {"score": 9.5, "rationale": "Key message literally present in primary text"},
  "format_adherence": {"score": 7.5, "rationale": "Partially testimonial style but could be more first-person"}
}"""


def test_build_prompt_includes_config_fields() -> None:
    """Prompt includes all session config fields."""
    prompt = _build_prompt(SAMPLE_COPY, SAMPLE_CONFIG)
    assert "parents" in prompt
    assert "conversion" in prompt
    assert "Burned Returner" in prompt
    assert "This time will be different" in prompt
    assert "ugc_testimonial" in prompt
    assert "Her SAT Score Jumped 360 Points" in prompt


def test_build_prompt_handles_missing_fields() -> None:
    """Prompt handles empty/missing config gracefully."""
    prompt = _build_prompt({}, {"audience": "auto"})
    assert "auto" in prompt
    assert "(none specified)" in prompt


def test_build_result_parses_valid_json() -> None:
    """_build_result extracts scores and rationales from valid JSON."""
    result = _build_result(MOCK_RESPONSE_JSON, 500, "ad_001")
    assert isinstance(result, BriefAdherenceResult)
    assert result.ad_id == "ad_001"
    assert result.scores["audience_match"] == 9.0
    assert result.scores["goal_alignment"] == 8.5
    assert result.scores["persona_fit"] == 7.0
    assert result.scores["message_delivery"] == 9.5
    assert result.scores["format_adherence"] == 7.5
    assert result.avg_score == 8.3
    assert "parent-facing" in result.rationales["audience_match"]
    assert result.tokens_consumed == 500


def test_build_result_handles_markdown_fences() -> None:
    """_build_result strips markdown code fences."""
    wrapped = f"```json\n{MOCK_RESPONSE_JSON}\n```"
    result = _build_result(wrapped, 100, "ad_002")
    assert result.scores["audience_match"] == 9.0


def test_build_result_handles_malformed_json() -> None:
    """_build_result returns empty result on bad JSON."""
    result = _build_result("not json at all", 100, "ad_003")
    assert result.avg_score == 0.0
    assert all(s == 0.0 for s in result.scores.values())


def test_empty_result() -> None:
    """_empty_result returns zeroed scores for all dimensions."""
    result = _empty_result("ad_err", 50)
    assert result.ad_id == "ad_err"
    assert result.avg_score == 0.0
    assert len(result.scores) == len(ADHERENCE_DIMENSIONS)
    assert all(s == 0.0 for s in result.scores.values())
    assert result.tokens_consumed == 50


def test_all_dimensions_present() -> None:
    """ADHERENCE_DIMENSIONS has exactly 5 entries."""
    assert len(ADHERENCE_DIMENSIONS) == 5
    assert "audience_match" in ADHERENCE_DIMENSIONS
    assert "goal_alignment" in ADHERENCE_DIMENSIONS
    assert "persona_fit" in ADHERENCE_DIMENSIONS
    assert "message_delivery" in ADHERENCE_DIMENSIONS
    assert "format_adherence" in ADHERENCE_DIMENSIONS


def test_score_brief_adherence_text_only() -> None:
    """score_brief_adherence calls Gemini text API for copy-only ads."""
    from generate.gemini_client import GeminiResponse

    mock_resp = GeminiResponse(
        text=MOCK_RESPONSE_JSON,
        total_tokens=500,
        prompt_tokens=400,
        completion_tokens=100,
        model="gemini-2.0-flash",
    )

    with patch("generate.gemini_client.call_gemini", return_value=mock_resp) as mock_call:
        result = score_brief_adherence(
            ad_copy=SAMPLE_COPY,
            session_config=SAMPLE_CONFIG,
            ad_id="ad_text_001",
        )

    assert mock_call.called
    assert result.ad_id == "ad_text_001"
    assert result.scores["audience_match"] == 9.0
    assert result.avg_score == 8.3


def test_score_brief_adherence_with_nonexistent_image() -> None:
    """Falls back to text-only when image path doesn't exist."""
    from generate.gemini_client import GeminiResponse

    mock_resp = GeminiResponse(
        text=MOCK_RESPONSE_JSON,
        total_tokens=500,
        prompt_tokens=400,
        completion_tokens=100,
        model="gemini-2.0-flash",
    )

    with patch("generate.gemini_client.call_gemini", return_value=mock_resp):
        result = score_brief_adherence(
            ad_copy=SAMPLE_COPY,
            session_config=SAMPLE_CONFIG,
            ad_id="ad_noimg",
            image_path="/nonexistent/image.png",
        )

    assert result.scores["audience_match"] == 9.0


def test_build_result_handles_flat_scores() -> None:
    """_build_result handles responses where scores are flat numbers, not dicts."""
    flat_json = """{
      "audience_match": 8.0,
      "goal_alignment": 7.0,
      "persona_fit": 6.0,
      "message_delivery": 9.0,
      "format_adherence": 7.0
    }"""
    result = _build_result(flat_json, 100, "ad_flat")
    assert result.scores["audience_match"] == 8.0
    assert result.avg_score == 7.4
    assert result.rationales["audience_match"] == ""
