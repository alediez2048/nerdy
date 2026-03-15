"""Statistical Process Control for quality drift detection (P4-02, R1-Q1).

Monitors score distributions for anomalies: mean shift, trends,
and outliers. Uses ±2σ control limits.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field

from iterate.ledger import read_events

logger = logging.getLogger(__name__)


@dataclass
class SPCResult:
    """Result of an SPC check."""

    in_control: bool
    mean: float
    ucl: float  # upper control limit
    lcl: float  # lower control limit
    violations: list[str] = field(default_factory=list)


def check_spc(scores: list[float], window: int = 10) -> SPCResult:
    """Run SPC analysis on a list of scores.

    Checks for:
    - Mean shift: 3+ consecutive points all above or all below the mean
    - Trend: 5+ monotonically increasing or decreasing points
    - Outlier: any single point outside ±2σ control limits

    Args:
        scores: List of quality scores (e.g., batch averages).
        window: Number of recent scores to analyze (default 10).

    Returns:
        SPCResult with control status and any violations found.
    """
    if len(scores) < 3:
        return SPCResult(in_control=True, mean=0.0, ucl=0.0, lcl=0.0)

    recent = scores[-window:]
    mean = sum(recent) / len(recent)

    if len(recent) < 2:
        return SPCResult(in_control=True, mean=mean, ucl=mean, lcl=mean)

    variance = sum((x - mean) ** 2 for x in recent) / (len(recent) - 1)
    sigma = math.sqrt(variance) if variance > 0 else 0.001
    ucl = mean + 2 * sigma
    lcl = mean - 2 * sigma

    violations: list[str] = []

    # Check outliers
    for i, score in enumerate(recent):
        if score > ucl or score < lcl:
            violations.append(f"outlier_at_{i}: score={score:.2f} outside [{lcl:.2f}, {ucl:.2f}]")

    # Check mean shift: 3+ consecutive points below or above mean
    consecutive_below = 0
    consecutive_above = 0
    for score in recent:
        if score < mean:
            consecutive_below += 1
            consecutive_above = 0
        elif score > mean:
            consecutive_above += 1
            consecutive_below = 0
        else:
            consecutive_below = 0
            consecutive_above = 0

        if consecutive_below >= 3:
            violations.append(f"mean_shift_below: {consecutive_below} consecutive points below mean {mean:.2f}")
            break
        if consecutive_above >= 3:
            violations.append(f"mean_shift_above: {consecutive_above} consecutive points above mean {mean:.2f}")
            break

    # Check trend: 5+ monotonically increasing or decreasing
    if len(recent) >= 5:
        for start in range(len(recent) - 4):
            segment = recent[start:start + 5]
            if all(segment[i] < segment[i + 1] for i in range(4)):
                violations.append(f"trend_increasing at position {start}")
            if all(segment[i] > segment[i + 1] for i in range(4)):
                violations.append(f"trend_decreasing at position {start}")

    in_control = len(violations) == 0

    return SPCResult(
        in_control=in_control,
        mean=round(mean, 4),
        ucl=round(ucl, 4),
        lcl=round(lcl, 4),
        violations=violations,
    )


def detect_quality_drift(ledger_path: str, window: int = 10) -> SPCResult:
    """Detect quality drift from recent batch scores in the ledger.

    Reads BatchCompleted events and extracts batch_average scores.

    Args:
        ledger_path: Path to the JSONL ledger.
        window: Number of recent batches to analyze.

    Returns:
        SPCResult from the batch average scores.
    """
    events = read_events(ledger_path)
    batch_events = [e for e in events if e.get("event_type") == "BatchCompleted"]

    scores = [
        e.get("outputs", {}).get("batch_average", 0.0)
        for e in batch_events
    ]

    if not scores:
        return SPCResult(in_control=True, mean=0.0, ucl=0.0, lcl=0.0)

    return check_spc(scores, window=window)
