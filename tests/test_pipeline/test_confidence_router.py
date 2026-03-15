"""Tests for confidence-gated autonomy routing (P2-05)."""

from __future__ import annotations

from pathlib import Path

from evaluate.confidence_router import (
    AUTONOMOUS,
    BRAND_SAFETY_STOP,
    FLAGGED,
    HUMAN_REQUIRED,
    ConfidenceRoutingResult,
    ConfidenceStats,
    get_confidence_stats,
    route_by_confidence,
)
from evaluate.evaluator import EvaluationResult


def _make_result(
    scores: dict[str, dict] | None = None,
    confidence_flags: dict[str, float] | None = None,
) -> EvaluationResult:
    """Build an EvaluationResult with specified scores and confidence."""
    default_scores = {
        "clarity": {"score": 7.5, "rationale": "", "contrastive": "", "confidence": 8},
        "value_proposition": {"score": 7.0, "rationale": "", "contrastive": "", "confidence": 8},
        "cta": {"score": 7.5, "rationale": "", "contrastive": "", "confidence": 8},
        "brand_voice": {"score": 7.0, "rationale": "", "contrastive": "", "confidence": 8},
        "emotional_resonance": {"score": 7.0, "rationale": "", "contrastive": "", "confidence": 8},
    }
    if scores:
        for dim, overrides in scores.items():
            default_scores[dim].update(overrides)

    return EvaluationResult(
        ad_id="test_001",
        scores=default_scores,
        aggregate_score=7.2,
        campaign_goal="conversion",
        meets_threshold=True,
        weakest_dimension="emotional_resonance",
        flags=[],
        confidence_flags=confidence_flags or {},
    )


# --- Routing Level Tests ---


def test_high_confidence_autonomous() -> None:
    """All dimensions confidence > 7 routes to autonomous."""
    result = _make_result()  # all confidence = 8
    routing = route_by_confidence(result)
    assert isinstance(routing, ConfidenceRoutingResult)
    assert routing.confidence_level == AUTONOMOUS


def test_medium_confidence_flagged() -> None:
    """Min confidence 5.5 routes to flagged."""
    result = _make_result(
        scores={"brand_voice": {"confidence": 5.5}},
        confidence_flags={"brand_voice": 5.5},
    )
    routing = route_by_confidence(result)
    assert routing.confidence_level == FLAGGED
    assert "brand_voice" in routing.low_confidence_dimensions


def test_low_confidence_human_required() -> None:
    """Min confidence 3.0 routes to human required."""
    result = _make_result(
        scores={"clarity": {"confidence": 3.0}},
        confidence_flags={"clarity": 3.0},
    )
    routing = route_by_confidence(result)
    assert routing.confidence_level == HUMAN_REQUIRED
    assert "clarity" in routing.low_confidence_dimensions


def test_brand_safety_stop_on_low_score() -> None:
    """Any dimension score < 4.0 triggers brand safety stop."""
    result = _make_result(
        scores={"brand_voice": {"score": 3.0, "confidence": 8}},
    )
    routing = route_by_confidence(result)
    assert routing.confidence_level == BRAND_SAFETY_STOP
    assert routing.brand_safety_triggered is True


def test_brand_safety_overrides_high_confidence() -> None:
    """Even with confidence 10, score < 4.0 triggers brand safety."""
    result = _make_result(
        scores={"cta": {"score": 2.5, "confidence": 10}},
    )
    routing = route_by_confidence(result)
    assert routing.confidence_level == BRAND_SAFETY_STOP


# --- Integration with Score-Based Routing ---


def test_publish_downgraded_to_flagged() -> None:
    """Score-based publish + low confidence → confidence level is FLAGGED."""
    result = _make_result(
        scores={"emotional_resonance": {"confidence": 6.0}},
        confidence_flags={"emotional_resonance": 6.0},
    )
    # meets_threshold=True (would publish), but confidence is low
    routing = route_by_confidence(result)
    assert routing.confidence_level == FLAGGED


def test_discard_not_upgraded() -> None:
    """Score-based discard stays discard — confidence doesn't upgrade decisions."""
    result = _make_result()
    result.meets_threshold = False
    result.aggregate_score = 5.0
    # High confidence doesn't override low scores
    routing = route_by_confidence(result)
    # Confidence routing is independent — it reports confidence level
    # The caller combines score routing + confidence routing
    assert routing.confidence_level == AUTONOMOUS  # confidence is fine
    # But meets_threshold is still False — caller uses both signals


def test_confidence_from_evaluation_result() -> None:
    """Correctly extracts confidence from real EvaluationResult structure."""
    result = _make_result(
        scores={
            "clarity": {"confidence": 9},
            "value_proposition": {"confidence": 8},
            "cta": {"confidence": 6},
            "brand_voice": {"confidence": 7},
            "emotional_resonance": {"confidence": 5},
        },
        confidence_flags={"cta": 6.0, "emotional_resonance": 5.0},
    )
    routing = route_by_confidence(result)
    assert routing.min_confidence == 5.0
    assert "emotional_resonance" in routing.low_confidence_dimensions
    assert "cta" in routing.low_confidence_dimensions


# --- Stats ---


def test_confidence_stats_aggregation(tmp_path: Path) -> None:
    """Stats correctly count each routing level."""
    from iterate.ledger import log_event

    ledger_path = str(tmp_path / "ledger.jsonl")
    levels = ["autonomous", "autonomous", "flagged", "human_required", "brand_safety_stop"]
    for i, level in enumerate(levels):
        log_event(ledger_path, {
            "event_type": "ConfidenceRouted",
            "ad_id": f"ad_{i:03d}",
            "brief_id": "b001",
            "cycle_number": 1,
            "action": "confidence-routing",
            "inputs": {},
            "outputs": {"confidence_level": level},
            "scores": {},
            "tokens_consumed": 0,
            "model_used": "gemini-2.0-flash",
            "seed": "42",
        })

    stats = get_confidence_stats(ledger_path)
    assert isinstance(stats, ConfidenceStats)
    assert stats.autonomous_count == 2
    assert stats.flagged_count == 1
    assert stats.human_required_count == 1
    assert stats.brand_safety_count == 1
    assert stats.total == 5
    assert abs(stats.autonomous_pct - 40.0) < 0.1
