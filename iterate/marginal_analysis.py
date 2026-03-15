"""Full marginal analysis engine — quality gain per regen per model per dimension (P4-06, R1-Q7).

Measures diminishing returns across regeneration cycles and auto-adjusts
the regeneration budget. If cycle N rarely improves by >0.2 points,
the system recommends capping at N-1 attempts.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass

from iterate.ledger import read_events

logger = logging.getLogger(__name__)

DIMENSIONS = ("clarity", "value_proposition", "cta", "brand_voice", "emotional_resonance")
DEFAULT_MIN_GAIN = 0.2


@dataclass
class MarginalGain:
    """Gain from a single regeneration cycle."""

    cycle: int
    score_before: float
    score_after: float
    gain: float
    tokens_spent: int
    gain_per_token: float


@dataclass
class RegenEfficiency:
    """Marginal analysis for a single ad."""

    ad_id: str
    gains: list[MarginalGain]
    total_tokens: int
    total_gain: float
    diminishing_at: int | None


@dataclass
class AggregateMarginals:
    """Aggregate marginal analysis across all ads."""

    avg_gain_by_cycle: dict[int, float]
    avg_tokens_by_cycle: dict[int, int]
    recommended_max_cycles: int
    by_model: dict[str, dict]
    by_dimension: dict[str, dict]


@dataclass
class DimensionMarginal:
    """Per-dimension marginal analysis."""

    dimension: str
    avg_gain_cycle_1: float
    avg_gain_cycle_2: float
    avg_gain_cycle_3: float
    most_improved_by_regen: bool


@dataclass
class RegenBudget:
    """Auto-cap recommendation."""

    max_cycles: int
    reason: str
    savings_estimate_tokens: int


def compute_marginal_gains(ledger_path: str, ad_id: str) -> RegenEfficiency:
    """Compute per-cycle marginal gains for a single ad.

    Args:
        ledger_path: Path to the JSONL ledger.
        ad_id: The ad identifier.

    Returns:
        RegenEfficiency with per-cycle gains and diminishing returns detection.
    """
    events = read_events(ledger_path)
    eval_events = [
        e for e in events
        if e.get("ad_id") == ad_id and e.get("event_type") == "AdEvaluated"
    ]
    eval_events.sort(key=lambda e: e.get("cycle_number", 0))

    if len(eval_events) <= 1:
        total_tokens = sum(e.get("tokens_consumed", 0) for e in eval_events)
        return RegenEfficiency(
            ad_id=ad_id, gains=[], total_tokens=total_tokens,
            total_gain=0.0, diminishing_at=None,
        )

    gains: list[MarginalGain] = []
    total_tokens = 0
    diminishing_at: int | None = None

    for i in range(1, len(eval_events)):
        prev_score = eval_events[i - 1].get("outputs", {}).get("aggregate_score", 0.0)
        curr_score = eval_events[i].get("outputs", {}).get("aggregate_score", 0.0)
        tokens = eval_events[i].get("tokens_consumed", 0)
        total_tokens += tokens

        gain = round(curr_score - prev_score, 4)
        gpt = round(gain / max(tokens, 1), 6)

        gains.append(MarginalGain(
            cycle=i,
            score_before=prev_score,
            score_after=curr_score,
            gain=gain,
            tokens_spent=tokens,
            gain_per_token=gpt,
        ))

        if gain < DEFAULT_MIN_GAIN and diminishing_at is None:
            diminishing_at = i

    total_gain = round(sum(g.gain for g in gains), 4)

    return RegenEfficiency(
        ad_id=ad_id,
        gains=gains,
        total_tokens=total_tokens,
        total_gain=total_gain,
        diminishing_at=diminishing_at,
    )


def compute_aggregate_marginals(ledger_path: str) -> AggregateMarginals:
    """Aggregate marginal analysis across all ads.

    Args:
        ledger_path: Path to the JSONL ledger.

    Returns:
        AggregateMarginals with per-cycle averages and recommended max cycles.
    """
    events = read_events(ledger_path)
    ad_ids = {e.get("ad_id") for e in events if e.get("event_type") == "AdEvaluated"}

    gains_by_cycle: dict[int, list[float]] = defaultdict(list)
    tokens_by_cycle: dict[int, list[int]] = defaultdict(list)
    gains_by_model: dict[str, list[float]] = defaultdict(list)

    for aid in ad_ids:
        efficiency = compute_marginal_gains(ledger_path, aid)
        for g in efficiency.gains:
            gains_by_cycle[g.cycle].append(g.gain)
            tokens_by_cycle[g.cycle].append(g.tokens_spent)

    # Per-model breakdown from raw events
    eval_events = [e for e in events if e.get("event_type") == "AdEvaluated"]
    for e in eval_events:
        model = e.get("model_used", "unknown")
        score = e.get("outputs", {}).get("aggregate_score", 0)
        gains_by_model[model].append(score)

    avg_gain = {c: round(sum(g) / len(g), 4) for c, g in gains_by_cycle.items() if g}
    avg_tokens = {c: round(sum(t) / len(t)) for c, t in tokens_by_cycle.items() if t}

    # Recommended max = highest cycle where avg gain > DEFAULT_MIN_GAIN
    recommended = 1
    for cycle in sorted(avg_gain.keys()):
        if avg_gain[cycle] >= DEFAULT_MIN_GAIN:
            recommended = cycle + 1  # +1 because cycle is 1-indexed delta
    recommended = max(1, recommended)

    return AggregateMarginals(
        avg_gain_by_cycle=avg_gain,
        avg_tokens_by_cycle=avg_tokens,
        recommended_max_cycles=recommended,
        by_model={m: {"avg_score": round(sum(s) / len(s), 2)} for m, s in gains_by_model.items()},
        by_dimension={},
    )


def compute_dimension_marginals(ledger_path: str) -> list[DimensionMarginal]:
    """Compute per-dimension marginal gains.

    Args:
        ledger_path: Path to the JSONL ledger.

    Returns:
        List of DimensionMarginal, one per dimension.
    """
    events = read_events(ledger_path)
    ad_ids = {e.get("ad_id") for e in events if e.get("event_type") == "AdEvaluated"}

    dim_gains: dict[str, dict[int, list[float]]] = {d: defaultdict(list) for d in DIMENSIONS}

    for aid in ad_ids:
        eval_events = [
            e for e in events
            if e.get("ad_id") == aid and e.get("event_type") == "AdEvaluated"
        ]
        eval_events.sort(key=lambda e: e.get("cycle_number", 0))

        for i in range(1, len(eval_events)):
            prev_scores = eval_events[i - 1].get("outputs", {}).get("scores", {})
            curr_scores = eval_events[i].get("outputs", {}).get("scores", {})
            for dim in DIMENSIONS:
                prev = prev_scores.get(dim, 0) if isinstance(prev_scores.get(dim), (int, float)) else 0
                curr = curr_scores.get(dim, 0) if isinstance(curr_scores.get(dim), (int, float)) else 0
                dim_gains[dim][i].append(curr - prev)

    results: list[DimensionMarginal] = []
    for dim in DIMENSIONS:
        c1 = dim_gains[dim].get(1, [])
        c2 = dim_gains[dim].get(2, [])
        c3 = dim_gains[dim].get(3, [])
        avg1 = round(sum(c1) / len(c1), 2) if c1 else 0.0
        avg2 = round(sum(c2) / len(c2), 2) if c2 else 0.0
        avg3 = round(sum(c3) / len(c3), 2) if c3 else 0.0

        results.append(DimensionMarginal(
            dimension=dim,
            avg_gain_cycle_1=avg1,
            avg_gain_cycle_2=avg2,
            avg_gain_cycle_3=avg3,
            most_improved_by_regen=avg1 > 0.3,
        ))

    return results


def compute_regen_budget(
    aggregate: AggregateMarginals,
    min_gain: float = DEFAULT_MIN_GAIN,
) -> RegenBudget:
    """Auto-set max regeneration cycles based on marginal analysis.

    Args:
        aggregate: Aggregate marginals from compute_aggregate_marginals.
        min_gain: Minimum gain threshold to justify a cycle.

    Returns:
        RegenBudget with recommended max_cycles and reasoning.
    """
    # Cycle keys are 1-indexed: cycle 1 = 1st regen delta, cycle 2 = 2nd, etc.
    # max_cycles = highest cycle where gain >= min_gain
    max_cycles = 1
    for cycle in sorted(aggregate.avg_gain_by_cycle.keys()):
        if aggregate.avg_gain_by_cycle[cycle] >= min_gain:
            max_cycles = max(max_cycles, cycle)

    # Estimate savings
    total_saved = 0
    for cycle in sorted(aggregate.avg_tokens_by_cycle.keys()):
        if cycle + 1 > max_cycles:
            total_saved += aggregate.avg_tokens_by_cycle.get(cycle, 0)

    dropped = [c for c in aggregate.avg_gain_by_cycle if aggregate.avg_gain_by_cycle[c] < min_gain]
    if dropped:
        reason = f"Cycles {dropped} avg gain < {min_gain} — capping at {max_cycles}"
    else:
        reason = f"All cycles have sufficient gain — keeping {max_cycles}"

    return RegenBudget(
        max_cycles=max_cycles,
        reason=reason,
        savings_estimate_tokens=total_saved,
    )


def get_marginal_dashboard_data(ledger_path: str) -> dict:
    """Generate structured data for Panel 6 (Token Economics).

    Args:
        ledger_path: Path to the JSONL ledger.

    Returns:
        Dict with gain_curve, token_spend, dimension_breakdown, recommendation.
    """
    aggregate = compute_aggregate_marginals(ledger_path)
    budget = compute_regen_budget(aggregate)
    dim_marginals = compute_dimension_marginals(ledger_path)

    return {
        "gain_curve": aggregate.avg_gain_by_cycle,
        "token_spend": aggregate.avg_tokens_by_cycle,
        "dimension_breakdown": [
            {
                "dimension": d.dimension,
                "cycle_1": d.avg_gain_cycle_1,
                "cycle_2": d.avg_gain_cycle_2,
                "cycle_3": d.avg_gain_cycle_3,
            }
            for d in dim_marginals
        ],
        "recommendation": {
            "max_cycles": budget.max_cycles,
            "reason": budget.reason,
            "savings_tokens": budget.savings_estimate_tokens,
        },
    }
