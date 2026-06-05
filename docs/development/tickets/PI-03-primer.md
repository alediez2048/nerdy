# PI-03 Primer

**Source plan:** [`PI-PLAN.md`](PI-PLAN.md) — sliced from the ticket section below.
**Phase plan:** [`PI-00-phase-plan.md`](PI-00-phase-plan.md)

**Status:** ⏳ Not started

---

# Ticket PI-03: `media_selector.py` — winner_reason + rejection_reason

**Goal:** Build the selection module that consumes `list[MediaEvaluationResult]` and produces `SelectionResult` with winner + per-loser rejection reasoning.

**Files:**
- Create: `evaluate/media_selector.py`
- Create: `tests/test_evaluation/test_media_selector.py`

- [ ] **Step 1: Write the failing test** — create `tests/test_evaluation/test_media_selector.py`:

```python
"""Tests for unified media selection (PI-03)."""
from __future__ import annotations

import pytest

from evaluate.media_quality import (
    DimensionScore, GateEvaluation, MediaEvaluationResult, IMAGE_DIMENSIONS,
)
from evaluate.media_selector import select_best, SelectionResult


def _eval(ad_id: str, variant: str, composite: float, dim_overrides: dict | None = None) -> MediaEvaluationResult:
    dim_overrides = dim_overrides or {}
    dims = {
        d["name"]: DimensionScore(
            score=int(dim_overrides.get(d["name"], 7)),
            weight=d["weight"], rationale=f"{d['name']} rationale",
        )
        for d in IMAGE_DIMENSIONS
    }
    return MediaEvaluationResult(
        ad_id=ad_id, variant_type=variant, media_type="image",
        media_path=f"/tmp/{variant}.png", model_used="gemini-2.5-flash",
        tokens_consumed=1500, dimensions=dims, penalty_gates={},
        raw_score=composite / 100.0, penalty_multiplier=1.0,
        composite_score=composite,
    )


def test_select_best_picks_highest_composite():
    evs = [_eval("a1", "anchor", 60.0), _eval("a1", "tone_shift", 80.0), _eval("a1", "comp", 55.0)]
    result = select_best(evs)
    assert isinstance(result, SelectionResult)
    assert result.winner.variant_type == "tone_shift"
    assert not result.all_failed


def test_select_best_winner_reason_names_top_two_distinguishing_dims():
    """Winner's top 2 dimensions vs. mean of losers."""
    losers_dims = {"thumb_stop_potential": 4, "emotional_impact": 5}
    winner_dims = {"thumb_stop_potential": 9, "emotional_impact": 9}
    evs = [
        _eval("a1", "anchor", 50.0, losers_dims),
        _eval("a1", "tone_shift", 90.0, winner_dims),
        _eval("a1", "comp", 50.0, losers_dims),
    ]
    result = select_best(evs)
    dims_named = {d["dimension"] for d in result.winner_reason.distinguishing_dimensions}
    assert "thumb_stop_potential" in dims_named
    assert "emotional_impact" in dims_named


def test_select_best_rejection_reasons_per_loser():
    evs = [_eval("a1", "anchor", 80.0), _eval("a1", "tone_shift", 50.0, {"mobile_legibility": 3})]
    result = select_best(evs)
    assert result.winner.variant_type == "anchor"
    rr = result.rejection_reasons["tone_shift"]
    assert rr.worst_dimension == "mobile_legibility"
    assert rr.composite_delta == pytest.approx(-30.0, abs=0.01)


def test_select_best_all_failed():
    evs = [
        MediaEvaluationResult(
            ad_id="a1", variant_type=v, media_type="image", media_path="x",
            model_used="g", tokens_consumed=0, dimensions={}, penalty_gates={},
            raw_score=0.0, penalty_multiplier=0.0, composite_score=0.0,
            failed=True, failure_reason="file_not_found",
        )
        for v in ("anchor", "tone_shift", "comp")
    ]
    result = select_best(evs)
    assert result.all_failed is True
    assert result.winner is None


def test_select_best_single_variant_uses_absolute_top_dims():
    """When only one valid variant exists, distinguishing dims come from its top-2 absolute scores."""
    high = {"thumb_stop_potential": 10, "emotional_impact": 9}
    evs = [_eval("a1", "anchor", 90.0, high)]
    result = select_best(evs)
    assert result.winner.variant_type == "anchor"
    dims_named = {d["dimension"] for d in result.winner_reason.distinguishing_dimensions}
    assert dims_named == {"thumb_stop_potential", "emotional_impact"}
```

- [ ] **Step 2: Run, expect ImportError fail**

```
.venv/bin/python -m pytest tests/test_evaluation/test_media_selector.py -v
```

Expected: FAIL with `ImportError`.

- [ ] **Step 3: Create `evaluate/media_selector.py`**

```python
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

    # winner_reason: top 2 distinguishing dimensions. If only 1 variant, use winner's own top-2.
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
            winner.dimensions, key=lambda d: winner.dimensions[d].score, reverse=True
        )[:2]
        distinguishing = [
            {"dimension": d, "absolute_score": winner.dimensions[d].score,
             "note": "only valid variant"}
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
        winner.variant_type, winner.composite_score, winner.ad_id, len(valid),
    )
    return SelectionResult(
        winner=winner, losers=losers,
        winner_reason=winner_reason, rejection_reasons=rejection_reasons,
    )
```

- [ ] **Step 4: Run, expect all tests pass**

```
.venv/bin/python -m pytest tests/test_evaluation/test_media_selector.py -v
```

Expected: 5/5 PASS.

- [ ] **Step 5: Commit**

```
git add evaluate/media_selector.py tests/test_evaluation/test_media_selector.py
git commit -m "feat(PI-03): media_selector — SelectionResult with winner/rejection reasons"
```

---
