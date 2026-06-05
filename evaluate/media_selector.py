"""Unified media variant selection (PI-03).

Picks the highest-composite variant and produces a SelectionResult
with winner_reason (top-2 distinguishing dimensions vs. mean of losers)
and per-loser rejection_reason (worst dimension delta + rationale).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from statistics import mean
from typing import Any

from evaluate.media_quality import MediaEvaluationResult

logger = logging.getLogger(__name__)


@dataclass
class WinnerReason:
    composite_score: float
    distinguishing_dimensions: list[dict[str, Any]]


@dataclass
class RejectionReason:
    composite_delta: float
    worst_dimension: str
    worst_dimension_delta: float
    worst_dimension_rationale: str


@dataclass
class SelectionResult:
    winner: MediaEvaluationResult | None
    losers: list[MediaEvaluationResult]
    winner_reason: WinnerReason | None = None
    rejection_reasons: dict[str, RejectionReason] = field(default_factory=dict)
    all_failed: bool = False


def select_best(evaluations: list[MediaEvaluationResult]) -> SelectionResult:
    valid = [e for e in evaluations if not e.failed]
    if not valid:
        return SelectionResult(winner=None, losers=[], all_failed=True)

    winner = max(valid, key=lambda e: e.composite_score)
    losers = [e for e in valid if e is not winner]

    if losers:
        delta_by_dim = {
            dim: winner.dimensions[dim].score
            - mean(loser.dimensions[dim].score for loser in losers)
            for dim in winner.dimensions
        }
        top_dims = sorted(delta_by_dim, key=delta_by_dim.get, reverse=True)[:2]
        distinguishing = [
            {"dimension": d, "delta_vs_mean": round(delta_by_dim[d], 2)}
            for d in top_dims
        ]
    else:
        top_dims = sorted(
            winner.dimensions,
            key=lambda d: winner.dimensions[d].score,
            reverse=True,
        )[:2]
        distinguishing = [
            {
                "dimension": d,
                "absolute_score": winner.dimensions[d].score,
                "note": "only valid variant",
            }
            for d in top_dims
        ]

    winner_reason = WinnerReason(
        composite_score=winner.composite_score,
        distinguishing_dimensions=distinguishing,
    )

    rejection_reasons: dict[str, RejectionReason] = {}
    for loser in losers:
        deltas = {
            dim: loser.dimensions[dim].score - winner.dimensions[dim].score
            for dim in loser.dimensions
        }
        worst_dim = min(deltas, key=deltas.get)
        rejection_reasons[loser.variant_type] = RejectionReason(
            composite_delta=round(loser.composite_score - winner.composite_score, 2),
            worst_dimension=worst_dim,
            worst_dimension_delta=round(deltas[worst_dim], 2),
            worst_dimension_rationale=loser.dimensions[worst_dim].rationale,
        )

    logger.info(
        "Selected %s (composite=%.2f) for ad %s from %d candidates",
        winner.variant_type,
        winner.composite_score,
        winner.ad_id,
        len(valid),
    )
    return SelectionResult(
        winner=winner,
        losers=losers,
        winner_reason=winner_reason,
        rejection_reasons=rejection_reasons,
    )
