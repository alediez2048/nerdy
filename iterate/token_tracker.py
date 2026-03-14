"""Token attribution engine — Performance Per Token made concrete (P1-11, R1-Q7).

Tags every API call with its pipeline stage, computes cost-per-publishable-ad,
and marginal quality gain per regeneration attempt. Reads from the JSONL
ledger only — no separate storage (Pillar 5: State Is Sacred).
"""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from iterate.ledger import read_events

logger = logging.getLogger(__name__)

# Map event types to pipeline stages
_STAGE_MAP: dict[str, str] = {
    "AdGenerated": "generation",
    "BriefExpanded": "generation",
    "AdEvaluated": "evaluation",
    "AdRegenerated": "regeneration",
    "ContextDistilled": "distillation",
    "AdRouted": "routing",
    "BriefMutated": "mutation",
    "AdPublished": "publish",
    "AdDiscarded": "discard",
    "AdEscalated": "escalation",
    "BatchCompleted": "batch",
    "RatchetUpdated": "ratchet",
}


@dataclass
class TokenSummary:
    """Aggregate token metrics for dashboard consumption."""

    total_tokens: int
    by_stage: dict[str, int]
    by_model: dict[str, int]
    cost_per_published: float
    avg_marginal_gain: float
    ads_published: int
    ads_discarded: int


def get_stage_from_event(event: dict[str, Any]) -> str:
    """Map a ledger event to its pipeline stage.

    Args:
        event: A ledger event dict.

    Returns:
        Stage string (generation, evaluation, regeneration, etc.) or "other".
    """
    event_type = event.get("event_type", "")
    return _STAGE_MAP.get(event_type, "other")


def aggregate_by_stage(ledger_path: str) -> dict[str, int]:
    """Sum tokens consumed by pipeline stage.

    Args:
        ledger_path: Path to the JSONL ledger.

    Returns:
        Dict mapping stage name to total tokens consumed.
    """
    events = read_events(ledger_path)
    totals: dict[str, int] = defaultdict(int)
    for event in events:
        stage = get_stage_from_event(event)
        tokens = event.get("tokens_consumed", 0)
        totals[stage] += tokens
    return dict(totals)


def aggregate_by_model(ledger_path: str) -> dict[str, int]:
    """Sum tokens consumed by model.

    Args:
        ledger_path: Path to the JSONL ledger.

    Returns:
        Dict mapping model name to total tokens consumed.
    """
    events = read_events(ledger_path)
    totals: dict[str, int] = defaultdict(int)
    for event in events:
        model = event.get("model_used", "unknown")
        tokens = event.get("tokens_consumed", 0)
        totals[model] += tokens
    return dict(totals)


def cost_per_publishable_ad(ledger_path: str) -> float:
    """Compute tokens per published ad.

    Args:
        ledger_path: Path to the JSONL ledger.

    Returns:
        Total tokens / published ad count. Returns inf if zero published.
    """
    events = read_events(ledger_path)
    total_tokens = sum(e.get("tokens_consumed", 0) for e in events)
    published = sum(1 for e in events if e.get("event_type") == "AdPublished")

    if published == 0:
        return float("inf")

    return total_tokens / published


def marginal_quality_gain(ledger_path: str, ad_id: str) -> list[float]:
    """Compute quality delta between each regeneration cycle for an ad.

    Args:
        ledger_path: Path to the JSONL ledger.
        ad_id: The ad identifier.

    Returns:
        List of score deltas between consecutive evaluation cycles.
        Empty list if no regeneration occurred.
    """
    events = read_events(ledger_path)
    eval_events = [
        e for e in events
        if e.get("ad_id") == ad_id and e.get("event_type") == "AdEvaluated"
    ]

    # Sort by cycle number
    eval_events.sort(key=lambda e: e.get("cycle_number", 0))

    if len(eval_events) <= 1:
        return []

    scores = [
        e.get("outputs", {}).get("aggregate_score", 0.0)
        for e in eval_events
    ]

    deltas = [round(scores[i] - scores[i - 1], 2) for i in range(1, len(scores))]
    return deltas


def get_token_summary(ledger_path: str) -> TokenSummary:
    """Aggregate all token metrics into a single summary.

    Args:
        ledger_path: Path to the JSONL ledger.

    Returns:
        TokenSummary with all metrics for dashboard consumption.
    """
    events = read_events(ledger_path)

    total_tokens = sum(e.get("tokens_consumed", 0) for e in events)
    by_stage = aggregate_by_stage(ledger_path)
    by_model = aggregate_by_model(ledger_path)

    published = sum(1 for e in events if e.get("event_type") == "AdPublished")
    discarded = sum(1 for e in events if e.get("event_type") == "AdDiscarded")

    cpp = total_tokens / published if published > 0 else float("inf")

    # Compute average marginal gain across all ads with regeneration
    ad_ids = {e.get("ad_id") for e in events if e.get("event_type") == "AdEvaluated"}
    all_deltas: list[float] = []
    for aid in ad_ids:
        deltas = marginal_quality_gain(ledger_path, aid)
        all_deltas.extend(deltas)

    avg_gain = sum(all_deltas) / len(all_deltas) if all_deltas else 0.0

    return TokenSummary(
        total_tokens=total_tokens,
        by_stage=by_stage,
        by_model=by_model,
        cost_per_published=cpp,
        avg_marginal_gain=round(avg_gain, 2),
        ads_published=published,
        ads_discarded=discarded,
    )
