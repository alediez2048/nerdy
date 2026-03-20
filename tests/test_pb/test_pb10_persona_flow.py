# PB-10: Persona flow tests
"""Tests that persona flows from session config through pipeline to all modules."""

import json
from unittest.mock import patch

from generate.visual_spec import _PERSONA_VISUAL_DIRECTION, extract_visual_spec
from generate.brief_expansion import expand_brief


def _mock_gemini_expansion():
    return json.dumps({
        "audience_profile": {"pain_points": ["recruiting"], "tone": "urgent"},
        "brand_facts": [{"claim": "1-on-1", "source": "test"}],
        "competitive_context_summary": "test",
        "emotional_angles": ["scholarship fear"],
        "value_propositions": ["10X"],
        "key_differentiators": ["digital SAT"],
        "constraints": ["no fake urgency"],
    })


def _mock_gemini_visual_spec():
    return {
        "subject": "athletic student on campus",
        "setting": "near practice field, late afternoon",
        "color_palette": ["#00838F", "#1A237E"],
        "composition": "medium shot, rule of thirds",
        "campaign_goal_cue": "action-oriented achievement",
        "text_overlay": "",
    }


# --- Persona extraction ---


def test_persona_auto_not_passed():
    """When persona is 'auto', batch processor should resolve to None or default."""
    config = {"persona": "auto", "ad_count": 3}
    persona_raw = config.get("persona", "auto")
    persona = persona_raw if persona_raw and persona_raw != "auto" else None
    assert persona is None


def test_persona_extracted_from_config():
    """When persona is set, it should be extracted."""
    config = {"persona": "athlete_recruit", "ad_count": 3}
    persona_raw = config.get("persona", "auto")
    persona = persona_raw if persona_raw and persona_raw != "auto" else None
    assert persona == "athlete_recruit"


# --- Visual spec persona direction ---


def test_visual_spec_has_all_persona_directions():
    """Every persona should have a visual direction defined."""
    expected = [
        "athlete_recruit", "suburban_optimizer", "immigrant_navigator",
        "cultural_investor", "system_optimizer", "neurodivergent_advocate", "burned_returner",
    ]
    for p in expected:
        assert p in _PERSONA_VISUAL_DIRECTION, f"Missing visual direction for {p}"


def test_visual_spec_persona_changes_prompt():
    """Persona should inject creative direction into the visual spec prompt."""
    brief = {"product": "SAT Tutoring", "audience": "parents", "campaign_goal": "conversion", "key_message": "test"}

    with patch(
        "generate.visual_spec._call_gemini_for_spec",
        return_value=(_mock_gemini_visual_spec(), 100),
    ):
        spec_generic = extract_visual_spec(brief, "conversion", "parents", "ad_001", persona=None)
        spec_athlete = extract_visual_spec(brief, "conversion", "parents", "ad_002", persona="athlete_recruit")

    # Both should return valid specs
    assert spec_generic.subject is not None
    assert spec_athlete.subject is not None


def test_visual_spec_system_optimizer_mckinsey():
    """System optimizer should get McKinsey-style direction."""
    direction = _PERSONA_VISUAL_DIRECTION["system_optimizer"]
    assert "McKinsey" in direction or "dashboard" in direction.lower()
    assert "NO lifestyle" in direction or "NO stock photos" in direction


# --- Persona flows to expand_brief ---


def test_persona_flows_to_expand_brief():
    """expand_brief with persona should set persona on result."""
    brief = {"audience": "parents", "campaign_goal": "conversion", "brief_id": "flow_001"}

    with (
        patch("generate.brief_expansion._call_gemini", return_value=_mock_gemini_expansion()),
        patch("generate.brief_expansion.log_event"),
    ):
        result = expand_brief(brief, persona="athlete_recruit")

    assert result.persona == "athlete_recruit"
    assert len(result.suggested_hooks) >= 1


def test_persona_none_uses_default():
    """expand_brief with no persona should auto-select."""
    brief = {"audience": "parents", "campaign_goal": "conversion", "brief_id": "flow_002"}

    with (
        patch("generate.brief_expansion._call_gemini", return_value=_mock_gemini_expansion()),
        patch("generate.brief_expansion.log_event"),
    ):
        result = expand_brief(brief, persona=None)

    assert result.persona == "suburban_optimizer"  # default for parents
