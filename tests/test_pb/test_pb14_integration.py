# PB-14: Full integration tests — persona flow end-to-end
"""Tests that the full PB-10 through PB-13 extension works together."""

import json
from unittest.mock import patch

from app.api.schemas.session import Persona, SessionConfig
from evaluate.evaluator import _apply_nerdy_adjustments
from generate.ad_generator import (
    VALID_CTAS,
    _build_generation_prompt,
)
from generate.brief_expansion import ExpandedBrief, expand_brief
from generate.compliance import check_compliance
from generate.visual_spec import (
    _CREATIVE_BRIEF_DIRECTIONS,
    _PERSONA_VISUAL_DIRECTION,
    extract_visual_spec,
)


def _mock_expansion():
    return (json.dumps({
        "audience_profile": {"pain_points": ["test"], "tone": "urgent"},
        "brand_facts": [{"claim": "1-on-1", "source": "test"}],
        "competitive_context_summary": "VT vs competitors",
        "emotional_angles": ["scholarship fear", "recruiting urgency"],
        "value_propositions": ["10X vs self-study", "100pts/month"],
        "key_differentiators": ["digital SAT"],
        "constraints": ["no fake urgency"],
    }), 100)


def _mock_visual():
    return {
        "subject": "athletic student",
        "setting": "campus field",
        "color_palette": ["#00838F"],
        "composition": "medium shot",
        "campaign_goal_cue": "achievement",
        "text_overlay": "",
    }


# --- Persona produces persona-specific content ---


def test_athlete_brief_has_persona_context():
    brief = {"audience": "parents", "campaign_goal": "conversion", "brief_id": "int_001"}
    with (
        patch("generate.brief_expansion._call_gemini", return_value=_mock_expansion()),
        patch("generate.brief_expansion.log_event"),
    ):
        result = expand_brief(brief, persona="athlete_recruit")
    assert result.persona == "athlete_recruit"
    assert len(result.suggested_hooks) >= 1
    assert any("coach" in h.get("hook_text", "").lower() or "recruit" in h.get("hook_text", "").lower()
               for h in result.suggested_hooks)


def test_suburban_optimizer_brief_has_gpa_context():
    brief = {"audience": "parents", "campaign_goal": "conversion", "brief_id": "int_002"}
    with (
        patch("generate.brief_expansion._call_gemini", return_value=_mock_expansion()),
        patch("generate.brief_expansion.log_event"),
    ):
        result = expand_brief(brief, persona="suburban_optimizer")
    assert result.persona == "suburban_optimizer"
    # Suburban optimizer should have hooks (persona has 30+ across categories)
    assert len(result.suggested_hooks) >= 1
    # Hooks should be for this persona
    assert all(h.get("persona") == "suburban_optimizer" for h in result.suggested_hooks)


def test_system_optimizer_visual_is_data_driven():
    direction = _PERSONA_VISUAL_DIRECTION["system_optimizer"]
    assert "McKinsey" in direction or "dashboard" in direction.lower()
    assert "NO lifestyle" in direction or "NO stock" in direction


# --- Creative brief presets ---


def test_gap_report_creative_brief():
    assert "gap_report" in _CREATIVE_BRIEF_DIRECTIONS
    assert "McKinsey" in _CREATIVE_BRIEF_DIRECTIONS["gap_report"] or "dashboard" in _CREATIVE_BRIEF_DIRECTIONS["gap_report"].lower()


def test_creative_brief_flows_to_visual_spec():
    brief = {"product": "SAT Tutoring", "audience": "parents", "campaign_goal": "conversion"}
    with patch("generate.visual_spec._call_gemini_for_spec", return_value=(_mock_visual(), 100)):
        spec = extract_visual_spec(brief, "conversion", "parents", "ad_int", creative_brief="stat_focused")
    assert spec is not None


# --- Copy on image ---


def test_copy_on_image_accepted_in_config():
    config = SessionConfig(audience="parents", campaign_goal="conversion", copy_on_image=True)
    assert config.copy_on_image is True


# --- Nerdy compliance across generated ads ---


def test_clean_nerdy_ad_passes_compliance():
    ad_text = (
        "3.8 GPA. 1260 SAT. Something's off.\n"
        "Your child is 3-4 targeted fixes away from a 1400+. "
        "Our 1:1 SAT tutoring diagnoses exactly where points are hiding. "
        "100 points per month at 2 sessions per week.\n"
        "See what score is realistic in 8-10 weeks."
    )
    result = check_compliance(ad_text)
    assert result.passes
    assert len(result.critical_violations) == 0


def test_bad_nerdy_ad_caught():
    ad_text = "Help your student with SAT Prep! Spots filling fast. Unlock their potential!"
    result = check_compliance(ad_text)
    assert not result.passes
    rules = {v.rule_name for v in result.critical_violations}
    assert "nerdy_wrong_address" in rules
    assert "nerdy_wrong_product" in rules
    assert "fake_urgency" in rules


# --- Conversion ads reference offer data ---


def test_conversion_prompt_has_offer():
    brief = ExpandedBrief(
        original_brief={"audience": "parents", "campaign_goal": "conversion", "brief_id": "t"},
        audience_profile={}, brand_facts=[], competitive_context="",
        emotional_angles=["fear"], value_propositions=["10X"],
        key_differentiators=["digital"], constraints=[],
        persona="athlete_recruit",
        suggested_hooks=[{"hook_text": "Coach wants him", "hook_id": "h1", "cta_text": "Call now"}],
        offer_context={"model": "Monthly membership", "score_improvement": "~100pts/month"},
        messaging_rules=None,
    )
    prompt = _build_generation_prompt(brief, [])
    assert "membership" in prompt.lower() or "100" in prompt


# --- Persona CTA in generated ads ---


def test_persona_cta_in_valid_set():
    for cta in ["Book Diagnostic", "Talk to an SAT specialist today", "Tell us about your child"]:
        assert cta in VALID_CTAS


# --- Auto persona backward compatibility ---


def test_auto_persona_uses_default():
    brief = {"audience": "parents", "campaign_goal": "awareness", "brief_id": "int_auto"}
    with (
        patch("generate.brief_expansion._call_gemini", return_value=_mock_expansion()),
        patch("generate.brief_expansion.log_event"),
    ):
        result = expand_brief(brief, persona=None)
    assert result.persona == "suburban_optimizer"  # default for parents


def test_auto_persona_config():
    config = SessionConfig(audience="parents", campaign_goal="awareness")
    assert config.persona == Persona.auto


# --- Evaluator rewards Nerdy-compliant ads ---


def test_evaluator_rewards_compliant_ad():
    scores = {d: {"score": 7.0, "rationale": "test", "confidence": 8}
              for d in ["brand_voice", "clarity", "value_proposition", "cta", "emotional_resonance"]}
    ad = {
        "primary_text": "3.8 GPA. 1260 SAT.\nYour child is 3-4 fixes away from a 1400+. Our diagnostic finds where scholarship points are hiding. 100 points per month at 2 sessions per week.",
        "headline": "SAT Tutoring That Works",
        "description": "1:1 expert matched to your child",
    }
    adjusted = _apply_nerdy_adjustments(scores, ad, persona="athlete_recruit")
    # Should get bonuses: your_child (+0.3 BV), meta structure (+0.3 CL), conditional claim (+0.5 VP), persona match (+0.7 ER)
    assert adjusted["brand_voice"]["score"] >= 7.3
    assert adjusted["clarity"]["score"] >= 7.3
    assert adjusted["value_proposition"]["score"] >= 7.5
    assert adjusted["emotional_resonance"]["score"] >= 7.4  # at least partial match
