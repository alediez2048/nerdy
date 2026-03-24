"""Tests for visual attribute evaluator + Pareto image selection (P1-15)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch


from evaluate.image_evaluator import (
    ImageAttributeResult,
    evaluate_image_attributes,
)
from evaluate.image_selector import (
    ImageVariantResult,
    ImageSelectionResult,
    compute_composite_score,
    select_best_variant,
)

ATTRIBUTES = ("age_appropriate", "lighting", "diversity", "brand_consistent", "no_artifacts")


def _make_attribute_result(
    passes: dict[str, bool] | None = None,
) -> ImageAttributeResult:
    """Build an ImageAttributeResult with given pass/fail flags."""
    if passes is None:
        passes = {a: True for a in ATTRIBUTES}
    return ImageAttributeResult(
        ad_id="ad_001",
        variant_type="anchor",
        attributes=passes,
        attribute_pass_pct=sum(passes.values()) / len(passes),
        meets_threshold=sum(passes.values()) / len(passes) >= 0.8,
    )


def _make_variant_result(
    variant_type: str,
    attribute_pass_pct: float,
    coherence_avg: float = 1.0,
) -> ImageVariantResult:
    """Build an ImageVariantResult for selection tests."""
    return ImageVariantResult(
        ad_id="ad_001",
        variant_type=variant_type,
        attribute_pass_pct=attribute_pass_pct,
        coherence_avg=coherence_avg,
        composite_score=compute_composite_score(attribute_pass_pct, coherence_avg),
        image_path=f"/tmp/{variant_type}.png",
    )


# --- Attribute Evaluation Tests ---


def test_attribute_result_all_pass() -> None:
    """All 5 attributes passing gives 100% pass rate."""
    result = _make_attribute_result()
    assert result.attribute_pass_pct == 1.0
    assert result.meets_threshold is True


def test_attribute_result_4_of_5_passes() -> None:
    """4/5 attributes = 80% = meets threshold."""
    passes = {a: True for a in ATTRIBUTES}
    passes["no_artifacts"] = False
    result = _make_attribute_result(passes)
    assert abs(result.attribute_pass_pct - 0.8) < 0.01
    assert result.meets_threshold is True


def test_attribute_result_3_of_5_fails() -> None:
    """3/5 attributes = 60% = below threshold."""
    passes = {a: True for a in ATTRIBUTES}
    passes["no_artifacts"] = False
    passes["diversity"] = False
    result = _make_attribute_result(passes)
    assert abs(result.attribute_pass_pct - 0.6) < 0.01
    assert result.meets_threshold is False


@patch("evaluate.image_evaluator._call_multimodal_eval")
def test_evaluate_image_attributes_returns_result(mock_call: MagicMock) -> None:
    """evaluate_image_attributes returns structured result from mock API."""
    mock_call.return_value = ({
        "age_appropriate": True,
        "lighting": True,
        "diversity": True,
        "brand_consistent": True,
        "no_artifacts": False,
    }, 0)
    result = evaluate_image_attributes(
        image_path="/tmp/test.png",
        visual_spec={"subject": "Student studying"},
        ad_id="ad_001",
        variant_type="anchor",
    )
    assert isinstance(result, ImageAttributeResult)
    assert result.attribute_pass_pct == 0.8
    assert result.meets_threshold is True


# --- Composite Score Tests ---


def test_composite_score_formula() -> None:
    """Composite = (attribute_pass_pct * 0.4) + (coherence_avg * 0.6)."""
    score = compute_composite_score(attribute_pass_pct=1.0, coherence_avg=0.8)
    # 1.0 * 0.4 + 0.8 * 0.6 = 0.4 + 0.48 = 0.88
    assert abs(score - 0.88) < 0.01


def test_composite_score_zero_coherence() -> None:
    """Zero coherence heavily penalizes composite."""
    score = compute_composite_score(attribute_pass_pct=1.0, coherence_avg=0.0)
    assert abs(score - 0.4) < 0.01


# --- Variant Selection Tests ---


def test_select_best_picks_highest_composite() -> None:
    """Selects variant with highest composite score."""
    variants = [
        _make_variant_result("anchor", 0.8, 0.7),
        _make_variant_result("tone_shift", 1.0, 0.9),
        _make_variant_result("composition_shift", 0.6, 0.8),
    ]
    result = select_best_variant(variants)
    assert isinstance(result, ImageSelectionResult)
    assert result.winner.variant_type == "tone_shift"


def test_select_best_tiebreak_first_wins() -> None:
    """On tie, first variant wins."""
    variants = [
        _make_variant_result("anchor", 1.0, 1.0),
        _make_variant_result("tone_shift", 1.0, 1.0),
    ]
    result = select_best_variant(variants)
    assert result.winner.variant_type == "anchor"


def test_select_best_all_fail_attributes() -> None:
    """Selection still picks best even if all fail attribute threshold."""
    variants = [
        _make_variant_result("anchor", 0.4, 0.5),
        _make_variant_result("tone_shift", 0.6, 0.5),
        _make_variant_result("composition_shift", 0.2, 0.5),
    ]
    result = select_best_variant(variants)
    assert result.winner.variant_type == "tone_shift"
    assert result.all_pass_threshold is False


def test_select_best_logs_all_variants() -> None:
    """Selection result contains all variants, not just winner."""
    variants = [
        _make_variant_result("anchor", 0.8, 0.7),
        _make_variant_result("tone_shift", 1.0, 0.9),
        _make_variant_result("composition_shift", 0.6, 0.8),
    ]
    result = select_best_variant(variants)
    assert len(result.all_variants) == 3
