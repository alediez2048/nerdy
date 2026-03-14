"""Campaign-goal-adaptive dimension weighting with floor constraints (P1-05, R1-Q3).

Two weight profiles (awareness/conversion) with hard floors on Clarity (6.0) and
Brand Voice (5.0). Transforms raw per-dimension scores into a weighted average
and pass/reject determination.

Weight table from PRD Section 5.2:
  | Dimension           | Awareness | Conversion | Floor |
  |---------------------|-----------|------------|-------|
  | Clarity             | 0.25      | 0.25       | 6.0   |
  | Value Proposition   | 0.20      | 0.25       | —     |
  | Call to Action      | 0.10      | 0.30       | —     |
  | Brand Voice         | 0.20      | 0.10       | 5.0   |
  | Emotional Resonance | 0.25      | 0.10       | —     |
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

DIMENSIONS = (
    "clarity",
    "value_proposition",
    "cta",
    "brand_voice",
    "emotional_resonance",
)

QUALITY_THRESHOLD = 7.0

FLOOR_CONSTRAINTS: dict[str, float] = {
    "clarity": 6.0,
    "brand_voice": 5.0,
}


@dataclass
class WeightProfile:
    """Campaign-goal-specific weight profile."""

    campaign_goal: str
    weights: dict[str, float]
    floors: dict[str, float] = field(default_factory=lambda: dict(FLOOR_CONSTRAINTS))


@dataclass
class FloorViolation:
    """A single floor constraint violation."""

    dimension: str
    score: float
    floor: float
    deficit: float


@dataclass
class WeightedResult:
    """Result of applying weights + floor checks to dimension scores."""

    weighted_average: float
    campaign_goal: str
    weight_profile: WeightProfile
    floor_violations: list[FloorViolation]
    passes_threshold: bool
    rejection_reasons: list[str]


AWARENESS_WEIGHTS = WeightProfile(
    campaign_goal="awareness",
    weights={
        "clarity": 0.25,
        "value_proposition": 0.20,
        "cta": 0.10,
        "brand_voice": 0.20,
        "emotional_resonance": 0.25,
    },
)

CONVERSION_WEIGHTS = WeightProfile(
    campaign_goal="conversion",
    weights={
        "clarity": 0.25,
        "value_proposition": 0.25,
        "cta": 0.30,
        "brand_voice": 0.10,
        "emotional_resonance": 0.10,
    },
)

_PROFILES: dict[str, WeightProfile] = {
    "awareness": AWARENESS_WEIGHTS,
    "conversion": CONVERSION_WEIGHTS,
}


def get_weight_profile(campaign_goal: str) -> WeightProfile:
    """Return the weight profile for the given campaign goal.

    Falls back to awareness weights for unknown goals with a logged warning.
    """
    if campaign_goal in _PROFILES:
        return _PROFILES[campaign_goal]
    logger.warning(
        "Unknown campaign goal '%s', falling back to awareness weights", campaign_goal
    )
    return AWARENESS_WEIGHTS


def compute_weighted_score(scores: dict[str, float], profile: WeightProfile) -> float:
    """Compute weighted average of dimension scores.

    Args:
        scores: Dict mapping dimension name to score (1-10).
        profile: Weight profile to apply.

    Returns:
        Weighted average rounded to 2 decimal places.
    """
    total = 0.0
    for dim in DIMENSIONS:
        score = scores.get(dim, 5.0)
        weight = profile.weights.get(dim, 0.2)
        total += score * weight
    return round(total, 2)


def check_floor_violations(scores: dict[str, float]) -> list[FloorViolation]:
    """Check dimension scores against floor constraints.

    Returns:
        List of FloorViolation objects (empty if no violations).
    """
    violations: list[FloorViolation] = []
    for dim, floor in FLOOR_CONSTRAINTS.items():
        score = scores.get(dim, 0.0)
        if score < floor:
            violations.append(
                FloorViolation(
                    dimension=dim,
                    score=score,
                    floor=floor,
                    deficit=round(floor - score, 2),
                )
            )
    return violations


def evaluate_with_weights(
    scores: dict[str, float], campaign_goal: str
) -> WeightedResult:
    """Apply campaign-goal weights and floor constraints to dimension scores.

    Args:
        scores: Dict mapping dimension name to score (1-10).
        campaign_goal: "awareness" or "conversion".

    Returns:
        WeightedResult with weighted average, violations, and pass/reject.
    """
    profile = get_weight_profile(campaign_goal)
    weighted_avg = compute_weighted_score(scores, profile)
    violations = check_floor_violations(scores)

    rejection_reasons: list[str] = []

    for v in violations:
        rejection_reasons.append(
            f"Floor violation: {v.dimension} scored {v.score:.1f}, "
            f"minimum required is {v.floor:.1f} (deficit: {v.deficit:.1f})"
        )

    if weighted_avg < QUALITY_THRESHOLD:
        rejection_reasons.append(
            f"Weighted average {weighted_avg:.2f} is below the 7.0 quality threshold "
            f"(campaign goal: {campaign_goal})"
        )

    passes = weighted_avg >= QUALITY_THRESHOLD and len(violations) == 0

    return WeightedResult(
        weighted_average=weighted_avg,
        campaign_goal=campaign_goal,
        weight_profile=profile,
        floor_violations=violations,
        passes_threshold=passes,
        rejection_reasons=rejection_reasons,
    )
