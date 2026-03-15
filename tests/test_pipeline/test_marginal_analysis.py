"""Tests for full marginal analysis engine (P4-06).

Validates per-ad marginal gains, aggregate analysis, per-dimension
breakdown, auto-cap logic, and dashboard data generation.
"""

from __future__ import annotations

from pathlib import Path

from iterate.ledger import log_event
from iterate.marginal_analysis import (
    AggregateMarginals,
    DimensionMarginal,
    MarginalGain,
    RegenBudget,
    RegenEfficiency,
    compute_aggregate_marginals,
    compute_dimension_marginals,
    compute_marginal_gains,
    compute_regen_budget,
    get_marginal_dashboard_data,
)


def _write_regen_events(ledger_path: str, ad_id: str, scores: list[float], tokens: list[int]) -> None:
    """Write AdEvaluated events for multiple cycles."""
    for cycle, (score, tok) in enumerate(zip(scores, tokens)):
        log_event(ledger_path, {
            "event_type": "AdEvaluated",
            "ad_id": ad_id,
            "brief_id": "b001",
            "cycle_number": cycle,
            "action": "evaluation",
            "tokens_consumed": tok,
            "model_used": "gemini-2.0-flash",
            "seed": "42",
            "inputs": {},
            "outputs": {
                "aggregate_score": score,
                "scores": {
                    "clarity": score + 0.2,
                    "value_proposition": score - 0.3,
                    "cta": score,
                    "brand_voice": score + 0.1,
                    "emotional_resonance": score - 0.1,
                },
            },
        })


# --- Per-Ad Marginal Gains ---


def test_marginal_gains_computed(tmp_path: Path) -> None:
    """compute_marginal_gains returns per-cycle gains."""
    ledger_path = str(tmp_path / "ledger.jsonl")
    _write_regen_events(ledger_path, "ad_001", [6.0, 7.0, 7.3], [1000, 1000, 1000])
    result = compute_marginal_gains(ledger_path, "ad_001")
    assert isinstance(result, RegenEfficiency)
    assert len(result.gains) == 2  # 2 deltas from 3 scores
    assert isinstance(result.gains[0], MarginalGain)
    assert abs(result.gains[0].gain - 1.0) < 0.01  # 7.0 - 6.0
    assert abs(result.gains[1].gain - 0.3) < 0.01  # 7.3 - 7.0


def test_marginal_gains_no_regen(tmp_path: Path) -> None:
    """No gains when only one evaluation cycle."""
    ledger_path = str(tmp_path / "ledger.jsonl")
    _write_regen_events(ledger_path, "ad_001", [7.5], [1000])
    result = compute_marginal_gains(ledger_path, "ad_001")
    assert len(result.gains) == 0
    assert result.total_gain == 0.0


def test_diminishing_returns_detected(tmp_path: Path) -> None:
    """Diminishing returns cycle identified."""
    ledger_path = str(tmp_path / "ledger.jsonl")
    _write_regen_events(ledger_path, "ad_001", [5.0, 6.5, 6.7, 6.75], [1000, 1000, 1000, 1000])
    result = compute_marginal_gains(ledger_path, "ad_001")
    # Gains: 1.5, 0.2, 0.05 — diminishing at cycle 3 (gain 0.05 < 0.2)
    assert result.diminishing_at is not None


# --- Aggregate Analysis ---


def test_aggregate_marginals(tmp_path: Path) -> None:
    """Aggregate across multiple ads."""
    ledger_path = str(tmp_path / "ledger.jsonl")
    _write_regen_events(ledger_path, "ad_001", [6.0, 7.0, 7.2], [1000, 1000, 1000])
    _write_regen_events(ledger_path, "ad_002", [5.5, 6.8, 7.0], [1200, 1200, 1200])
    result = compute_aggregate_marginals(ledger_path)
    assert isinstance(result, AggregateMarginals)
    assert 1 in result.avg_gain_by_cycle
    assert result.recommended_max_cycles >= 1


# --- Per-Dimension Analysis ---


def test_dimension_marginals(tmp_path: Path) -> None:
    """Per-dimension marginal analysis."""
    ledger_path = str(tmp_path / "ledger.jsonl")
    _write_regen_events(ledger_path, "ad_001", [6.0, 7.0, 7.3], [1000, 1000, 1000])
    result = compute_dimension_marginals(ledger_path)
    assert isinstance(result, list)
    assert all(isinstance(d, DimensionMarginal) for d in result)
    assert len(result) == 5  # 5 dimensions


# --- Auto-Cap Logic ---


def test_auto_cap_recommends_lower(tmp_path: Path) -> None:
    """Auto-cap reduces max_cycles when later cycles have low gain."""
    aggregate = AggregateMarginals(
        avg_gain_by_cycle={1: 0.8, 2: 0.3, 3: 0.05},
        avg_tokens_by_cycle={1: 1000, 2: 1000, 3: 1000},
        recommended_max_cycles=3,
        by_model={},
        by_dimension={},
    )
    budget = compute_regen_budget(aggregate, min_gain=0.2)
    assert isinstance(budget, RegenBudget)
    assert budget.max_cycles == 2  # Cycle 3 gain (0.05) < 0.2


def test_auto_cap_keeps_all_when_gains_high() -> None:
    """Auto-cap keeps max when all cycles have sufficient gain."""
    aggregate = AggregateMarginals(
        avg_gain_by_cycle={1: 1.0, 2: 0.5, 3: 0.3},
        avg_tokens_by_cycle={1: 1000, 2: 1000, 3: 1000},
        recommended_max_cycles=3,
        by_model={},
        by_dimension={},
    )
    budget = compute_regen_budget(aggregate, min_gain=0.2)
    assert budget.max_cycles == 3


# --- Dashboard Data ---


def test_dashboard_data_structure(tmp_path: Path) -> None:
    """Dashboard data has required keys."""
    ledger_path = str(tmp_path / "ledger.jsonl")
    _write_regen_events(ledger_path, "ad_001", [6.0, 7.0, 7.3], [1000, 1000, 1000])
    data = get_marginal_dashboard_data(ledger_path)
    assert isinstance(data, dict)
    assert "gain_curve" in data
    assert "token_spend" in data
    assert "dimension_breakdown" in data
    assert "recommendation" in data
