"""Style experiment runner and aggregation (P3-04).

Runs style experiments per ad/audience, evaluates each style, and
aggregates results to identify best style per audience segment.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass

from iterate.ledger import read_events_filtered

logger = logging.getLogger(__name__)


@dataclass
class StyleExperimentResult:
    """Result of running a style experiment for one ad."""

    ad_id: str
    audience: str
    style_results: dict[str, dict]
    best_style: str
    worst_style: str


def aggregate_style_results(ledger_path: str) -> dict[str, dict[str, float]]:
    """Aggregate style experiment results per audience per style.

    Args:
        ledger_path: Path to the JSONL ledger.

    Returns:
        Dict of {audience: {style: avg_composite_score}}.
    """
    events = read_events_filtered(ledger_path, event_type="StyleExperiment")

    if not events:
        return {}

    # Collect scores: {audience: {style: [scores]}}
    scores: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))

    for event in events:
        audience = event.get("inputs", {}).get("audience", "unknown")
        style_results = event.get("outputs", {}).get("style_results", {})
        for style_name, result in style_results.items():
            composite = result.get("composite_score", 0.0)
            scores[audience][style_name].append(composite)

    # Compute averages
    averages: dict[str, dict[str, float]] = {}
    for audience, style_scores in scores.items():
        averages[audience] = {
            style: sum(vals) / len(vals)
            for style, vals in style_scores.items()
            if vals
        }

    return averages
