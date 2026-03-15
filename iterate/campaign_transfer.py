"""Cross-campaign transfer — shared structure, isolated content (P4-04, R3-Q8).

Structural patterns (hook types, CTA styles, body structure) transfer
across campaigns. Content (claims, proof points, pricing) stays
campaign-specific. A campaign_scope tag separates craft from substance.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

UNIVERSAL = "universal"

STRUCTURAL_TYPES = frozenset({
    "hook_type", "cta_style", "body_structure", "emotional_angle",
    "composition", "color_palette", "subject_framing",
})

CONTENT_TYPES = frozenset({
    "claims", "proof_points", "pricing", "testimonials",
    "brand_language", "specific_offers",
})


def campaign_scope(name: str) -> str:
    """Create a campaign-specific scope tag."""
    return f"campaign:{name}"


@dataclass
class PatternRecord:
    """A pattern with campaign scope and win rate."""

    pattern_type: str
    pattern_value: str
    campaign_scope: str
    win_rate: float
    sample_size: int
    audience: str
    source: str


def classify_scope(pattern: dict) -> str:
    """Determine if a pattern is universal or campaign-specific.

    Args:
        pattern: Dict with at least 'pattern_type'.

    Returns:
        UNIVERSAL for structural patterns, campaign-specific otherwise.
    """
    ptype = pattern.get("pattern_type", "")
    if ptype in STRUCTURAL_TYPES:
        return UNIVERSAL
    return campaign_scope(pattern.get("campaign", "default"))


class PatternLibrary:
    """In-memory pattern library with scope-based filtering."""

    def __init__(self) -> None:
        self._patterns: list[PatternRecord] = []

    def add_pattern(self, record: PatternRecord) -> None:
        """Add or update a pattern record."""
        for i, existing in enumerate(self._patterns):
            if (existing.pattern_type == record.pattern_type
                    and existing.pattern_value == record.pattern_value
                    and existing.audience == record.audience):
                self._patterns[i] = record
                return
        self._patterns.append(record)

    def get_universal_patterns(
        self,
        audience: str | None = None,
        top_n: int = 20,
    ) -> list[PatternRecord]:
        """Return universal patterns, optionally filtered by audience."""
        results = [p for p in self._patterns if p.campaign_scope == UNIVERSAL]
        if audience:
            results = [p for p in results if p.audience == audience]
        results.sort(key=lambda p: -p.win_rate)
        return results[:top_n]

    def get_campaign_patterns(
        self,
        campaign_name: str,
        audience: str | None = None,
    ) -> list[PatternRecord]:
        """Return patterns for a specific campaign."""
        scope = campaign_scope(campaign_name)
        results = [p for p in self._patterns if p.campaign_scope == scope]
        if audience:
            results = [p for p in results if p.audience == audience]
        return results

    def get_transferable_insights(
        self,
        source_campaign: str,
        target_audience: str,
    ) -> list[PatternRecord]:
        """Return universal patterns applicable to target audience."""
        return self.get_universal_patterns(audience=target_audience)

    def save(self, path: str) -> None:
        """Persist library to JSON."""
        data = [asdict(p) for p in self._patterns]
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    def load(self, path: str) -> None:
        """Load library from JSON."""
        with open(path) as f:
            data = json.load(f)
        self._patterns = [PatternRecord(**d) for d in data]


def get_transfer_recommendations(
    library: PatternLibrary,
    target_audience: str,
    target_goal: str | None = None,
    min_sample_size: int = 3,
) -> list[PatternRecord]:
    """Return high-win-rate universal patterns for the target.

    Args:
        library: The pattern library to query.
        target_audience: Target audience segment.
        target_goal: Optional campaign goal filter.
        min_sample_size: Minimum sample size to include (default 3).

    Returns:
        List of PatternRecord sorted by win_rate descending.
    """
    patterns = library.get_universal_patterns(audience=target_audience)
    filtered = [p for p in patterns if p.sample_size >= min_sample_size]
    filtered.sort(key=lambda p: -p.win_rate)
    return filtered
