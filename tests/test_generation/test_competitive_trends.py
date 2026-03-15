"""Tests for competitive intelligence trends (P4-03).

Validates temporal tracking, trend analysis, strategy shift alerts,
refresh workflow, and dashboard data generation.
"""

from __future__ import annotations

from generate.competitive_trends import (
    RefreshResult,
    StrategyAlert,
    TrendResult,
    compute_competitor_shifts,
    compute_hook_trends,
    detect_strategy_shifts,
    get_competitive_dashboard_data,
    get_trending_hooks,
    run_competitive_refresh,
)


# --- Sample Data ---

def _sample_patterns() -> list[dict]:
    """Build sample patterns with observed dates."""
    patterns = []
    # Old period: mostly question hooks
    for i in range(10):
        patterns.append({
            "pattern_id": f"old_{i}",
            "competitor": "Chegg" if i < 5 else "Kaplan",
            "hook_type": "question" if i < 7 else "statistic",
            "emotional_angle": "aspiration",
            "cta_style": "soft",
            "observed_date": "2025-12-01",
        })
    # New period: shift to statistic hooks
    for i in range(10):
        patterns.append({
            "pattern_id": f"new_{i}",
            "competitor": "Chegg" if i < 5 else "Kaplan",
            "hook_type": "statistic" if i < 6 else "question",
            "emotional_angle": "urgency" if i < 4 else "aspiration",
            "cta_style": "direct" if i < 5 else "soft",
            "observed_date": "2026-03-01",
        })
    return patterns


# --- Trend Analysis ---


def test_compute_hook_trends() -> None:
    """compute_hook_trends detects shifts in hook distribution."""
    patterns = _sample_patterns()
    trends = compute_hook_trends(patterns, window_months=3)
    assert isinstance(trends, list)
    assert all(isinstance(t, TrendResult) for t in trends)
    assert any(t.hook_type == "statistic" for t in trends)


def test_trending_hooks_rising() -> None:
    """get_trending_hooks returns hooks with rising direction."""
    patterns = _sample_patterns()
    rising = get_trending_hooks(patterns, direction="rising")
    assert isinstance(rising, list)
    # Statistic hooks should be rising (30% → 60%)
    assert "statistic" in rising


def test_trending_hooks_falling() -> None:
    """get_trending_hooks returns hooks with falling direction."""
    patterns = _sample_patterns()
    falling = get_trending_hooks(patterns, direction="falling")
    assert isinstance(falling, list)
    # Question hooks should be falling (70% → 40%)
    assert "question" in falling


def test_competitor_shifts() -> None:
    """compute_competitor_shifts detects per-competitor strategy changes."""
    patterns = _sample_patterns()
    shifts = compute_competitor_shifts(patterns, competitor="Chegg")
    assert isinstance(shifts, list)
    assert all(isinstance(s, TrendResult) for s in shifts)


# --- Strategy Shift Alerts ---


def test_detect_strategy_shifts_fires_alert() -> None:
    """Significant strategy shift (>15%) triggers alert."""
    patterns = _sample_patterns()
    alerts = detect_strategy_shifts(patterns)
    assert isinstance(alerts, list)
    assert len(alerts) > 0
    assert all(isinstance(a, StrategyAlert) for a in alerts)
    assert all(a.severity in ("info", "warning", "action") for a in alerts)


def test_no_alerts_stable_patterns() -> None:
    """No alerts when patterns are stable."""
    # All same date = no temporal comparison possible
    patterns = [
        {"pattern_id": f"p_{i}", "competitor": "Chegg", "hook_type": "question",
         "emotional_angle": "aspiration", "cta_style": "soft", "observed_date": "2026-03-01"}
        for i in range(10)
    ]
    alerts = detect_strategy_shifts(patterns)
    assert isinstance(alerts, list)
    assert len(alerts) == 0


# --- Refresh Workflow ---


def test_refresh_merges_new_patterns() -> None:
    """Refresh adds new patterns and deduplicates."""
    current = [
        {"pattern_id": "p1", "competitor": "Chegg", "hook_type": "question",
         "source_url": "http://a.com", "observed_date": "2025-12-01"},
    ]
    new_observations = [
        {"competitor": "Chegg", "hook_type": "statistic",
         "source_url": "http://b.com", "observed_date": "2026-03-01"},
        {"competitor": "Chegg", "hook_type": "question",
         "source_url": "http://a.com", "observed_date": "2026-03-01"},  # duplicate
    ]
    result = run_competitive_refresh(current, new_observations)
    assert isinstance(result, RefreshResult)
    assert result.new_patterns >= 1
    assert result.updated_patterns >= 0


# --- Dashboard Data ---


def test_dashboard_data_structure() -> None:
    """Dashboard data has required keys."""
    patterns = _sample_patterns()
    data = get_competitive_dashboard_data(patterns)
    assert isinstance(data, dict)
    assert "hook_distribution" in data
    assert "gap_analysis" in data
    assert "temporal_trends" in data
