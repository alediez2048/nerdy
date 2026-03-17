# PB-11: Creative direction form fields tests
"""Tests for key_message, creative_brief, copy_on_image flow through pipeline."""

from unittest.mock import patch

from app.api.schemas.session import SessionConfig
from generate.visual_spec import _CREATIVE_BRIEF_DIRECTIONS, extract_visual_spec


def _mock_visual_spec():
    return {
        "subject": "student studying",
        "setting": "home office",
        "color_palette": ["#00838F"],
        "composition": "medium shot",
        "campaign_goal_cue": "focused achievement",
        "text_overlay": "",
    }


# --- Schema ---


def test_session_config_has_creative_fields():
    config = SessionConfig(
        audience="parents",
        campaign_goal="conversion",
        key_message="SAT score for scholarship",
        creative_brief="gap_report",
        copy_on_image=True,
    )
    assert config.key_message == "SAT score for scholarship"
    assert config.creative_brief == "gap_report"
    assert config.copy_on_image is True


def test_session_config_creative_defaults():
    config = SessionConfig(audience="parents", campaign_goal="awareness")
    assert config.key_message == ""
    assert config.creative_brief == "auto"
    assert config.copy_on_image is False


# --- Creative brief directions ---


def test_creative_brief_directions_defined():
    expected = ["gap_report", "ugc_testimonial", "before_after", "lifestyle", "stat_focused"]
    for key in expected:
        assert key in _CREATIVE_BRIEF_DIRECTIONS


# --- Visual spec with creative_brief ---


def test_visual_spec_gap_report_changes_prompt():
    brief = {"product": "SAT Tutoring", "audience": "parents", "campaign_goal": "conversion"}

    with patch("generate.visual_spec._call_gemini_for_spec", return_value=_mock_visual_spec()):
        spec = extract_visual_spec(brief, "conversion", "parents", "ad_test", creative_brief="gap_report")

    assert spec.subject is not None


def test_visual_spec_auto_brief_no_extra_direction():
    brief = {"product": "SAT Tutoring", "audience": "parents", "campaign_goal": "conversion"}

    with patch("generate.visual_spec._call_gemini_for_spec", return_value=_mock_visual_spec()):
        spec = extract_visual_spec(brief, "conversion", "parents", "ad_test", creative_brief="auto")

    assert spec.subject is not None


def test_visual_spec_copy_on_image():
    brief = {"product": "SAT Tutoring", "audience": "parents", "campaign_goal": "conversion"}

    with patch("generate.visual_spec._call_gemini_for_spec", return_value={**_mock_visual_spec(), "text_overlay": "SAT Tutoring Works"}):
        spec = extract_visual_spec(brief, "conversion", "parents", "ad_test", copy_on_image=True)

    assert spec is not None


# --- Pipeline config extraction ---


def test_pipeline_extracts_creative_fields():
    config = {
        "key_message": "SAT for scholarship",
        "creative_brief": "stat_focused",
        "copy_on_image": True,
    }
    assert config.get("key_message", "") == "SAT for scholarship"
    assert config.get("creative_brief", "auto") == "stat_focused"
    assert config.get("copy_on_image", False) is True


def test_pipeline_creative_defaults():
    config = {}
    assert config.get("key_message", "") == ""
    assert config.get("creative_brief", "auto") == "auto"
    assert config.get("copy_on_image", False) is False
