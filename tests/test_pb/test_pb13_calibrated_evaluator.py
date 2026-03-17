# PB-13: Calibrated evaluator tests
"""Tests for PB-13 additions: fake urgency ER penalty, meta structure bonus,
your_child positive signal, expanded persona matching."""

from evaluate.evaluator import _apply_nerdy_adjustments


def _scores(bv=7.0, cl=7.0, vp=7.0, cta=7.0, er=7.0):
    return {
        "brand_voice": {"score": bv, "rationale": "test", "confidence": 8},
        "clarity": {"score": cl, "rationale": "test", "confidence": 8},
        "value_proposition": {"score": vp, "rationale": "test", "confidence": 8},
        "cta": {"score": cta, "rationale": "test", "confidence": 8},
        "emotional_resonance": {"score": er, "rationale": "test", "confidence": 8},
    }


def _ad(primary="", headline="", description=""):
    return {"primary_text": primary, "headline": headline, "description": description}


# --- PB-13: Fake urgency also hurts ER ---


def test_fake_urgency_penalizes_er():
    scores = _scores(er=7.0)
    ad = _ad(primary="Spots filling fast! Don't miss out on SAT tutoring.")
    result = _apply_nerdy_adjustments(scores, ad)
    assert result["emotional_resonance"]["score"] <= 6.0  # -1.0


# --- PB-13: Meta ad structure bonus ---


def test_short_hook_line_boosts_clarity():
    scores = _scores(cl=7.0)
    ad = _ad(primary="3.8 GPA. 1260 SAT. Something's off.\nThe SAT isn't a classroom test. Most strong students are 3-4 fixes away from a 1400+.\nSee what score is realistic in 8-10 weeks.")
    result = _apply_nerdy_adjustments(scores, ad)
    assert result["clarity"]["score"] >= 7.3  # +0.3


def test_no_bonus_for_long_first_line():
    scores = _scores(cl=7.0)
    ad = _ad(primary="This is a very long first line that goes on and on and on and keeps going beyond 80 characters for sure without stopping")
    result = _apply_nerdy_adjustments(scores, ad)
    assert result["clarity"]["score"] == 7.0  # no bonus


# --- PB-13: "your child" positive signal ---


def test_your_child_without_student_gets_bv_bonus():
    scores = _scores(bv=7.0)
    ad = _ad(primary="Your child can raise their SAT score with expert tutoring.")
    result = _apply_nerdy_adjustments(scores, ad)
    assert result["brand_voice"]["score"] >= 7.3  # +0.3


def test_your_child_with_student_no_bonus():
    scores = _scores(bv=7.0)
    ad = _ad(primary="Your child... err your student needs help")
    result = _apply_nerdy_adjustments(scores, ad)
    # "your student" caps at 4.0, no bonus
    assert result["brand_voice"]["score"] <= 4.0


# --- PB-13: Expanded persona matching ---


def test_strong_persona_match_higher_bonus():
    scores = _scores(er=7.0)
    # Two keywords: "scholarship" + "recruit"
    ad = _ad(primary="The scholarship window is closing. Recruiting coaches need that SAT score.")
    result = _apply_nerdy_adjustments(scores, ad, persona="athlete_recruit")
    assert result["emotional_resonance"]["score"] >= 7.7  # +0.7 for 2+ matches


def test_single_keyword_partial_match():
    scores = _scores(er=7.0)
    ad = _ad(primary="The coach needs a better SAT score from your child.")
    result = _apply_nerdy_adjustments(scores, ad, persona="athlete_recruit")
    assert result["emotional_resonance"]["score"] >= 7.4  # +0.4 for 1 match
    assert result["emotional_resonance"]["score"] < 7.7  # less than strong match


def test_no_keyword_match_no_bonus():
    scores = _scores(er=7.0)
    ad = _ad(primary="Improve your SAT score with expert tutoring")
    result = _apply_nerdy_adjustments(scores, ad, persona="athlete_recruit")
    assert result["emotional_resonance"]["score"] == 7.0
