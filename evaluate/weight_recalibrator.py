"""Weight recalibration from real-world performance data (PF-04).

Uses dimension-performance correlations to compute data-driven weight profiles.
Blends 70% data-driven + 30% prior to avoid overfitting to simulated data.

Extends evaluate/dimensions.py — produces compatible WeightProfile instances.
"""

from __future__ import annotations

from dataclasses import dataclass

from evaluate.correlation import DIMENSIONS
from evaluate.dimensions import (
    AWARENESS_WEIGHTS,
    CONVERSION_WEIGHTS,
    FLOOR_CONSTRAINTS,
    WeightProfile,
)
from evaluate.performance_correlation import (
    DimensionPerformanceMatrix,
)
from iterate.ledger import log_event


# Metric-to-campaign-goal mapping for recalibration
GOAL_TARGET_METRICS = {
    "awareness": "ctr",           # Awareness optimizes for eyeballs
    "conversion": "conversion_rate",  # Conversion optimizes for actions
}

# Blend ratio: data-driven vs prior
DATA_BLEND_RATIO = 0.70
PRIOR_BLEND_RATIO = 0.30

# Minimum weight per dimension (prevent any dimension from being zeroed out)
MIN_WEIGHT = 0.05


@dataclass
class RecalibrationReport:
    """Before/after comparison of weight profiles."""

    campaign_goal: str
    target_metric: str
    original_weights: dict[str, float]
    recalibrated_weights: dict[str, float]
    correlation_basis: dict[str, float]  # dimension -> r with target metric
    delta_per_dimension: dict[str, float]
    data_blend_ratio: float
    confidence_note: str


def recalibrate_weights(
    matrix: DimensionPerformanceMatrix,
    campaign_goal: str,
    target_metric: str | None = None,
) -> RecalibrationReport:
    """Compute data-driven weight profile from performance correlations.

    Algorithm:
    1. Extract correlations between each dimension and the target metric
    2. Take absolute values (both positive and negative correlations matter)
    3. Apply floor (MIN_WEIGHT) so no dimension is zeroed
    4. Normalize to sum to 1.0
    5. Blend 70% data-driven + 30% prior weights

    Args:
        matrix: DimensionPerformanceMatrix from PF-03.
        campaign_goal: "awareness" or "conversion".
        target_metric: Which metric to optimize for. Defaults based on goal.

    Returns:
        RecalibrationReport with before/after weights and rationale.
    """
    if target_metric is None:
        target_metric = GOAL_TARGET_METRICS.get(campaign_goal, "ctr")

    # Get prior weights
    prior_profile = AWARENESS_WEIGHTS if campaign_goal == "awareness" else CONVERSION_WEIGHTS
    prior_weights = dict(prior_profile.weights)

    # Extract correlations for target metric
    correlations: dict[str, float] = {}
    for dim in DIMENSIONS:
        r = matrix.matrix.get((dim, target_metric), 0.0)
        correlations[dim] = r

    # Step 1: Absolute correlations
    abs_corr = {dim: max(abs(r), MIN_WEIGHT) for dim, r in correlations.items()}

    # Step 2: Normalize to sum to 1.0
    total = sum(abs_corr.values())
    data_weights = {dim: round(v / total, 4) for dim, v in abs_corr.items()}

    # Step 3: Blend with prior
    blended = {}
    for dim in DIMENSIONS:
        blended[dim] = round(
            DATA_BLEND_RATIO * data_weights[dim] + PRIOR_BLEND_RATIO * prior_weights.get(dim, 0.2),
            4,
        )

    # Step 4: Re-normalize after blending (ensure sum = 1.0)
    blend_total = sum(blended.values())
    recalibrated = {dim: round(v / blend_total, 4) for dim, v in blended.items()}

    # Fix rounding to ensure exact 1.0
    diff = round(1.0 - sum(recalibrated.values()), 4)
    if diff != 0:
        # Add remainder to largest weight
        max_dim = max(recalibrated, key=recalibrated.get)
        recalibrated[max_dim] = round(recalibrated[max_dim] + diff, 4)

    # Compute deltas
    deltas = {dim: round(recalibrated[dim] - prior_weights.get(dim, 0.2), 4) for dim in DIMENSIONS}

    return RecalibrationReport(
        campaign_goal=campaign_goal,
        target_metric=target_metric,
        original_weights=prior_weights,
        recalibrated_weights=recalibrated,
        correlation_basis=correlations,
        delta_per_dimension=deltas,
        data_blend_ratio=DATA_BLEND_RATIO,
        confidence_note=(
            "Recalibrated from simulated performance data (PF-02). "
            "Production deployment requires validation against real Meta Ads Manager data. "
            f"Blend ratio: {DATA_BLEND_RATIO:.0%} data-driven + {PRIOR_BLEND_RATIO:.0%} prior."
        ),
    )


def recalibrated_weight_profile(report: RecalibrationReport) -> WeightProfile:
    """Create a WeightProfile from a RecalibrationReport."""
    return WeightProfile(
        campaign_goal=f"{report.campaign_goal}_recalibrated",
        weights=dict(report.recalibrated_weights),
        floors=dict(FLOOR_CONSTRAINTS),
    )


def compare_profiles(original: WeightProfile, recalibrated: WeightProfile) -> str:
    """Format a before/after weight comparison table."""
    lines = [
        f"Weight Profile Comparison: {original.campaign_goal} vs {recalibrated.campaign_goal}",
        "",
        f"{'Dimension':<25} {'Original':>10} {'Recalibrated':>14} {'Delta':>8}",
        "-" * 60,
    ]

    dim_labels = {
        "clarity": "Clarity",
        "value_proposition": "Value Proposition",
        "cta": "Call to Action",
        "brand_voice": "Brand Voice",
        "emotional_resonance": "Emotional Resonance",
    }

    for dim in DIMENSIONS:
        orig = original.weights.get(dim, 0.2)
        recal = recalibrated.weights.get(dim, 0.2)
        delta = recal - orig
        sign = "+" if delta > 0 else ""
        lines.append(
            f"{dim_labels[dim]:<25} {orig:>10.2%} {recal:>14.2%} {sign}{delta:>7.2%}"
        )

    lines.append("-" * 60)
    lines.append(f"{'Total':<25} {sum(original.weights.values()):>10.2%} {sum(recalibrated.weights.values()):>14.2%}")

    return "\n".join(lines)


def log_recalibration(report: RecalibrationReport, ledger_path: str) -> None:
    """Log a WeightsRecalibrated event to the ledger."""
    event = {
        "event_type": "WeightsRecalibrated",
        "ad_id": "system",
        "brief_id": "system",
        "cycle_number": 0,
        "action": "recalibrate_weights",
        "tokens_consumed": 0,
        "model_used": "none",
        "seed": 0,
        "inputs": {
            "campaign_goal": report.campaign_goal,
            "target_metric": report.target_metric,
            "original_weights": report.original_weights,
            "correlation_basis": report.correlation_basis,
        },
        "outputs": {
            "recalibrated_weights": report.recalibrated_weights,
            "delta_per_dimension": report.delta_per_dimension,
            "confidence_note": report.confidence_note,
        },
    }
    log_event(ledger_path, event)
