"""Tests for text-image coherence checker (P1-16)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from evaluate.coherence_checker import (
    CoherenceResult,
    check_coherence,
    is_incoherent,
    all_variants_incoherent,
    COHERENCE_DIMENSIONS,
)
from evaluate.image_selector import compute_composite_score


COPY = {
    "headline": "Ace Your SAT with Expert Tutors",
    "body": "1-on-1 tutoring that builds confidence and raises scores.",
    "cta": "Start Today",
}


def _make_coherence_result(
    scores: dict[str, float] | None = None,
) -> CoherenceResult:
    """Build a CoherenceResult with given dimension scores."""
    if scores is None:
        scores = {d: 8.0 for d in COHERENCE_DIMENSIONS}
    avg = sum(scores.values()) / len(scores)
    return CoherenceResult(
        ad_id="ad_001",
        variant_type="anchor",
        dimension_scores=scores,
        coherence_avg=round(avg, 2),
    )


# --- CoherenceResult structure ---


def test_coherence_result_has_four_dimensions() -> None:
    """CoherenceResult contains exactly 4 dimension scores."""
    result = _make_coherence_result()
    assert len(result.dimension_scores) == 4
    for dim in COHERENCE_DIMENSIONS:
        assert dim in result.dimension_scores


def test_coherence_avg_is_mean_of_dimensions() -> None:
    """coherence_avg is the arithmetic mean of all 4 dimension scores."""
    scores = {
        "message_alignment": 8.0,
        "audience_match": 6.0,
        "emotional_consistency": 7.0,
        "visual_narrative": 9.0,
    }
    result = _make_coherence_result(scores)
    expected = (8.0 + 6.0 + 7.0 + 9.0) / 4
    assert abs(result.coherence_avg - expected) < 0.01


# --- Incoherence threshold ---


def test_is_incoherent_below_threshold() -> None:
    """Average below 6.0 is incoherent."""
    scores = {d: 5.0 for d in COHERENCE_DIMENSIONS}
    result = _make_coherence_result(scores)
    assert is_incoherent(result) is True


def test_is_incoherent_above_threshold() -> None:
    """Average at or above 6.0 is coherent."""
    scores = {d: 7.0 for d in COHERENCE_DIMENSIONS}
    result = _make_coherence_result(scores)
    assert is_incoherent(result) is False


def test_is_incoherent_exact_threshold() -> None:
    """Average exactly 6.0 is coherent (threshold is <6.0)."""
    scores = {d: 6.0 for d in COHERENCE_DIMENSIONS}
    result = _make_coherence_result(scores)
    assert is_incoherent(result) is False


# --- All variants incoherent ---


def test_all_variants_incoherent_when_all_fail() -> None:
    """Returns True when every variant is below threshold."""
    results = [
        _make_coherence_result({d: 4.0 for d in COHERENCE_DIMENSIONS}),
        _make_coherence_result({d: 5.0 for d in COHERENCE_DIMENSIONS}),
        _make_coherence_result({d: 3.0 for d in COHERENCE_DIMENSIONS}),
    ]
    assert all_variants_incoherent(results) is True


def test_all_variants_incoherent_false_when_one_passes() -> None:
    """Returns False when at least one variant is coherent."""
    results = [
        _make_coherence_result({d: 4.0 for d in COHERENCE_DIMENSIONS}),
        _make_coherence_result({d: 8.0 for d in COHERENCE_DIMENSIONS}),
        _make_coherence_result({d: 3.0 for d in COHERENCE_DIMENSIONS}),
    ]
    assert all_variants_incoherent(results) is False


# --- Coherence in composite score ---


def test_coherence_normalized_in_composite() -> None:
    """Coherence avg (1-10 scale) is normalized to 0-1 for composite."""
    # coherence_avg=8.0 -> normalized=0.8
    # attribute_pass_pct=1.0
    # composite = 1.0*0.4 + 0.8*0.6 = 0.4 + 0.48 = 0.88
    score = compute_composite_score(attribute_pass_pct=1.0, coherence_avg=0.8)
    assert abs(score - 0.88) < 0.01


def test_zero_coherence_penalizes_composite() -> None:
    """Zero coherence heavily penalizes composite even with perfect attributes."""
    score = compute_composite_score(attribute_pass_pct=1.0, coherence_avg=0.0)
    assert abs(score - 0.4) < 0.01


# --- API integration ---


@patch("evaluate.coherence_checker._call_coherence_eval")
def test_check_coherence_returns_result(mock_call: MagicMock) -> None:
    """check_coherence returns structured CoherenceResult from mock API."""
    mock_call.return_value = ({
        "message_alignment": 8,
        "audience_match": 7,
        "emotional_consistency": 9,
        "visual_narrative": 6,
    }, 0)
    result = check_coherence(
        copy=COPY,
        image_path="/tmp/test.png",
        ad_id="ad_001",
        variant_type="anchor",
    )
    assert isinstance(result, CoherenceResult)
    assert abs(result.coherence_avg - 7.5) < 0.01


@patch("evaluate.coherence_checker._call_coherence_eval")
def test_check_coherence_api_failure_defaults_to_mid_scores(mock_call: MagicMock) -> None:
    """On API failure, defaults to mid-range scores (5.0) rather than crashing."""
    mock_call.side_effect = RuntimeError("API error")
    result = check_coherence(
        copy=COPY,
        image_path="/tmp/test.png",
        ad_id="ad_001",
        variant_type="anchor",
    )
    assert isinstance(result, CoherenceResult)
    assert result.coherence_avg == 5.0
