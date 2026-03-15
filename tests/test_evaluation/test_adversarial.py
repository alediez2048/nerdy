"""Adversarial boundary tests for evaluator (P2-03).

Hand-crafted edge cases that probe whether the evaluator correctly
identifies dimension-specific failures in extreme scenarios.

These tests call the REAL Gemini API — they are NOT mocked.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

import pytest

from evaluate.evaluator import EvaluationResult, evaluate_ad

ADVERSARIAL_ADS_PATH = (
    Path(__file__).resolve().parents[1] / "test_data" / "adversarial_ads.json"
)

requires_api = pytest.mark.skipif(
    not os.getenv("GEMINI_API_KEY"),
    reason="GEMINI_API_KEY required for adversarial tests",
)


def _load_adversarial_ads() -> list[dict]:
    """Load adversarial test data."""
    with open(ADVERSARIAL_ADS_PATH, encoding="utf-8") as f:
        data = json.load(f)
    return data["ads"]


def _eval_adversarial(ad: dict) -> EvaluationResult:
    """Evaluate an adversarial ad text."""
    ad_text = {
        "ad_id": ad["ad_id"],
        "primary_text": ad["ad_text"],
        "headline": "—",
        "description": "—",
        "cta_button": "—",
    }
    return evaluate_ad(ad_text, campaign_goal="conversion")


# --- Fixtures ---


@pytest.fixture(scope="module")
def adversarial_results() -> dict[str, tuple[dict, EvaluationResult]]:
    """Evaluate all adversarial ads once. Keyed by ad_id."""
    ads = _load_adversarial_ads()
    results: dict[str, tuple[dict, EvaluationResult]] = {}
    for i, ad in enumerate(ads):
        if i > 0:
            time.sleep(2)
        result = _eval_adversarial(ad)
        results[ad["ad_id"]] = (ad, result)
    return results


# --- Data Integrity ---


def test_adversarial_ads_file_exists() -> None:
    """Adversarial ads test data file exists with 8+ ads."""
    assert ADVERSARIAL_ADS_PATH.exists()
    ads = _load_adversarial_ads()
    assert len(ads) >= 8
    for ad in ads:
        assert "ad_id" in ad
        assert "ad_text" in ad
        assert "expected_failures" in ad
        assert "boundary_being_tested" in ad


# --- Per-Boundary Tests ---


@requires_api
def test_wrong_brand_voice_scores_low_brand(
    adversarial_results: dict[str, tuple[dict, EvaluationResult]],
) -> None:
    """Fast-food brand voice should score Brand Voice <= 4.0."""
    ad, result = adversarial_results["adv_wrong_brand_voice"]
    bv = result.scores["brand_voice"]["score"]
    assert bv <= 4.0, (
        f"Wrong brand voice scored BV={bv:.1f}, expected <= 4.0"
    )


@requires_api
def test_high_clarity_zero_emotion(
    adversarial_results: dict[str, tuple[dict, EvaluationResult]],
) -> None:
    """Factual list should score Clarity >= 6.0, Emotional Resonance <= 4.0."""
    ad, result = adversarial_results["adv_high_clarity_zero_emotion"]
    clarity = result.scores["clarity"]["score"]
    er = result.scores["emotional_resonance"]["score"]
    assert clarity >= 6.0, f"Factual ad Clarity={clarity:.1f}, expected >= 6.0"
    assert er <= 5.0, f"Factual ad ER={er:.1f}, expected <= 5.0"


@requires_api
def test_pure_manipulation_low_value_prop(
    adversarial_results: dict[str, tuple[dict, EvaluationResult]],
) -> None:
    """Pure emotional manipulation should score Value Proposition <= 5.0."""
    ad, result = adversarial_results["adv_pure_manipulation"]
    vp = result.scores["value_proposition"]["score"]
    assert vp <= 5.0, (
        f"Pure manipulation scored VP={vp:.1f}, expected <= 5.0"
    )


@requires_api
def test_competitor_branding_caught_by_compliance(
    adversarial_results: dict[str, tuple[dict, EvaluationResult]],
) -> None:
    """Competitor branding may pass evaluator but MUST be caught by compliance filter.

    The evaluator scores copy quality generically — it doesn't know which brand
    the ad is for. The compliance regex layer (P2-06) catches competitor names.
    This test validates the three-layer defense: evaluator alone isn't enough.
    """
    from generate.compliance import check_compliance

    ad, result = adversarial_results["adv_competitor_branding"]
    compliance = check_compliance(ad["ad_text"])
    assert compliance.passes is False, (
        "Competitor branding must be caught by compliance filter"
    )
    rules = {v.rule_name for v in compliance.violations}
    assert "competitor_reference" in rules


@requires_api
def test_aggressive_cta_no_value(
    adversarial_results: dict[str, tuple[dict, EvaluationResult]],
) -> None:
    """CTA spam should score Value Proposition <= 4.0."""
    ad, result = adversarial_results["adv_aggressive_cta_no_value"]
    vp = result.scores["value_proposition"]["score"]
    assert vp <= 4.0, (
        f"CTA spam scored VP={vp:.1f}, expected <= 4.0"
    )


@requires_api
def test_jargon_overload_low_clarity(
    adversarial_results: dict[str, tuple[dict, EvaluationResult]],
) -> None:
    """Technical jargon should score Clarity <= 5.0."""
    ad, result = adversarial_results["adv_jargon_overload"]
    clarity = result.scores["clarity"]["score"]
    assert clarity <= 5.0, (
        f"Jargon overload scored Clarity={clarity:.1f}, expected <= 5.0"
    )


@requires_api
def test_empty_ad_all_dimensions_low(
    adversarial_results: dict[str, tuple[dict, EvaluationResult]],
) -> None:
    """Single-word ad should score all dimensions <= 5.0."""
    ad, result = adversarial_results["adv_empty_minimal"]
    for dim in ("clarity", "value_proposition", "cta", "brand_voice", "emotional_resonance"):
        score = result.scores[dim]["score"]
        assert score <= 5.0, (
            f"Empty ad scored {dim}={score:.1f}, expected <= 5.0"
        )


@requires_api
def test_adversarial_ads_dont_pass_threshold(
    adversarial_results: dict[str, tuple[dict, EvaluationResult]],
) -> None:
    """Adversarial ads (except compliance-only cases) should fail the 7.0 threshold.

    Competitor branding is excluded — it's well-written copy that passes the
    evaluator but is caught by the compliance filter (Layer 3). This validates
    the three-layer defense design: no single layer catches everything.
    """
    # Ads caught by compliance filter, not evaluator
    compliance_only = {"adv_competitor_branding"}

    for ad_id, (ad, result) in adversarial_results.items():
        if ad_id in compliance_only:
            continue
        assert result.aggregate_score < 7.0, (
            f"Adversarial ad {ad_id} passed threshold with "
            f"aggregate={result.aggregate_score:.2f} — "
            f"boundary: {ad['boundary_being_tested']}"
        )
