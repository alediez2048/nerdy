"""Tests for unified media selection (PI-03)."""
from __future__ import annotations

import pytest

from evaluate.media_quality import (
    DimensionScore,
    MediaEvaluationResult,
    IMAGE_DIMENSIONS,
)
from evaluate.media_selector import select_best, SelectionResult


def _eval(
    ad_id: str,
    variant: str,
    composite: float,
    dim_overrides: dict | None = None,
) -> MediaEvaluationResult:
    dim_overrides = dim_overrides or {}
    dims = {
        d["name"]: DimensionScore(
            score=int(dim_overrides.get(d["name"], 7)),
            weight=d["weight"],
            rationale=f"{d['name']} rationale",
        )
        for d in IMAGE_DIMENSIONS
    }
    return MediaEvaluationResult(
        ad_id=ad_id,
        variant_type=variant,
        media_type="image",
        media_path=f"/tmp/{variant}.png",
        model_used="gemini-2.5-flash",
        tokens_consumed=1500,
        dimensions=dims,
        penalty_gates={},
        raw_score=composite / 100.0,
        penalty_multiplier=1.0,
        composite_score=composite,
    )


def test_select_best_picks_highest_composite():
    evs = [
        _eval("a1", "anchor", 60.0),
        _eval("a1", "tone_shift", 80.0),
        _eval("a1", "comp", 55.0),
    ]
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
    evs = [
        _eval("a1", "anchor", 80.0),
        _eval("a1", "tone_shift", 50.0, {"mobile_legibility": 3}),
    ]
    result = select_best(evs)
    assert result.winner.variant_type == "anchor"
    rr = result.rejection_reasons["tone_shift"]
    assert rr.worst_dimension == "mobile_legibility"
    assert rr.composite_delta == pytest.approx(-30.0, abs=0.01)


def test_select_best_all_failed():
    evs = [
        MediaEvaluationResult(
            ad_id="a1",
            variant_type=v,
            media_type="image",
            media_path="x",
            model_used="g",
            tokens_consumed=0,
            dimensions={},
            penalty_gates={},
            raw_score=0.0,
            penalty_multiplier=0.0,
            composite_score=0.0,
            failed=True,
            failure_reason="file_not_found",
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
