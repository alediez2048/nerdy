# PB-12: Nerdy messaging rules in ad generator tests
"""Tests for compliance pre-check, persona CTA preference, and offer context in generation."""

import json

from generate.ad_generator import (
    VALID_CTAS,
    GeneratedAd,
    _build_generation_prompt,
    _compliance_pre_check,
    _parse_generation_response,
)
from generate.brief_expansion import ExpandedBrief


def _make_brief(persona="athlete_recruit", campaign_goal="conversion"):
    return ExpandedBrief(
        original_brief={"audience": "parents", "campaign_goal": campaign_goal, "brief_id": "test"},
        audience_profile={},
        brand_facts=[],
        competitive_context="",
        emotional_angles=["scholarship fear"],
        value_propositions=["10X"],
        key_differentiators=["digital SAT"],
        constraints=[],
        persona=persona,
        suggested_hooks=[
            {"hook_text": "The coach wants him.", "hook_id": "h1", "cta_text": "Talk to an SAT specialist today."},
        ],
        offer_context={"model": "Monthly membership", "score_improvement": "~100pts/month"} if campaign_goal == "conversion" else None,
        messaging_rules={"dos": [{"rule": "your child"}], "donts": [{"rule": "your student"}]},
    )


# --- Compliance pre-check ---


def test_compliance_precheck_clean_ad():
    ad = GeneratedAd(
        ad_id="test_clean",
        primary_text="Your child can raise their SAT score with 1-on-1 tutoring.",
        headline="SAT Tutoring That Works",
        description="Expert tutors matched to your child",
        cta_button="Book Diagnostic",
    )
    violations = _compliance_pre_check(ad)
    assert len(violations) == 0


def test_compliance_precheck_catches_your_student():
    ad = GeneratedAd(
        ad_id="test_bad",
        primary_text="Help your student with SAT prep.",
        headline="SAT Prep for Students",
        description="Enroll now",
        cta_button="Learn More",
    )
    violations = _compliance_pre_check(ad)
    assert len(violations) >= 1
    assert any("nerdy_wrong_address" in v for v in violations)


def test_compliance_precheck_catches_fake_urgency():
    ad = GeneratedAd(
        ad_id="test_urgency",
        primary_text="Spots filling fast! Don't miss out on SAT tutoring.",
        headline="Limited Enrollment",
        description="Act now",
        cta_button="Sign Up",
    )
    violations = _compliance_pre_check(ad)
    assert any("fake_urgency" in v for v in violations)


# --- Persona CTA in prompt ---


def test_prompt_includes_persona_preferred_cta():
    brief = _make_brief(persona="athlete_recruit")
    prompt = _build_generation_prompt(brief, [])
    # Should include athlete's preferred CTA or hook CTA
    assert "specialist" in prompt.lower() or "Talk to" in prompt or "Preferred CTA" in prompt


def test_prompt_includes_offer_context_for_conversion():
    brief = _make_brief(campaign_goal="conversion")
    prompt = _build_generation_prompt(brief, [])
    assert "membership" in prompt.lower() or "100" in prompt


def test_prompt_no_offer_for_awareness():
    brief = _make_brief(campaign_goal="awareness")
    prompt = _build_generation_prompt(brief, [])
    assert "Offer Context" not in prompt


# --- CTA validation ---


def test_persona_cta_accepted():
    response = json.dumps({
        "primary_text": "Your child deserves better SAT tutoring.",
        "headline": "SAT Tutoring That Works",
        "description": "1:1 expert matched to your child",
        "cta_button": "Talk to an SAT specialist today",
    })
    ad = _parse_generation_response(response, "test_cta", [], "brief", {})
    assert ad.cta_button == "Talk to an SAT specialist today"
    assert ad.cta_button in VALID_CTAS


def test_all_persona_ctas_in_valid_set():
    """All persona CTAs from brand KB should be in VALID_CTAS."""
    persona_ctas = [
        "Book Diagnostic",
        "Talk to an SAT specialist today",
        "See what score range is realistic in 8–10 weeks",
        "Tell us about your child",
        "Tell us what went wrong",
    ]
    for cta in persona_ctas:
        assert cta in VALID_CTAS, f"Persona CTA '{cta}' not in VALID_CTAS"


# --- Prompt has Nerdy rules ---


def test_prompt_has_nerdy_language_rules():
    brief = _make_brief()
    prompt = _build_generation_prompt(brief, [])
    assert "your child" in prompt.lower()
    assert "NEVER" in prompt  # NEVER "your student"
    assert "SAT Tutoring" in prompt
