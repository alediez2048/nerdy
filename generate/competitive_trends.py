"""Competitive intelligence — temporal trends + strategy shift alerts (P4-03).

Extends P0-09/P0-10 pattern DB with time awareness: tracks when patterns
were observed, computes hook type trends, and alerts on strategy shifts.
"""

from __future__ import annotations

import logging
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)

SHIFT_THRESHOLD_PCT = 15.0  # >15% change triggers alert


@dataclass
class PatternSnapshot:
    """A pattern observation with temporal metadata."""

    pattern_id: str
    competitor: str
    hook_type: str
    emotional_angle: str
    cta_style: str
    observed_date: str
    source_url: str | None = None


@dataclass
class TrendResult:
    """Trend for a single hook type or dimension."""

    hook_type: str
    direction: str  # rising, falling, stable
    current_pct: float
    previous_pct: float
    change_pct: float


@dataclass
class StrategyAlert:
    """Alert for a significant strategy shift."""

    competitor: str
    alert_type: str
    description: str
    severity: str  # info, warning, action


@dataclass
class RefreshResult:
    """Result of a competitive refresh cycle."""

    new_patterns: int
    updated_patterns: int
    alerts: list[StrategyAlert] = field(default_factory=list)


def _parse_date(date_str: str) -> datetime:
    """Parse ISO date string."""
    try:
        return datetime.fromisoformat(date_str)
    except (ValueError, TypeError):
        return datetime(2025, 1, 1)


def _split_by_period(patterns: list[dict], cutoff_date: str) -> tuple[list[dict], list[dict]]:
    """Split patterns into old (before cutoff) and new (on/after cutoff)."""
    cutoff = _parse_date(cutoff_date)
    old = [p for p in patterns if _parse_date(p.get("observed_date", "")) < cutoff]
    new = [p for p in patterns if _parse_date(p.get("observed_date", "")) >= cutoff]
    return old, new


def _compute_distribution(patterns: list[dict], field_name: str) -> dict[str, float]:
    """Compute percentage distribution for a field."""
    if not patterns:
        return {}
    counts = Counter(p.get(field_name, "unknown") for p in patterns)
    total = sum(counts.values())
    return {k: round(v / total * 100, 1) for k, v in counts.items()}


def _infer_cutoff(patterns: list[dict], window_months: int) -> str:
    """Infer cutoff date from patterns based on midpoint of date range."""
    dates = [_parse_date(p.get("observed_date", "")) for p in patterns]
    if not dates:
        return "2026-01-01"
    dates.sort()
    mid_idx = len(dates) // 2
    return dates[mid_idx].strftime("%Y-%m-%d")


def compute_hook_trends(
    patterns: list[dict],
    window_months: int = 3,
) -> list[TrendResult]:
    """Compare hook type distribution between old and new periods.

    Args:
        patterns: List of pattern dicts with observed_date.
        window_months: Used to infer the cutoff between old/new periods.

    Returns:
        List of TrendResult for each hook type.
    """
    cutoff = _infer_cutoff(patterns, window_months)
    old, new = _split_by_period(patterns, cutoff)

    if not old or not new:
        return []

    old_dist = _compute_distribution(old, "hook_type")
    new_dist = _compute_distribution(new, "hook_type")

    all_hooks = set(old_dist.keys()) | set(new_dist.keys())
    trends: list[TrendResult] = []

    for hook in all_hooks:
        prev = old_dist.get(hook, 0.0)
        curr = new_dist.get(hook, 0.0)
        change = curr - prev

        if change > 5:
            direction = "rising"
        elif change < -5:
            direction = "falling"
        else:
            direction = "stable"

        trends.append(TrendResult(
            hook_type=hook,
            direction=direction,
            current_pct=curr,
            previous_pct=prev,
            change_pct=round(change, 1),
        ))

    return trends


def get_trending_hooks(
    patterns: list[dict],
    direction: str = "rising",
) -> list[str]:
    """Return hook types trending in the given direction.

    Args:
        patterns: List of pattern dicts with observed_date.
        direction: "rising", "falling", or "stable".

    Returns:
        List of hook type strings matching the direction.
    """
    trends = compute_hook_trends(patterns)
    return [t.hook_type for t in trends if t.direction == direction]


def compute_competitor_shifts(
    patterns: list[dict],
    competitor: str,
) -> list[TrendResult]:
    """Detect strategy changes for a specific competitor.

    Args:
        patterns: All patterns.
        competitor: Competitor name to analyze.

    Returns:
        List of TrendResult for that competitor's hook distribution.
    """
    comp_patterns = [p for p in patterns if p.get("competitor") == competitor]
    return compute_hook_trends(comp_patterns)


def detect_strategy_shifts(patterns: list[dict]) -> list[StrategyAlert]:
    """Detect significant strategy shifts across all competitors.

    Fires an alert when any competitor's hook distribution shifts >15%.

    Args:
        patterns: All patterns with observed_date.

    Returns:
        List of StrategyAlert for significant shifts.
    """
    competitors = set(p.get("competitor", "") for p in patterns)
    alerts: list[StrategyAlert] = []

    for comp in competitors:
        if not comp:
            continue
        shifts = compute_competitor_shifts(patterns, comp)
        for trend in shifts:
            if abs(trend.change_pct) > SHIFT_THRESHOLD_PCT:
                severity = "action" if abs(trend.change_pct) > 30 else "warning"
                alerts.append(StrategyAlert(
                    competitor=comp,
                    alert_type=f"hook_shift_{trend.direction}",
                    description=(
                        f"{comp}: {trend.hook_type} shifted {trend.change_pct:+.1f}% "
                        f"({trend.previous_pct:.0f}% → {trend.current_pct:.0f}%)"
                    ),
                    severity=severity,
                ))

    return alerts


def run_competitive_refresh(
    current_patterns: list[dict],
    new_observations: list[dict],
) -> RefreshResult:
    """Merge new observations into the pattern database.

    Deduplicates by (competitor, source_url). Updates existing if
    re-observed, adds new if novel.

    Args:
        current_patterns: Existing pattern records.
        new_observations: Newly scraped patterns.

    Returns:
        RefreshResult with counts and any alerts.
    """
    existing_keys: dict[tuple[str, str], int] = {}
    for i, p in enumerate(current_patterns):
        key = (p.get("competitor", ""), p.get("source_url", ""))
        if key[1]:  # Only track if source_url exists
            existing_keys[key] = i

    new_count = 0
    updated_count = 0
    merged = list(current_patterns)

    for obs in new_observations:
        key = (obs.get("competitor", ""), obs.get("source_url", ""))
        if key[1] and key in existing_keys:
            idx = existing_keys[key]
            merged[idx]["observed_date"] = obs.get("observed_date", merged[idx].get("observed_date"))
            updated_count += 1
        else:
            obs["pattern_id"] = obs.get("pattern_id", f"auto_{len(merged)}")
            merged.append(obs)
            new_count += 1

    all_patterns = merged
    alerts = detect_strategy_shifts(all_patterns)

    return RefreshResult(
        new_patterns=new_count,
        updated_patterns=updated_count,
        alerts=alerts,
    )


def get_competitive_dashboard_data(patterns: list[dict]) -> dict:
    """Generate structured data for the competitive dashboard (Panel 8).

    Args:
        patterns: All pattern records.

    Returns:
        Dict with hook_distribution, strategy_radar, gap_analysis, temporal_trends.
    """
    hook_dist = _compute_distribution(patterns, "hook_type")

    # Strategy radar: per-competitor hook distribution
    competitors = set(p.get("competitor", "") for p in patterns)
    strategy_radar: dict[str, dict] = {}
    for comp in competitors:
        if comp:
            comp_patterns = [p for p in patterns if p.get("competitor") == comp]
            strategy_radar[comp] = _compute_distribution(comp_patterns, "hook_type")

    # Gap analysis: hook types with low competitor coverage
    all_hooks = set(p.get("hook_type", "") for p in patterns)
    gap_analysis: list[dict] = []
    for hook in all_hooks:
        if not hook:
            continue
        hook_pct = hook_dist.get(hook, 0)
        if hook_pct < 15:
            gap_analysis.append({
                "hook_type": hook,
                "coverage_pct": hook_pct,
                "opportunity": f"Low competitor usage ({hook_pct:.0f}%) — potential differentiation",
            })

    # Temporal trends
    trends = compute_hook_trends(patterns)
    temporal = [
        {"hook_type": t.hook_type, "direction": t.direction, "change_pct": t.change_pct}
        for t in trends
    ]

    return {
        "hook_distribution": hook_dist,
        "strategy_radar": strategy_radar,
        "gap_analysis": gap_analysis,
        "temporal_trends": temporal,
    }
