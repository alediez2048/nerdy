"""Tests for competitive pattern query interface (P0-10).

TDD: Tests written first. Validates load_patterns, query_patterns,
get_competitor_summary, get_all_competitors, get_landscape_context.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from generate.competitive import (
    get_all_competitors,
    get_competitor_summary,
    get_landscape_context,
    load_patterns,
    query_patterns,
)

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
PATTERNS_PATH = DATA_DIR / "competitive" / "patterns.json"


def test_load_patterns_loads_valid_records() -> None:
    """load_patterns returns list of pattern records."""
    patterns = load_patterns(str(PATTERNS_PATH))
    assert isinstance(patterns, list)
    assert len(patterns) >= 40
    for p in patterns[:3]:
        assert "pattern_id" in p
        assert "competitor" in p
        assert "primary_audience" in p
        assert "hook_type" in p
        assert "tags" in p


def test_load_patterns_missing_file_raises() -> None:
    """load_patterns with missing file raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        load_patterns("/nonexistent/path/patterns.json")


def test_query_patterns_audience_parents() -> None:
    """query_patterns(audience='parents') returns only parent-targeted patterns."""
    results = query_patterns(audience="parents", top_n=10)
    assert len(results) <= 10
    for p in results:
        assert p["primary_audience"] in ("parents", "both")


def test_query_patterns_audience_parents_tags_returns_ranked() -> None:
    """query_patterns(audience='parents', tags=['tutoring']) returns ranked results."""
    results = query_patterns(audience="parents", tags=["tutoring"], top_n=5)
    assert len(results) <= 5
    for p in results:
        assert p["primary_audience"] in ("parents", "both")
        assert "tutoring" in p.get("tags", [])


def test_query_patterns_competitor_kaplan() -> None:
    """query_patterns(competitor='Kaplan') returns only Kaplan patterns."""
    results = query_patterns(competitor="Kaplan", top_n=20)
    for p in results:
        assert p["competitor"] == "Kaplan"


def test_query_patterns_hook_type() -> None:
    """query_patterns(hook_type='question') filters correctly."""
    results = query_patterns(hook_type="question", top_n=10)
    for p in results:
        assert p["hook_type"] == "question"


def test_query_patterns_no_filters_returns_all() -> None:
    """query_patterns() with no filters returns all records (limited by top_n)."""
    all_patterns = load_patterns(str(PATTERNS_PATH))
    results = query_patterns(top_n=1000)
    assert len(results) == len(all_patterns)


def test_query_patterns_top_n() -> None:
    """query_patterns(top_n=3) returns at most 3 results."""
    results = query_patterns(top_n=3)
    assert len(results) <= 3


def test_get_competitor_summary_returns_correct() -> None:
    """get_competitor_summary returns correct summary for known competitor."""
    summary = get_competitor_summary("Chegg")
    assert summary is not None
    assert "strategy" in summary
    assert "dominant_hooks" in summary


def test_get_competitor_summary_unknown_returns_none() -> None:
    """get_competitor_summary with unknown competitor returns None."""
    assert get_competitor_summary("UnknownBrand") is None


def test_get_all_competitors() -> None:
    """get_all_competitors returns list of all competitors."""
    competitors = get_all_competitors()
    assert isinstance(competitors, list)
    assert "Chegg" in competitors
    assert "Kaplan" in competitors
    assert "Varsity Tutors" in competitors


def test_get_landscape_context_returns_non_empty() -> None:
    """get_landscape_context returns non-empty formatted string."""
    ctx = get_landscape_context(audience="parents", campaign_goal="conversion", top_n=3)
    assert isinstance(ctx, str)
    assert len(ctx) > 50
