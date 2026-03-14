"""Tests for result-level cache (P1-12)."""

from __future__ import annotations


import pytest

from iterate.cache import (
    compute_cache_key,
    get_cache_stats,
    get_cached_result,
    invalidate_cache,
    store_result,
)


def _sample_result() -> dict:
    """A minimal EvaluationResult-like dict for caching."""
    return {
        "ad_id": "ad_001",
        "scores": {
            "clarity": {"score": 8.0, "rationale": "Clear"},
            "value_proposition": {"score": 7.5, "rationale": "Good"},
            "cta": {"score": 7.0, "rationale": "OK"},
            "brand_voice": {"score": 8.0, "rationale": "Strong"},
            "emotional_resonance": {"score": 7.0, "rationale": "Decent"},
        },
        "aggregate_score": 7.5,
        "meets_threshold": True,
        "weakest_dimension": "cta",
    }


# --- compute_cache_key Tests ---


def test_cache_key_deterministic() -> None:
    """Same inputs always produce same key."""
    k1 = compute_cache_key("Hello world", "v1")
    k2 = compute_cache_key("Hello world", "v1")
    assert k1 == k2


def test_cache_key_differs_on_text_change() -> None:
    """Different ad text produces different key."""
    k1 = compute_cache_key("Ad version A", "v1")
    k2 = compute_cache_key("Ad version B", "v1")
    assert k1 != k2


def test_cache_key_differs_on_version_change() -> None:
    """Different prompt version produces different key (invalidation mechanism)."""
    k1 = compute_cache_key("Same ad text", "v1")
    k2 = compute_cache_key("Same ad text", "v2")
    assert k1 != k2


# --- store_result / get_cached_result Round-Trip Tests ---


def test_store_and_retrieve_round_trip(tmp_path: pytest.TempPathFactory) -> None:
    """Store a result and retrieve it by the same key."""
    cache_path = str(tmp_path / "cache.jsonl")
    result = _sample_result()

    store_result(cache_path, "Test ad copy", "v1", result)
    cached = get_cached_result(cache_path, "Test ad copy", "v1")

    assert cached is not None
    assert cached["ad_id"] == "ad_001"
    assert cached["aggregate_score"] == 7.5


def test_cache_miss_returns_none(tmp_path: pytest.TempPathFactory) -> None:
    """Cache miss returns None, not an error."""
    cache_path = str(tmp_path / "cache.jsonl")
    # Empty cache
    cached = get_cached_result(cache_path, "Nonexistent ad", "v1")
    assert cached is None


def test_cache_miss_wrong_version(tmp_path: pytest.TempPathFactory) -> None:
    """Stored with v1, lookup with v2 returns None (version mismatch)."""
    cache_path = str(tmp_path / "cache.jsonl")
    store_result(cache_path, "Test ad", "v1", _sample_result())

    cached = get_cached_result(cache_path, "Test ad", "v2")
    assert cached is None


def test_newer_entry_overrides_older(tmp_path: pytest.TempPathFactory) -> None:
    """Last match wins in append-only cache."""
    cache_path = str(tmp_path / "cache.jsonl")
    result1 = _sample_result()
    result1["aggregate_score"] = 6.0

    result2 = _sample_result()
    result2["aggregate_score"] = 8.0

    store_result(cache_path, "Same ad", "v1", result1)
    store_result(cache_path, "Same ad", "v1", result2)

    cached = get_cached_result(cache_path, "Same ad", "v1")
    assert cached is not None
    assert cached["aggregate_score"] == 8.0


# --- invalidate_cache Tests ---


def test_invalidate_clears_all(tmp_path: pytest.TempPathFactory) -> None:
    """Invalidation clears all entries; subsequent lookup returns None."""
    cache_path = str(tmp_path / "cache.jsonl")
    store_result(cache_path, "Ad 1", "v1", _sample_result())
    store_result(cache_path, "Ad 2", "v1", _sample_result())

    count = invalidate_cache(cache_path)
    assert count == 2

    assert get_cached_result(cache_path, "Ad 1", "v1") is None
    assert get_cached_result(cache_path, "Ad 2", "v1") is None


def test_invalidate_empty_cache(tmp_path: pytest.TempPathFactory) -> None:
    """Invalidating empty/nonexistent cache returns 0, no crash."""
    cache_path = str(tmp_path / "cache.jsonl")
    count = invalidate_cache(cache_path)
    assert count == 0


# --- get_cache_stats Tests ---


def test_cache_stats_correct(tmp_path: pytest.TempPathFactory) -> None:
    """Stats return correct counts and versions."""
    cache_path = str(tmp_path / "cache.jsonl")
    store_result(cache_path, "Ad 1", "v1", _sample_result())
    store_result(cache_path, "Ad 2", "v2", _sample_result())
    store_result(cache_path, "Ad 3", "v1", _sample_result())

    stats = get_cache_stats(cache_path)
    assert stats["total_entries"] == 3
    assert set(stats["prompt_versions"]) == {"v1", "v2"}


def test_cache_stats_empty(tmp_path: pytest.TempPathFactory) -> None:
    """Stats on empty cache return zeros, no crash."""
    cache_path = str(tmp_path / "cache.jsonl")
    stats = get_cache_stats(cache_path)
    assert stats["total_entries"] == 0
    assert stats["prompt_versions"] == []
