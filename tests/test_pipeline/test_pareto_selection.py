"""Tests for Pareto-optimal regeneration (P1-07)."""

from __future__ import annotations

import pytest

from iterate.pareto_selection import (
    ParetoCandidate,
    filter_regressions,
    is_pareto_dominant,
    select_best,
)

DIMS = ("clarity", "value_proposition", "cta", "brand_voice", "emotional_resonance")


def _candidate(
    ad_id: str,
    variant_index: int,
    scores: dict[str, float],
    weighted_average: float | None = None,
) -> ParetoCandidate:
    """Helper to build a ParetoCandidate."""
    if weighted_average is None:
        weighted_average = sum(scores.values()) / len(scores)
    return ParetoCandidate(
        ad_id=ad_id,
        variant_index=variant_index,
        scores=scores,
        weighted_average=weighted_average,
    )


# --- is_pareto_dominant Tests ---


def test_pareto_dominant_when_best_on_all() -> None:
    """Candidate that scores highest on all dimensions is Pareto-dominant."""
    a = _candidate("a", 0, {d: 8.0 for d in DIMS})
    b = _candidate("b", 1, {d: 6.0 for d in DIMS})
    c = _candidate("c", 2, {d: 7.0 for d in DIMS})
    assert is_pareto_dominant(a, [b, c]) is True


def test_not_pareto_dominant_when_strictly_dominated() -> None:
    """Candidate is NOT dominant if another beats it on ALL dimensions."""
    weak = _candidate("weak", 0, {d: 5.0 for d in DIMS})
    strong = _candidate("strong", 1, {d: 8.0 for d in DIMS})
    assert is_pareto_dominant(weak, [strong]) is False


def test_pareto_dominant_with_mixed_scores() -> None:
    """Candidate is dominant if no other beats it on every dimension."""
    a = _candidate("a", 0, {"clarity": 9.0, "value_proposition": 7.0, "cta": 6.0, "brand_voice": 8.0, "emotional_resonance": 7.0})
    b = _candidate("b", 1, {"clarity": 7.0, "value_proposition": 9.0, "cta": 8.0, "brand_voice": 6.0, "emotional_resonance": 8.0})
    # Neither dominates the other — both are Pareto-optimal
    assert is_pareto_dominant(a, [b]) is True
    assert is_pareto_dominant(b, [a]) is True


def test_pareto_dominant_equal_scores() -> None:
    """Candidate with equal scores to all others is Pareto-dominant (not strictly dominated)."""
    a = _candidate("a", 0, {d: 7.0 for d in DIMS})
    b = _candidate("b", 1, {d: 7.0 for d in DIMS})
    assert is_pareto_dominant(a, [b]) is True


# --- filter_regressions Tests ---


def test_filter_regressions_removes_regressing_candidates() -> None:
    """Candidates that regress on any dimension vs prior are removed."""
    prior = {d: 7.0 for d in DIMS}
    good = _candidate("good", 0, {d: 7.5 for d in DIMS})
    bad = _candidate("bad", 1, {"clarity": 6.5, "value_proposition": 8.0, "cta": 8.0, "brand_voice": 8.0, "emotional_resonance": 8.0})
    result = filter_regressions([good, bad], prior)
    assert len(result) == 1
    assert result[0].ad_id == "good"


def test_filter_regressions_returns_empty_when_all_regress() -> None:
    """Returns empty list when every candidate regresses on at least one dimension."""
    prior = {d: 8.0 for d in DIMS}
    c1 = _candidate("c1", 0, {"clarity": 7.5, "value_proposition": 9.0, "cta": 9.0, "brand_voice": 9.0, "emotional_resonance": 9.0})
    c2 = _candidate("c2", 1, {"clarity": 9.0, "value_proposition": 9.0, "cta": 7.0, "brand_voice": 9.0, "emotional_resonance": 9.0})
    result = filter_regressions([c1, c2], prior)
    assert len(result) == 0


def test_filter_regressions_keeps_equal_scores() -> None:
    """Candidates with scores equal to prior are not considered regressions."""
    prior = {d: 7.0 for d in DIMS}
    equal = _candidate("equal", 0, {d: 7.0 for d in DIMS})
    result = filter_regressions([equal], prior)
    assert len(result) == 1


# --- select_best Tests ---


def test_select_best_picks_highest_weighted_among_pareto() -> None:
    """Among Pareto-dominant candidates, picks highest weighted average."""
    a = _candidate("a", 0, {"clarity": 9.0, "value_proposition": 7.0, "cta": 6.0, "brand_voice": 8.0, "emotional_resonance": 7.0}, weighted_average=7.4)
    b = _candidate("b", 1, {"clarity": 7.0, "value_proposition": 9.0, "cta": 8.0, "brand_voice": 6.0, "emotional_resonance": 8.0}, weighted_average=7.6)
    # Both are Pareto-optimal (mixed scores), b has higher weighted avg
    result = select_best([a, b], prior_scores=None)
    assert result is not None
    assert result.ad_id == "b"


def test_select_best_returns_none_when_all_regress() -> None:
    """Returns None when no non-regressing candidate exists (signals brief mutation)."""
    prior = {d: 8.0 for d in DIMS}
    c1 = _candidate("c1", 0, {"clarity": 7.5, "value_proposition": 9.0, "cta": 9.0, "brand_voice": 9.0, "emotional_resonance": 9.0})
    c2 = _candidate("c2", 1, {"clarity": 9.0, "value_proposition": 9.0, "cta": 7.0, "brand_voice": 9.0, "emotional_resonance": 9.0})
    result = select_best([c1, c2], prior_scores=prior)
    assert result is None


def test_select_best_first_cycle_skips_regression_filter() -> None:
    """First cycle (no prior_scores) skips regression filtering entirely."""
    # These would all "regress" if compared to high prior scores, but with no prior they all qualify
    c1 = _candidate("c1", 0, {d: 5.0 for d in DIMS}, weighted_average=5.0)
    c2 = _candidate("c2", 1, {d: 6.0 for d in DIMS}, weighted_average=6.0)
    result = select_best([c1, c2], prior_scores=None)
    assert result is not None
    assert result.ad_id == "c2"


def test_select_best_single_candidate_no_prior() -> None:
    """Single candidate with no prior scores is selected."""
    c = _candidate("solo", 0, {d: 7.0 for d in DIMS}, weighted_average=7.0)
    result = select_best([c], prior_scores=None)
    assert result is not None
    assert result.ad_id == "solo"


def test_select_best_empty_list_returns_none() -> None:
    """Empty candidate list returns None."""
    result = select_best([], prior_scores=None)
    assert result is None
