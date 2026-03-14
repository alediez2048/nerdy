"""Competitive pattern query interface (P0-10, R2-Q2).

Loads and queries the competitive pattern database for brief expansion
and pipeline differentiation. Used by P1-01 (brief expansion engine).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_DEFAULT_PATH = "data/competitive/patterns.json"
_cache: dict[str, Any] | None = None


def load_patterns(path: str = _DEFAULT_PATH) -> list[dict[str, Any]]:
    """Load and cache the pattern database.

    Args:
        path: Path to patterns.json (relative to project root or absolute).

    Returns:
        List of pattern records.

    Raises:
        FileNotFoundError: If path does not exist.
    """
    global _cache
    p = Path(path)
    if not p.is_absolute():
        p = Path(__file__).resolve().parents[1] / path
    if not p.exists():
        raise FileNotFoundError(f"Pattern database not found: {p}")

    with open(p, encoding="utf-8") as f:
        data = json.load(f)

    if "patterns" not in data:
        raise ValueError("Invalid pattern database: missing 'patterns' key")

    _cache = data
    return data["patterns"]


def _get_cached() -> dict[str, Any]:
    """Return cached data, loading if needed."""
    global _cache
    if _cache is None:
        load_patterns()
    assert _cache is not None
    return _cache


def _matches_filters(
    pattern: dict[str, Any],
    audience: str | None,
    campaign_goal: str | None,
    hook_type: str | None,
    competitor: str | None,
    tags: list[str] | None,
) -> tuple[bool, int]:
    """Check if pattern matches filters. Returns (matches, relevance_score)."""
    relevance = 0

    if audience is not None:
        pa = pattern.get("primary_audience", "")
        if pa not in (audience, "both"):
            return (False, 0)
        relevance += 1

    if campaign_goal is not None:
        pattern_tags = pattern.get("tags", [])
        if campaign_goal not in pattern_tags:
            return (False, 0)
        relevance += 1

    if hook_type is not None:
        if pattern.get("hook_type") != hook_type:
            return (False, 0)
        relevance += 1

    if competitor is not None:
        if pattern.get("competitor") != competitor:
            return (False, 0)
        relevance += 1

    if tags is not None:
        pattern_tags = set(pattern.get("tags", []))
        if not any(t in pattern_tags for t in tags):
            return (False, 0)
        relevance += len([t for t in tags if t in pattern_tags])

    return (True, relevance)


def query_patterns(
    audience: str | None = None,
    campaign_goal: str | None = None,
    hook_type: str | None = None,
    competitor: str | None = None,
    tags: list[str] | None = None,
    top_n: int = 5,
) -> list[dict[str, Any]]:
    """Query pattern records by audience, campaign_goal, hook_type, competitor, tags.

    All filters are optional. Tags use inclusive matching (any tag matches).
    Results ranked by relevance (number of matching criteria). Returns top-N.

    Args:
        audience: Filter by primary_audience (or "both").
        campaign_goal: Filter by tag (e.g. "conversion", "awareness").
        hook_type: Filter by hook_type.
        competitor: Filter by competitor name.
        tags: Filter by tags (any match).
        top_n: Maximum number of results (default 5).

    Returns:
        List of matching pattern records, ranked by relevance.
    """
    data = _get_cached()
    patterns = data["patterns"]

    matched: list[tuple[dict[str, Any], int]] = []
    for p in patterns:
        ok, score = _matches_filters(p, audience, campaign_goal, hook_type, competitor, tags)
        if ok:
            matched.append((p, score))

    matched.sort(key=lambda x: -x[1])
    return [p for p, _ in matched[:top_n]]


def get_competitor_summary(competitor: str) -> dict[str, Any] | None:
    """Return the strategy summary for a given competitor.

    Args:
        competitor: Competitor name (e.g. "Chegg", "Kaplan").

    Returns:
        Summary dict with strategy, dominant_hooks, emotional_levers, gaps,
        or None if competitor not found.
    """
    data = _get_cached()
    summaries = data.get("competitor_summaries", {})
    return summaries.get(competitor)


def get_all_competitors() -> list[str]:
    """Return list of all competitors in the database."""
    data = _get_cached()
    summaries = data.get("competitor_summaries", {})
    return list(summaries.keys())


def get_landscape_context(
    audience: str,
    campaign_goal: str,
    top_n: int = 3,
) -> str:
    """Return formatted competitive context for brief expansion prompts.

    Combines top patterns and competitor summaries into a concise
    landscape overview suitable for injection into P1-01 brief expansion.

    Args:
        audience: Target audience (e.g. "parents", "students").
        campaign_goal: Campaign goal (e.g. "conversion", "awareness").
        top_n: Number of patterns to include (default 3).

    Returns:
        Formatted string with competitive differentiation guidance.
    """
    patterns = query_patterns(audience=audience, campaign_goal=campaign_goal, top_n=top_n)
    if not patterns:
        patterns = query_patterns(audience=audience, top_n=top_n)

    competitors = get_all_competitors()
    lines = ["## Competitive Landscape", ""]

    if patterns:
        lines.append("### Top Patterns")
        for p in patterns:
            comp = p.get("competitor", "?")
            hook = p.get("hook_type", "?")
            hook_text = (p.get("hook_text", "") or p.get("ad_text", ""))[:80]
            lines.append(f"- [{comp}] {hook}: {hook_text}...")
        lines.append("")

    lines.append("### Competitor Summaries")
    for comp in competitors:
        if comp == "Varsity Tutors":
            continue
        summary = get_competitor_summary(comp)
        if summary:
            strategy = summary.get("strategy", "")[:150]
            lines.append(f"- **{comp}**: {strategy}...")
    lines.append("")

    return "\n".join(lines)
