"""Quality ratchet — monotonically increasing publish threshold (P1-10, R1-Q9).

Formula: effective_threshold = max(7.0, rolling_N_batch_avg - buffer)
Monotonic enforcement: new threshold = max(old threshold, computed threshold)

The ratchet ensures quality standards never decrease. Once the system
achieves high-quality output, it refuses to regress. Config-driven via
ratchet_window and ratchet_buffer in data/config.yaml.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from iterate.ledger import read_events

logger = logging.getLogger(__name__)

_BASE_THRESHOLD = 7.0
_DEFAULT_WINDOW = 5
_DEFAULT_BUFFER = 0.5


@dataclass
class RatchetState:
    """Current state of the quality ratchet."""

    current_threshold: float
    base_threshold: float
    rolling_average: float
    window_scores: list[float]
    history: list[dict[str, Any]] = field(default_factory=list)


def compute_threshold(batch_averages: list[float], config: dict[str, Any]) -> float:
    """Compute the effective threshold from batch history.

    Formula: max(base_threshold, rolling_window_avg - buffer)

    Args:
        batch_averages: List of batch average scores.
        config: Config dict with ratchet_window, ratchet_buffer, quality_threshold.

    Returns:
        Effective threshold (>= base_threshold).
    """
    base = config.get("quality_threshold", _BASE_THRESHOLD)
    window = config.get("ratchet_window", _DEFAULT_WINDOW)
    buffer = config.get("ratchet_buffer", _DEFAULT_BUFFER)

    if not batch_averages:
        return base

    # Use last N batches (or all if fewer)
    windowed = batch_averages[-window:]
    rolling_avg = sum(windowed) / len(windowed)

    return max(base, round(rolling_avg - buffer, 2))


def update_ratchet(
    state: RatchetState,
    new_batch_avg: float,
    config: dict[str, Any],
) -> RatchetState:
    """Update the ratchet with a new batch average.

    Monotonic enforcement: new threshold = max(old threshold, computed threshold).

    Args:
        state: Current ratchet state.
        new_batch_avg: Average score of the latest batch.
        config: Config dict with ratchet_window, ratchet_buffer.

    Returns:
        Updated RatchetState with monotonically non-decreasing threshold.
    """
    window = config.get("ratchet_window", _DEFAULT_WINDOW)

    # Append and trim window
    new_window = list(state.window_scores) + [new_batch_avg]
    if len(new_window) > window:
        new_window = new_window[-window:]

    # Compute new threshold
    computed = compute_threshold(new_window, config)

    # Monotonic enforcement — never decrease
    new_threshold = max(state.current_threshold, computed)

    rolling_avg = sum(new_window) / len(new_window)

    # Record history entry
    history_entry = {
        "batch_index": len(state.history) + 1,
        "batch_avg": new_batch_avg,
        "threshold": new_threshold,
        "rolling_average": round(rolling_avg, 2),
    }
    new_history = list(state.history) + [history_entry]

    logger.info(
        "Ratchet updated: batch_avg=%.2f, threshold=%.2f→%.2f (rolling=%.2f)",
        new_batch_avg,
        state.current_threshold,
        new_threshold,
        rolling_avg,
    )

    return RatchetState(
        current_threshold=new_threshold,
        base_threshold=state.base_threshold,
        rolling_average=round(rolling_avg, 2),
        window_scores=new_window,
        history=new_history,
    )


def meets_threshold(score: float, state: RatchetState) -> bool:
    """Check if a score meets the current ratcheted threshold.

    Args:
        score: The ad's weighted average score.
        state: Current ratchet state.

    Returns:
        True if score >= current_threshold.
    """
    return score >= state.current_threshold


def get_ratchet_state(ledger_path: str, config: dict[str, Any]) -> RatchetState:
    """Reconstruct ratchet state from ledger history.

    Reads all BatchCompleted events, extracts batch averages, and replays
    threshold computation to restore the ratchet to its correct position.

    Args:
        ledger_path: Path to the JSONL ledger.
        config: Config dict with ratchet parameters.

    Returns:
        RatchetState reconstructed from ledger.
    """
    base = config.get("quality_threshold", _BASE_THRESHOLD)
    events = read_events(ledger_path)
    batch_events = [e for e in events if e.get("event_type") == "BatchCompleted"]

    state = RatchetState(
        current_threshold=base,
        base_threshold=base,
        rolling_average=0.0,
        window_scores=[],
        history=[],
    )

    for event in batch_events:
        batch_avg = event.get("outputs", {}).get("batch_average", 0.0)
        state = update_ratchet(state, batch_avg, config)

    logger.info(
        "Reconstructed ratchet from %d batches: threshold=%.2f",
        len(batch_events),
        state.current_threshold,
    )

    return state


def get_ratchet_history(state: RatchetState) -> list[dict[str, Any]]:
    """Return time-series data for visualization.

    Args:
        state: Current ratchet state with history.

    Returns:
        List of dicts with batch_index, batch_avg, threshold — suitable for plotting.
    """
    return list(state.history)
