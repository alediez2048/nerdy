# PB-06: Nerdy-calibrated evaluator tests
"""Tests for Nerdy language penalties, specificity bonuses, and persona matching."""

from evaluate.evaluator import _apply_nerdy_adjustments, _build_evaluation_prompt


def _make_scores(bv=7.0, cl=7.0, vp=7.0, cta=7.0, er=7.0):
    """Create a scores dict with given values."""
    return {
        "brand_voice": {"score": bv, "rationale": "test", "confidence": 8},
        "clarity": {"score": cl, "rationale": "test", "confidence": 8},
        "value_proposition": {"score": vp, "rationale": "test", "confidence": 8},
        "cta": {"score": cta, "rationale": "test", "confidence": 8},
        "emotional_resonance": {"score": er, "rationale": "test", "confidence": 8},
    }


def _make_ad(primary="", headline="", description="", cta="Learn More"):
    return {"primary_text": primary, "headline": headline, "description": description, "cta_button": cta}


# --- Penalties ---


def test_your_student_caps_brand_voice_at_4():
    scores = _make_scores(bv=8.0)
    ad = _make_ad(primary="Help your student succeed on the SAT")
    result = _apply_nerdy_adjustments(scores, ad)
    assert result["brand_voice"]["score"] <= 4.0


def test_sat_prep_reduces_brand_voice():
    scores = _make_scores(bv=7.0)
    ad = _make_ad(primary="Best SAT Prep program in the country")
    result = _apply_nerdy_adjustments(scores, ad)
    assert result["brand_voice"]["score"] <= 6.0  # 7.0 - 1.0


def test_fake_urgency_reduces_brand_voice():
    scores = _make_scores(bv=7.0)
    ad = _make_ad(primary="Spots filling fast! Don't miss out!")
    result = _apply_nerdy_adjustments(scores, ad)
    assert result["brand_voice"]["score"] <= 5.5  # 7.0 - 1.5


def test_corporate_jargon_reduces_clarity():
    scores = _make_scores(cl=7.0)
    ad = _make_ad(primary="Unlock their potential with our tailored support")
    result = _apply_nerdy_adjustments(scores, ad)
    assert result["clarity"]["score"] <= 6.0  # 7.0 - 1.0


def test_online_tutoring_reduces_brand_voice():
    scores = _make_scores(bv=7.0)
    ad = _make_ad(primary="Try our online tutoring platform today")
    result = _apply_nerdy_adjustments(scores, ad)
    assert result["brand_voice"]["score"] <= 6.0


# --- Bonuses ---


def test_conditional_claim_boosts_vp():
    scores = _make_scores(vp=7.0)
    ad = _make_ad(primary="Your child can gain 200 points in 16 sessions with focused 1:1 SAT Tutoring")
    result = _apply_nerdy_adjustments(scores, ad)
    assert result["value_proposition"]["score"] >= 7.5  # 7.0 + 0.5


def test_specific_mechanism_boosts_vp():
    scores = _make_scores(vp=7.0)
    ad = _make_ad(primary="The digital SAT interface has a built-in calculator that most students don't use")
    result = _apply_nerdy_adjustments(scores, ad)
    assert result["value_proposition"]["score"] >= 7.5


def test_competitor_data_boosts_vp():
    scores = _make_scores(vp=7.0)
    ad = _make_ad(primary="Princeton Review charges $252/hr for 1:1. We charge $349/month.")
    result = _apply_nerdy_adjustments(scores, ad)
    assert result["value_proposition"]["score"] >= 7.5


# --- Persona matching ---


def test_athlete_persona_keywords_boost_er():
    scores = _make_scores(er=7.0)
    ad = _make_ad(primary="The coach wants him. The recruiting window is closing and your child needs the SAT score.")
    result = _apply_nerdy_adjustments(scores, ad, persona="athlete_recruit")
    assert result["emotional_resonance"]["score"] >= 7.5


def test_no_persona_keywords_no_er_change():
    scores = _make_scores(er=7.0)
    ad = _make_ad(primary="Your child can improve their SAT score with tutoring")
    result = _apply_nerdy_adjustments(scores, ad, persona="athlete_recruit")
    assert result["emotional_resonance"]["score"] == 7.0  # no keywords matched


# --- Clean copy stays clean ---


def test_clean_nerdy_copy_no_penalties():
    scores = _make_scores(bv=7.5, cl=7.5, vp=7.0, er=7.0)
    ad = _make_ad(
        primary="3.8 GPA. 1260 SAT. Something's off. Your child is 3-4 fixes away from a 1400+.",
        headline="SAT Tutoring That Raises Scores",
    )
    result = _apply_nerdy_adjustments(scores, ad)
    # No penalties — may get bonuses (your_child +0.3 BV, meta structure +0.3 CL)
    assert result["brand_voice"]["score"] >= 7.5
    assert result["clarity"]["score"] >= 7.5


# --- Combined penalties stack ---


def test_multiple_violations_stack():
    scores = _make_scores(bv=8.0, cl=8.0)
    ad = _make_ad(primary="Help your student with SAT Prep. Unlock their potential! Spots filling fast!")
    result = _apply_nerdy_adjustments(scores, ad)
    # "your student" caps at 4.0, then "SAT Prep" -1.0 → 3.0, then fake urgency -1.5 → 1.5, clamped to 1.0
    assert result["brand_voice"]["score"] <= 4.0
    # "unlock potential" → clarity -1.0
    assert result["clarity"]["score"] <= 7.0


# --- Prompt includes Nerdy calibration ---


def test_prompt_includes_nerdy_calibration_anchors():
    ad = _make_ad(primary="Test ad", headline="Test")
    ad["ad_id"] = "test_001"
    prompt = _build_evaluation_prompt(ad, "conversion", "parents")
    assert "3.8 GPA. 1260 SAT" in prompt
    assert "your student" in prompt.lower()
    assert "spots filling fast" in prompt.lower()
    assert "Nerdy" in prompt or "NERDY" in prompt
