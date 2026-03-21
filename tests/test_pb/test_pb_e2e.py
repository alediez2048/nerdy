# PB-08: End-to-end pipeline test with persona
"""Tests that brief → expand → generate → evaluate → compliance works with persona context."""

import json
from unittest.mock import patch

from generate.brief_expansion import expand_brief
from generate.ad_generator import GeneratedAd, _build_generation_prompt, _parse_generation_response, VALID_CTAS
from generate.compliance import check_compliance, check_nerdy_positives
from evaluate.evaluator import _apply_nerdy_adjustments


def _mock_gemini_expansion() -> tuple[str, int]:
    return (json.dumps({
        "audience_profile": {"pain_points": ["recruiting timeline"], "emotional_drivers": ["scholarship fear"], "tone": "urgent"},
        "brand_facts": [{"claim": "1-on-1 SAT tutoring", "source": "supplementary"}],
        "competitive_context_summary": "VT: 1:1 vs Princeton Review group at $252/hr",
        "emotional_angles": ["scholarship urgency", "recruiting window closing"],
        "value_propositions": ["10X vs self-study", "100pts/month at 2x/week"],
        "key_differentiators": ["digital SAT training", "late evening availability"],
        "constraints": ["no fake urgency", "use your child"],
    }), 100)


def _mock_gemini_ad() -> str:
    return json.dumps({
        "primary_text": "The coach wants him. The admissions office needs an SAT score. Your child is 3-4 targeted fixes away from eligibility. We diagnose exactly where points are hiding with a free diagnostic. 100 points per month at 2 sessions per week.",
        "headline": "SAT Tutoring Around Practice",
        "description": "1:1 expert tutoring matched to your child's schedule. Late evening sessions available.",
        "cta_button": "Talk to an SAT specialist today",
    })


def test_full_pipeline_with_persona():
    """Brief → expand → generate → evaluate → compliance — full chain."""
    brief = {"audience": "parents", "campaign_goal": "conversion", "brief_id": "e2e_001"}

    # Step 1: Expand with persona
    with (
        patch("generate.brief_expansion._call_gemini", return_value=_mock_gemini_expansion()),
        patch("generate.brief_expansion.log_event"),
    ):
        expanded = expand_brief(brief, persona="athlete_recruit")

    assert expanded.persona == "athlete_recruit"
    assert len(expanded.suggested_hooks) >= 1

    # Step 2: Build generation prompt (verify it includes Nerdy rules)
    prompt = _build_generation_prompt(expanded, [])
    assert "your child" in prompt.lower()
    assert "your student" in prompt.lower()  # in the NEVER rule

    # Step 3: Parse a mock generated ad
    ad = _parse_generation_response(_mock_gemini_ad(), "ad_e2e_001", [], "e2e_001", {})
    assert isinstance(ad, GeneratedAd)
    assert ad.cta_button in VALID_CTAS

    # Step 4: Compliance check
    full_text = f"{ad.primary_text} {ad.headline} {ad.description}"
    result = check_compliance(full_text)
    assert result.passes, f"Critical violations: {[v.rule_name for v in result.critical_violations]}"

    # Step 5: Nerdy positives
    positives = check_nerdy_positives(full_text)
    assert "uses_your_child" in positives

    # Step 6: Evaluate (deterministic adjustments only)
    scores = {
        "brand_voice": {"score": 7.5, "rationale": "good", "confidence": 8},
        "clarity": {"score": 7.5, "rationale": "good", "confidence": 8},
        "value_proposition": {"score": 7.0, "rationale": "good", "confidence": 8},
        "cta": {"score": 7.0, "rationale": "good", "confidence": 8},
        "emotional_resonance": {"score": 7.0, "rationale": "good", "confidence": 8},
    }
    adjusted = _apply_nerdy_adjustments(scores, ad.to_evaluator_input(), persona="athlete_recruit")
    # Should get bonuses (conditional claim, persona match) not penalties
    assert adjusted["value_proposition"]["score"] >= 7.0
    assert adjusted["brand_voice"]["score"] >= 7.0  # no penalties on clean copy


def test_pipeline_zero_critical_violations():
    """Generated ad with Nerdy-approved copy has no critical compliance violations."""
    clean_ad = {
        "primary_text": "Your child can gain 200 points in 16 sessions. The digital SAT interface has tools most students don't know how to use. Princeton Review charges $252/hr for 1:1. We charge $349/month.",
        "headline": "SAT Tutoring That Raises Scores",
        "description": "1:1 expert matched to your child",
        "cta_button": "Book Diagnostic",
    }
    full_text = f"{clean_ad['primary_text']} {clean_ad['headline']} {clean_ad['description']}"
    result = check_compliance(full_text)
    assert len(result.critical_violations) == 0


def test_pipeline_catches_bad_nerdy_copy():
    """Ad with Nerdy violations gets caught by compliance + evaluator."""
    bad_ad = {
        "primary_text": "Help your student with SAT Prep! Spots filling fast. Unlock their potential!",
        "headline": "Online Tutoring Available",
        "description": "Limited enrollment. Don't miss out.",
        "cta_button": "Learn More",
    }
    full_text = f"{bad_ad['primary_text']} {bad_ad['headline']} {bad_ad['description']}"

    # Compliance catches it
    result = check_compliance(full_text)
    assert not result.passes
    assert result.has_critical
    critical_rules = {v.rule_name for v in result.critical_violations}
    assert "nerdy_wrong_address" in critical_rules  # your student
    assert "nerdy_wrong_product" in critical_rules  # SAT Prep
    assert "fake_urgency" in critical_rules

    # Evaluator penalizes it
    scores = {d: {"score": 7.0, "rationale": "test", "confidence": 8}
              for d in ["brand_voice", "clarity", "value_proposition", "cta", "emotional_resonance"]}
    adjusted = _apply_nerdy_adjustments(scores, bad_ad)
    assert adjusted["brand_voice"]["score"] <= 4.0  # "your student" caps at 4
    assert adjusted["clarity"]["score"] <= 6.0  # "unlock potential" penalty


def test_pipeline_persona_in_expanded_brief():
    """Persona metadata flows through expansion."""
    brief = {"audience": "parents", "campaign_goal": "awareness", "brief_id": "e2e_meta"}

    with (
        patch("generate.brief_expansion._call_gemini", return_value=_mock_gemini_expansion()),
        patch("generate.brief_expansion.log_event"),
    ):
        expanded = expand_brief(brief, persona="neurodivergent_advocate")

    assert expanded.persona == "neurodivergent_advocate"
    assert expanded.messaging_rules is not None
    assert "dos" in expanded.messaging_rules


def test_pipeline_hook_attribution():
    """Expanded brief includes hook IDs for attribution."""
    brief = {"audience": "parents", "campaign_goal": "conversion", "brief_id": "e2e_hooks"}

    with (
        patch("generate.brief_expansion._call_gemini", return_value=_mock_gemini_expansion()),
        patch("generate.brief_expansion.log_event"),
    ):
        expanded = expand_brief(brief, persona="suburban_optimizer")

    assert len(expanded.suggested_hooks) >= 1
    assert all("hook_id" in h for h in expanded.suggested_hooks)
