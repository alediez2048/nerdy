"""Tests for quality ratchet — monotonically increasing threshold (P1-10)."""

from __future__ import annotations

import json

import pytest

from iterate.quality_ratchet import (
    RatchetState,
    compute_threshold,
    get_ratchet_history,
    get_ratchet_state,
    meets_threshold,
    update_ratchet,
)


def _make_config(window: int = 5, buffer: float = 0.5) -> dict:
    return {
        "ratchet_window": window,
        "ratchet_buffer": buffer,
        "quality_threshold": 7.0,
        "ledger_path": "data/ledger.jsonl",
    }


# --- compute_threshold Tests ---


def test_compute_threshold_no_batches_returns_base() -> None:
    """No batch history returns base threshold of 7.0."""
    config = _make_config()
    result = compute_threshold([], config)
    assert result == 7.0


def test_compute_threshold_below_window_uses_all() -> None:
    """Fewer batches than window size uses all available."""
    config = _make_config(window=5)
    # 2 batches averaging 8.0 → max(7.0, 8.0 - 0.5) = 7.5
    result = compute_threshold([8.0, 8.0], config)
    assert abs(result - 7.5) < 0.01


def test_compute_threshold_formula_correct() -> None:
    """max(7.0, rolling_avg - buffer) computed correctly."""
    config = _make_config(window=5, buffer=0.5)
    # 5 batches averaging 8.2 → max(7.0, 8.2 - 0.5) = 7.7
    batches = [8.0, 8.2, 8.4, 8.0, 8.4]
    result = compute_threshold(batches, config)
    expected = max(7.0, sum(batches) / len(batches) - 0.5)
    assert abs(result - expected) < 0.01


def test_compute_threshold_low_avg_returns_base() -> None:
    """When rolling avg - buffer < 7.0, returns base threshold."""
    config = _make_config(window=5, buffer=0.5)
    # avg 7.3 - 0.5 = 6.8 < 7.0 → returns 7.0
    batches = [7.2, 7.4, 7.3, 7.2, 7.4]
    result = compute_threshold(batches, config)
    assert result == 7.0


def test_compute_threshold_trims_to_window() -> None:
    """Only last N batches are used when more than window size."""
    config = _make_config(window=3, buffer=0.5)
    # 5 batches, window=3: use last 3 [9.0, 9.0, 9.0] → avg 9.0 → max(7.0, 8.5) = 8.5
    batches = [7.0, 7.0, 9.0, 9.0, 9.0]
    result = compute_threshold(batches, config)
    expected = max(7.0, 9.0 - 0.5)
    assert abs(result - expected) < 0.01


# --- update_ratchet Tests ---


def test_update_ratchet_monotonic_never_decreases() -> None:
    """Threshold never decreases even when batch averages decline."""
    config = _make_config(window=3, buffer=0.5)
    state = RatchetState(
        current_threshold=8.0,
        base_threshold=7.0,
        rolling_average=8.5,
        window_scores=[8.5, 8.5, 8.5],
        history=[],
    )
    # New batch avg of 7.0 would compute max(7.0, (8.5+8.5+7.0)/3 - 0.5) = 7.5
    # But monotonic enforcement keeps it at 8.0
    new_state = update_ratchet(state, 7.0, config)
    assert new_state.current_threshold == 8.0


def test_update_ratchet_ratchets_up() -> None:
    """Improving batch averages push threshold higher."""
    config = _make_config(window=3, buffer=0.5)
    state = RatchetState(
        current_threshold=7.0,
        base_threshold=7.0,
        rolling_average=7.5,
        window_scores=[7.5],
        history=[],
    )
    # New batch avg 9.0 → window [7.5, 9.0] → avg 8.25 → max(7.0, 7.75) = 7.75
    # max(current 7.0, computed 7.75) = 7.75
    new_state = update_ratchet(state, 9.0, config)
    assert new_state.current_threshold > 7.0


def test_update_ratchet_trims_window() -> None:
    """Window trims to ratchet_window size (FIFO)."""
    config = _make_config(window=3)
    state = RatchetState(
        current_threshold=7.0,
        base_threshold=7.0,
        rolling_average=7.5,
        window_scores=[7.5, 7.5, 7.5],
        history=[],
    )
    new_state = update_ratchet(state, 8.0, config)
    assert len(new_state.window_scores) == 3  # trimmed to window size


# --- meets_threshold Tests ---


def test_meets_threshold_above() -> None:
    """Score above threshold passes."""
    state = RatchetState(current_threshold=7.5, base_threshold=7.0, rolling_average=8.0, window_scores=[], history=[])
    assert meets_threshold(8.0, state) is True


def test_meets_threshold_below() -> None:
    """Score below threshold fails."""
    state = RatchetState(current_threshold=7.5, base_threshold=7.0, rolling_average=8.0, window_scores=[], history=[])
    assert meets_threshold(7.0, state) is False


def test_meets_threshold_exact() -> None:
    """Score exactly at threshold passes."""
    state = RatchetState(current_threshold=7.5, base_threshold=7.0, rolling_average=8.0, window_scores=[], history=[])
    assert meets_threshold(7.5, state) is True


# --- get_ratchet_state Tests ---


def test_get_ratchet_state_from_ledger(tmp_path: pytest.TempPathFactory) -> None:
    """Reconstructs ratchet state from ledger batch events."""
    ledger = str(tmp_path / "ledger.jsonl")
    events = [
        {
            "event_type": "BatchCompleted",
            "ad_id": "batch",
            "brief_id": "batch",
            "cycle_number": 0,
            "action": "batch-complete",
            "tokens_consumed": 0,
            "model_used": "none",
            "seed": "0",
            "outputs": {"batch_average": 7.8},
        },
        {
            "event_type": "BatchCompleted",
            "ad_id": "batch",
            "brief_id": "batch",
            "cycle_number": 0,
            "action": "batch-complete",
            "tokens_consumed": 0,
            "model_used": "none",
            "seed": "0",
            "outputs": {"batch_average": 8.2},
        },
    ]
    with open(ledger, "w") as f:
        for e in events:
            f.write(json.dumps(e) + "\n")

    config = _make_config(window=5, buffer=0.5)
    state = get_ratchet_state(ledger, config)
    assert len(state.window_scores) == 2
    assert state.current_threshold >= 7.0


# --- get_ratchet_history Tests ---


def test_ratchet_history_plottable() -> None:
    """History produces time-series data suitable for plotting."""
    config = _make_config(window=3, buffer=0.5)
    state = RatchetState(
        current_threshold=7.0,
        base_threshold=7.0,
        rolling_average=0.0,
        window_scores=[],
        history=[],
    )
    # Simulate 4 batch updates
    for avg in [7.5, 8.0, 8.5, 7.8]:
        state = update_ratchet(state, avg, config)

    history = get_ratchet_history(state)
    assert len(history) == 4
    for entry in history:
        assert "batch_index" in entry
        assert "batch_avg" in entry
        assert "threshold" in entry

    # Thresholds should be monotonically non-decreasing
    thresholds = [h["threshold"] for h in history]
    for i in range(1, len(thresholds)):
        assert thresholds[i] >= thresholds[i - 1]
