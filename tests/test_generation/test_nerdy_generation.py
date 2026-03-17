# PB-05: Nerdy generation rules tests
"""Tests for Nerdy language enforcement, expanded CTAs, persona voice, and Meta ad structure."""

import json

from generate.ad_generator import VALID_CTAS, _build_generation_prompt, _parse_generation_response
from generate.brand_voice import get_voice_for_persona
from generate.brief_expansion import ExpandedBrief


def _make_brief(persona="athlete_recruit", campaign_goal="conversion"):
    """Create a test ExpandedBrief with PB-04 fields."""
    return ExpandedBrief(
        original_brief={"audience": "parents", "campaign_goal": campaign_goal, "brief_id": "test_001"},
        audience_profile={"pain_points": ["SAT anxiety"], "tone": "reassuring"},
        brand_facts=[{"claim": "1-on-1 SAT tutoring", "source": "supplementary"}],
        competitive_context="VT offers 1:1 vs group classes",
        emotional_angles=["scholarship fear", "recruiting urgency"],
        value_propositions=["10X vs self-study"],
        key_differentiators=["digital SAT interface"],
        constraints=["no fake urgency"],
        persona=persona,
        suggested_hooks=[
            {"hook_text": "The coach wants him. The admissions office needs an SAT score.", "hook_id": "h1", "cta_text": "Talk to an SAT specialist today."},
            {"hook_text": "Recruiting windows don't care about SAT score excuses.", "hook_id": "h2", "cta_text": "Talk to an SAT specialist today."},
        ],
        offer_context={"model": "Monthly membership", "score_improvement": "~100 points/month"} if campaign_goal == "conversion" else None,
        messaging_rules={"dos": [{"rule": "your child"}], "donts": [{"rule": "your student"}]},
    )


# --- VALID_CTAS expanded ---


def test_valid_ctas_includes_persona_options():
    assert "Book Diagnostic" in VALID_CTAS
    assert "Talk to an SAT specialist today" in VALID_CTAS
    assert "Tell us about your child" in VALID_CTAS
    assert "Tell us what went wrong" in VALID_CTAS
    assert "See what score range is realistic in 8–10 weeks" in VALID_CTAS
    # Original still present
    assert "Learn More" in VALID_CTAS
    assert "Sign Up" in VALID_CTAS


def test_valid_ctas_count():
    assert len(VALID_CTAS) >= 16


# --- Generation prompt includes Nerdy rules ---


def test_prompt_includes_nerdy_language_rules():
    brief = _make_brief()
    prompt = _build_generation_prompt(brief, [])
    assert "your child" in prompt.lower()
    assert "your student" in prompt.lower()  # mentioned in the "NEVER" rule
    assert "SAT Tutoring" in prompt
    assert "SAT Prep" in prompt  # mentioned in the "NEVER" rule
    assert "fake urgency" in prompt.lower() or "spots filling fast" in prompt.lower()


def test_prompt_includes_meta_ad_structure():
    brief = _make_brief()
    prompt = _build_generation_prompt(brief, [])
    assert "Hook" in prompt
    assert "pattern interrupt" in prompt.lower()
    assert "Micro-commitment CTA" in prompt or "CTA" in prompt


def test_prompt_includes_persona_hooks():
    brief = _make_brief()
    prompt = _build_generation_prompt(brief, [])
    assert "The coach wants him" in prompt
    assert "Recruiting windows" in prompt


def test_prompt_includes_offer_for_conversion():
    brief = _make_brief(campaign_goal="conversion")
    prompt = _build_generation_prompt(brief, [])
    assert "membership" in prompt.lower()
    assert "100 points" in prompt


def test_prompt_no_offer_for_awareness():
    brief = _make_brief(campaign_goal="awareness")
    prompt = _build_generation_prompt(brief, [])
    assert "Offer Context" not in prompt


def test_prompt_includes_conditional_claim_instruction():
    brief = _make_brief()
    prompt = _build_generation_prompt(brief, [])
    assert "condition" in prompt.lower() or "16 sessions" in prompt.lower() or "MUST have conditions" in prompt


# --- Persona voice ---


def test_persona_voice_athlete():
    voice = get_voice_for_persona("athlete_recruit")
    assert "recruiting" in voice.lower() or "scholarship" in voice.lower()
    assert "your child" in voice.lower()
    assert "your student" in voice.lower()  # in the NEVER rule


def test_persona_voice_system_optimizer():
    voice = get_voice_for_persona("system_optimizer")
    assert "data-driven" in voice.lower() or "process" in voice.lower()


def test_persona_voice_neurodivergent():
    voice = get_voice_for_persona("neurodivergent_advocate")
    assert "warm" in voice.lower() or "accommodation" in voice.lower()
    assert "broken" in voice.lower()  # in avoid list


def test_persona_voice_unknown_falls_back():
    voice = get_voice_for_persona("nonexistent_persona")
    assert "Brand Voice" in voice or "brand" in voice.lower()


# --- CTA validation ---


def test_parse_accepts_persona_cta():
    response = json.dumps({
        "primary_text": "Your child can raise their score.",
        "headline": "SAT Tutoring That Works",
        "description": "1-on-1 expert tutoring",
        "cta_button": "Book Diagnostic",
    })
    ad = _parse_generation_response(response, "ad_test", [], "brief_test", {})
    assert ad.cta_button == "Book Diagnostic"


def test_parse_accepts_original_cta():
    response = json.dumps({
        "primary_text": "text",
        "headline": "headline",
        "description": "desc",
        "cta_button": "Learn More",
    })
    ad = _parse_generation_response(response, "ad_test2", [], "brief_test", {})
    assert ad.cta_button == "Learn More"


def test_parse_fallback_for_invalid_cta():
    response = json.dumps({
        "primary_text": "text",
        "headline": "headline",
        "description": "desc",
        "cta_button": "Click Here Now!!!",
    })
    ad = _parse_generation_response(response, "ad_test3", [], "brief_test", {})
    assert ad.cta_button == "Learn More"  # fallback
