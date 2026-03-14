"""Pareto-optimal regeneration — prevent dimension collapse (P1-07, R1-Q5).

Generates multiple variants per regeneration cycle and selects the
Pareto-dominant variant: the one where no other variant scores strictly
higher on every dimension. If all variants regress on at least one
dimension vs. the prior cycle, returns None to signal brief mutation (P1-08).

Variant count is config-driven via `pareto_variants` in data/config.yaml.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

DIMENSIONS = (
    "clarity",
    "value_proposition",
    "cta",
    "brand_voice",
    "emotional_resonance",
)


@dataclass
class ParetoCandidate:
    """A single ad variant with its evaluation scores."""

    ad_id: str
    variant_index: int
    scores: dict[str, float]
    weighted_average: float
    ad_content: dict[str, Any] = field(default_factory=dict)


def is_pareto_dominant(
    candidate: ParetoCandidate, others: list[ParetoCandidate]
) -> bool:
    """Check if candidate is Pareto-dominant within the set.

    A candidate is Pareto-dominant if no other candidate scores strictly
    higher on ALL dimensions. In other words, for every other candidate,
    there must be at least one dimension where this candidate scores
    equal or higher.

    Args:
        candidate: The candidate to check.
        others: The other candidates to compare against.

    Returns:
        True if no other candidate strictly dominates this one.
    """
    for other in others:
        if other.ad_id == candidate.ad_id:
            continue
        # Check if 'other' strictly dominates 'candidate'
        # (other is better on ALL dimensions)
        all_better = all(
            other.scores.get(d, 0) > candidate.scores.get(d, 0)
            for d in DIMENSIONS
        )
        if all_better:
            return False
    return True


def filter_regressions(
    candidates: list[ParetoCandidate], prior_scores: dict[str, float]
) -> list[ParetoCandidate]:
    """Remove candidates that regress on any dimension vs. prior cycle.

    A regression is when a candidate's score on any dimension is strictly
    less than the prior cycle's score for that dimension.

    Args:
        candidates: List of candidates to filter.
        prior_scores: Dict mapping dimension name to prior cycle's score.

    Returns:
        Filtered list with only non-regressing candidates.
        Empty list if all candidates regress (signals brief mutation needed).
    """
    non_regressing: list[ParetoCandidate] = []
    for c in candidates:
        regresses = any(
            c.scores.get(d, 0) < prior_scores.get(d, 0)
            for d in DIMENSIONS
        )
        if not regresses:
            non_regressing.append(c)
        else:
            regressed_dims = [
                d for d in DIMENSIONS
                if c.scores.get(d, 0) < prior_scores.get(d, 0)
            ]
            logger.debug(
                "Candidate %s regresses on: %s", c.ad_id, regressed_dims
            )
    if not non_regressing:
        logger.warning(
            "All %d candidates regress vs prior — brief mutation needed",
            len(candidates),
        )
    return non_regressing


def select_best(
    candidates: list[ParetoCandidate],
    prior_scores: dict[str, float] | None = None,
) -> ParetoCandidate | None:
    """Select the best Pareto-dominant, non-regressing candidate.

    1. If prior_scores provided, filter out regressions.
    2. Find Pareto-dominant candidates from remaining set.
    3. Among Pareto-dominant, pick highest weighted average.
    4. Return None if no valid candidate (triggers P1-08 brief mutation).

    Args:
        candidates: List of evaluated candidates.
        prior_scores: Prior cycle's dimension scores (None for first cycle).

    Returns:
        Best candidate, or None if no valid candidate exists.
    """
    if not candidates:
        return None

    # Step 1: Filter regressions (skip on first cycle)
    pool = candidates
    if prior_scores is not None:
        pool = filter_regressions(candidates, prior_scores)
        if not pool:
            return None

    # Step 2: Find Pareto-dominant candidates
    pareto_set = [c for c in pool if is_pareto_dominant(c, pool)]

    if not pareto_set:
        # Fallback: if no candidate is Pareto-dominant (shouldn't happen
        # with valid data), use the full pool
        pareto_set = pool

    # Step 3: Pick highest weighted average
    best = max(pareto_set, key=lambda c: c.weighted_average)

    logger.info(
        "Selected %s (variant %d, weighted_avg=%.2f) from %d candidates "
        "(%d Pareto-dominant)",
        best.ad_id,
        best.variant_index,
        best.weighted_average,
        len(candidates),
        len(pareto_set),
    )
    return best
