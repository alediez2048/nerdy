"""Tests for script-video coherence checker (P3-09).

Validates 4-dimension coherence scoring, incoherence detection,
diagnostic output, and is_coherent edge cases.
"""

from __future__ import annotations

from evaluate.video_coherence import (
    COHERENCE_DIMENSIONS,
    CoherenceDimensionScore,
    VideoCoherenceResult,
    is_coherent,
)


def _make_result(scores: dict[str, float]) -> VideoCoherenceResult:
    """Build a VideoCoherenceResult with given dimension scores."""
    dim_scores = {
        name: CoherenceDimensionScore(name=name, score=score, rationale="Test rationale")
        for name, score in scores.items()
    }
    avg = sum(scores.values()) / len(scores) if scores else 0
    return VideoCoherenceResult(
        ad_id="ad_001",
        variant_id="anchor",
        dimension_scores=dim_scores,
        coherence_avg=avg,
        is_coherent_flag=all(s >= 6.0 for s in scores.values()),
        failing_dimensions=[n for n, s in scores.items() if s < 6.0],
    )


# --- Dimension Structure ---


def test_four_dimensions_defined() -> None:
    """All 4 coherence dimensions are defined."""
    assert len(COHERENCE_DIMENSIONS) == 4


# --- Coherence Logic ---


def test_all_above_six_is_coherent() -> None:
    """All dimensions >= 6 → coherent."""
    result = _make_result({
        "message_alignment": 8.0,
        "audience_match": 7.5,
        "emotional_consistency": 7.0,
        "narrative_flow": 6.5,
    })
    assert is_coherent(result) is True


def test_one_below_six_is_incoherent() -> None:
    """One dimension < 6 → incoherent."""
    result = _make_result({
        "message_alignment": 8.0,
        "audience_match": 5.5,
        "emotional_consistency": 7.0,
        "narrative_flow": 7.0,
    })
    assert is_coherent(result) is False


def test_multiple_below_six_is_incoherent() -> None:
    """Multiple dimensions < 6 → incoherent."""
    result = _make_result({
        "message_alignment": 4.0,
        "audience_match": 3.0,
        "emotional_consistency": 7.0,
        "narrative_flow": 7.0,
    })
    assert is_coherent(result) is False
    assert len(result.failing_dimensions) == 2


def test_exactly_six_is_coherent() -> None:
    """Score of exactly 6.0 → passes (threshold is >= 6)."""
    result = _make_result({
        "message_alignment": 6.0,
        "audience_match": 6.0,
        "emotional_consistency": 6.0,
        "narrative_flow": 6.0,
    })
    assert is_coherent(result) is True


# --- Diagnostics ---


def test_failing_dimensions_identified() -> None:
    """Failing dimensions are listed with names."""
    result = _make_result({
        "message_alignment": 8.0,
        "audience_match": 4.0,
        "emotional_consistency": 7.0,
        "narrative_flow": 3.0,
    })
    assert "audience_match" in result.failing_dimensions
    assert "narrative_flow" in result.failing_dimensions
    assert "message_alignment" not in result.failing_dimensions


def test_diagnostic_rationale_populated() -> None:
    """Each dimension score has a rationale string."""
    result = _make_result({
        "message_alignment": 8.0,
        "audience_match": 7.0,
        "emotional_consistency": 7.0,
        "narrative_flow": 7.0,
    })
    for dim_score in result.dimension_scores.values():
        assert len(dim_score.rationale) > 0


# --- Coherence Average ---


def test_coherence_avg_calculation() -> None:
    """coherence_avg is the mean of all dimension scores."""
    result = _make_result({
        "message_alignment": 8.0,
        "audience_match": 6.0,
        "emotional_consistency": 7.0,
        "narrative_flow": 7.0,
    })
    assert abs(result.coherence_avg - 7.0) < 0.01
