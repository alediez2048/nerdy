"""Tests for tiered compliance filter (P2-06)."""

from __future__ import annotations

from generate.compliance import (
    ComplianceResult,
    check_compliance,
    check_evaluator_compliance,
    is_compliant,
)


KNOWN_BAD_ADS = [
    "Guaranteed 1500+ SAT score or your money back!",
    "Princeton Review is terrible — choose us instead",
    "100% of students pass with our program, always",
    "Your child is falling behind — don't let them fail",
    "Only $49.99 for unlimited tutoring sessions!",
]

CLEAN_AD = (
    "Is your child's SAT score holding them back from their dream school? "
    "Varsity Tutors pairs your student with expert 1-on-1 tutors who adapt "
    "to how they learn. See the difference personalized prep can make. "
    "Start with a free practice test today."
)


# --- Structure ---


def test_compliance_result_structure() -> None:
    """ComplianceResult has passes bool and violations list."""
    result = check_compliance("Some text")
    assert isinstance(result, ComplianceResult)
    assert isinstance(result.passes, bool)
    assert isinstance(result.violations, list)


# --- Pattern Detection ---


def test_guaranteed_score_caught() -> None:
    """'Guaranteed 1500+ SAT score' triggers violation."""
    result = check_compliance("Guaranteed 1500+ SAT score or your money back!")
    assert result.passes is False
    rules = {v.rule_name for v in result.violations}
    assert "guaranteed_outcome" in rules or "absolute_promise" in rules


def test_competitor_name_caught() -> None:
    """Competitor name in negative context triggers violation."""
    result = check_compliance("Princeton Review is terrible — choose us instead")
    assert result.passes is False
    rules = {v.rule_name for v in result.violations}
    assert "competitor_reference" in rules


def test_absolute_promise_caught() -> None:
    """'100% of students pass' triggers violation."""
    result = check_compliance("100% of students pass with our program, always")
    assert result.passes is False
    rules = {v.rule_name for v in result.violations}
    assert "absolute_promise" in rules or "guaranteed_outcome" in rules


def test_dollar_amount_caught() -> None:
    """Dollar amount without disclaimer triggers violation."""
    result = check_compliance("Only $49.99 for unlimited tutoring sessions!")
    assert result.passes is False
    rules = {v.rule_name for v in result.violations}
    assert "unverified_pricing" in rules


def test_fear_language_caught() -> None:
    """Fear-based language targeting the child triggers violation."""
    result = check_compliance("Your child is falling behind — don't let them fail")
    assert result.passes is False
    rules = {v.rule_name for v in result.violations}
    assert "fear_language" in rules


def test_clean_ad_passes() -> None:
    """Well-written compliant ad has no violations."""
    result = check_compliance(CLEAN_AD)
    assert result.passes is True
    assert len(result.violations) == 0


def test_multiple_violations_all_reported() -> None:
    """Ad with multiple violations reports all of them."""
    bad_text = (
        "Guaranteed 1600 SAT score! 100% success rate! "
        "Princeton Review can't match our $29.99 deal!"
    )
    result = check_compliance(bad_text)
    assert result.passes is False
    assert len(result.violations) >= 3


def test_case_insensitive_matching() -> None:
    """GUARANTEED and guaranteed both caught."""
    result_upper = check_compliance("GUARANTEED improvement!")
    result_lower = check_compliance("guaranteed improvement!")
    assert result_upper.passes is False
    assert result_lower.passes is False


def test_is_compliant_convenience() -> None:
    """is_compliant() returns True/False correctly."""
    assert is_compliant(CLEAN_AD) is True
    assert is_compliant("Guaranteed 1600!") is False


# --- Three-Layer Validation ---


def test_three_layers_catch_all_violations() -> None:
    """All known-bad ads caught by regex layer (zero false negatives)."""
    for bad_ad in KNOWN_BAD_ADS:
        result = check_compliance(bad_ad)
        assert result.passes is False, (
            f"Known-bad ad not caught: '{bad_ad[:50]}...'"
        )


# --- Evaluator Compliance Check (Layer 2) ---


def test_evaluator_compliance_low_score_fails() -> None:
    """Any dimension score < 4.0 fails evaluator compliance."""
    scores = {
        "clarity": {"score": 7.0, "confidence": 8},
        "value_proposition": {"score": 7.0, "confidence": 8},
        "cta": {"score": 7.0, "confidence": 8},
        "brand_voice": {"score": 3.5, "confidence": 8},
        "emotional_resonance": {"score": 7.0, "confidence": 8},
    }
    assert check_evaluator_compliance(scores) is False


def test_evaluator_compliance_all_above_threshold() -> None:
    """All dimensions >= 4.0 passes evaluator compliance."""
    scores = {
        "clarity": {"score": 7.0, "confidence": 8},
        "value_proposition": {"score": 7.0, "confidence": 8},
        "cta": {"score": 6.0, "confidence": 8},
        "brand_voice": {"score": 5.0, "confidence": 8},
        "emotional_resonance": {"score": 6.5, "confidence": 8},
    }
    assert check_evaluator_compliance(scores) is True
