"""Tests for campaign-goal-adaptive weighting and floor constraints (P1-05)."""

from __future__ import annotations


from evaluate.dimensions import (
    AWARENESS_WEIGHTS,
    CONVERSION_WEIGHTS,
    check_floor_violations,
    compute_weighted_score,
    evaluate_with_weights,
    get_weight_profile,
)


# --- Weight Profile Tests ---


def test_awareness_weights_sum_to_one() -> None:
    """Awareness weight profile must sum to 1.0."""
    total = sum(AWARENESS_WEIGHTS.weights.values())
    assert abs(total - 1.0) < 1e-9, f"Awareness weights sum to {total}, expected 1.0"


def test_conversion_weights_sum_to_one() -> None:
    """Conversion weight profile must sum to 1.0."""
    total = sum(CONVERSION_WEIGHTS.weights.values())
    assert abs(total - 1.0) < 1e-9, f"Conversion weights sum to {total}, expected 1.0"


def test_awareness_profile_selected_for_awareness_goal() -> None:
    """get_weight_profile('awareness') returns awareness weights."""
    profile = get_weight_profile("awareness")
    assert profile.campaign_goal == "awareness"
    assert profile.weights["emotional_resonance"] == 0.25
    assert profile.weights["cta"] == 0.10


def test_conversion_profile_selected_for_conversion_goal() -> None:
    """get_weight_profile('conversion') returns conversion weights."""
    profile = get_weight_profile("conversion")
    assert profile.campaign_goal == "conversion"
    assert profile.weights["cta"] == 0.30
    assert profile.weights["emotional_resonance"] == 0.10


def test_unknown_goal_falls_back_to_awareness() -> None:
    """Unknown campaign goal defaults to awareness profile."""
    profile = get_weight_profile("unknown_goal")
    assert profile.campaign_goal == "awareness"


# --- Weighted Score Computation Tests ---


def test_weighted_score_awareness_hand_calculated() -> None:
    """Hand-calculated weighted average for awareness profile."""
    scores = {
        "clarity": 8.0,
        "value_proposition": 7.0,
        "cta": 6.0,
        "brand_voice": 9.0,
        "emotional_resonance": 8.0,
    }
    profile = get_weight_profile("awareness")
    # 8.0*0.25 + 7.0*0.20 + 6.0*0.10 + 9.0*0.20 + 8.0*0.25
    # = 2.0 + 1.4 + 0.6 + 1.8 + 2.0 = 7.8
    result = compute_weighted_score(scores, profile)
    assert abs(result - 7.8) < 0.01, f"Expected 7.8, got {result}"


def test_weighted_score_conversion_hand_calculated() -> None:
    """Hand-calculated weighted average for conversion profile."""
    scores = {
        "clarity": 8.0,
        "value_proposition": 7.0,
        "cta": 6.0,
        "brand_voice": 9.0,
        "emotional_resonance": 8.0,
    }
    profile = get_weight_profile("conversion")
    # 8.0*0.25 + 7.0*0.25 + 6.0*0.30 + 9.0*0.10 + 8.0*0.10
    # = 2.0 + 1.75 + 1.8 + 0.9 + 0.8 = 7.25
    result = compute_weighted_score(scores, profile)
    assert abs(result - 7.25) < 0.01, f"Expected 7.25, got {result}"


# --- Floor Constraint Tests ---


def test_clarity_floor_violation_detected() -> None:
    """Clarity score below 6.0 triggers floor violation."""
    scores = {
        "clarity": 5.5,
        "value_proposition": 8.0,
        "cta": 7.0,
        "brand_voice": 7.0,
        "emotional_resonance": 8.0,
    }
    violations = check_floor_violations(scores)
    assert len(violations) == 1
    assert violations[0].dimension == "clarity"
    assert violations[0].floor == 6.0
    assert abs(violations[0].deficit - 0.5) < 0.01


def test_brand_voice_floor_violation_detected() -> None:
    """Brand Voice score below 5.0 triggers floor violation."""
    scores = {
        "clarity": 7.0,
        "value_proposition": 8.0,
        "cta": 7.0,
        "brand_voice": 4.5,
        "emotional_resonance": 8.0,
    }
    violations = check_floor_violations(scores)
    assert len(violations) == 1
    assert violations[0].dimension == "brand_voice"
    assert violations[0].floor == 5.0


def test_no_floor_violations_when_above_floors() -> None:
    """No violations when all scores meet floor constraints."""
    scores = {
        "clarity": 7.0,
        "value_proposition": 8.0,
        "cta": 7.0,
        "brand_voice": 6.0,
        "emotional_resonance": 8.0,
    }
    violations = check_floor_violations(scores)
    assert len(violations) == 0


# --- evaluate_with_weights Integration Tests ---


def test_good_weighted_average_but_floor_violation_rejected() -> None:
    """Ad with weighted avg >= 7.0 but floor violation is rejected."""
    scores = {
        "clarity": 5.0,  # Below 6.0 floor
        "value_proposition": 9.0,
        "cta": 9.0,
        "brand_voice": 9.0,
        "emotional_resonance": 9.0,
    }
    result = evaluate_with_weights(scores, "awareness")
    assert not result.passes_threshold
    assert len(result.floor_violations) > 0
    assert any("clarity" in r.lower() for r in result.rejection_reasons)


def test_no_violations_above_threshold_passes() -> None:
    """Ad with no floor violations and weighted avg >= 7.0 passes."""
    scores = {
        "clarity": 8.0,
        "value_proposition": 7.5,
        "cta": 7.0,
        "brand_voice": 8.0,
        "emotional_resonance": 7.5,
    }
    result = evaluate_with_weights(scores, "awareness")
    assert result.passes_threshold
    assert len(result.floor_violations) == 0
    assert len(result.rejection_reasons) == 0


def test_below_threshold_no_violations_rejected() -> None:
    """Ad with no floor violations but weighted avg < 7.0 is rejected."""
    scores = {
        "clarity": 6.0,
        "value_proposition": 6.0,
        "cta": 6.0,
        "brand_voice": 6.0,
        "emotional_resonance": 6.0,
    }
    result = evaluate_with_weights(scores, "awareness")
    assert not result.passes_threshold
    assert len(result.floor_violations) == 0
    assert any("threshold" in r.lower() or "7.0" in r for r in result.rejection_reasons)


def test_rejection_reasons_are_human_readable() -> None:
    """Rejection reasons should be clear, human-readable strings."""
    scores = {
        "clarity": 5.0,
        "value_proposition": 6.0,
        "cta": 6.0,
        "brand_voice": 4.0,
        "emotional_resonance": 6.0,
    }
    result = evaluate_with_weights(scores, "conversion")
    assert len(result.rejection_reasons) >= 2
    for reason in result.rejection_reasons:
        assert isinstance(reason, str)
        assert len(reason) > 10  # Not just a code, but a readable message


def test_weighted_result_contains_weight_profile() -> None:
    """WeightedResult includes the weight profile that was used."""
    scores = {
        "clarity": 8.0,
        "value_proposition": 8.0,
        "cta": 8.0,
        "brand_voice": 8.0,
        "emotional_resonance": 8.0,
    }
    result = evaluate_with_weights(scores, "conversion")
    assert result.weight_profile.campaign_goal == "conversion"
    assert result.campaign_goal == "conversion"


def test_equal_scores_different_goals_different_averages() -> None:
    """Same scores with different goals should produce different weighted averages."""
    scores = {
        "clarity": 7.0,
        "value_proposition": 7.0,
        "cta": 9.0,
        "brand_voice": 7.0,
        "emotional_resonance": 5.5,
    }
    awareness_result = evaluate_with_weights(scores, "awareness")
    conversion_result = evaluate_with_weights(scores, "conversion")
    # Conversion weights CTA at 0.30 vs awareness at 0.10 — conversion should score higher
    assert conversion_result.weighted_average > awareness_result.weighted_average
