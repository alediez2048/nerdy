"""Pareto image selection — composite scoring and variant picking (P1-15).

Selects the best image variant using a composite score that blends
visual attribute pass rate (40%) with text-image coherence (60%).
Coherence defaults to 1.0 until P1-16 adds the coherence evaluator.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ImageVariantResult:
    """Scored image variant ready for selection."""

    ad_id: str
    variant_type: str
    attribute_pass_pct: float
    coherence_avg: float
    composite_score: float
    image_path: str


@dataclass
class ImageSelectionResult:
    """Result of selecting the best image variant."""

    winner: ImageVariantResult
    all_variants: list[ImageVariantResult]
    all_pass_threshold: bool


def compute_composite_score(
    attribute_pass_pct: float,
    coherence_avg: float,
) -> float:
    """Compute composite score: attribute_pass_pct * 0.4 + coherence_avg * 0.6.

    Args:
        attribute_pass_pct: Fraction of visual attributes that passed (0.0–1.0).
        coherence_avg: Average text-image coherence score (0.0–1.0).

    Returns:
        Composite score between 0.0 and 1.0.
    """
    return round(attribute_pass_pct * 0.4 + coherence_avg * 0.6, 4)


def select_best_variant(
    variants: list[ImageVariantResult],
) -> ImageSelectionResult:
    """Select the best image variant by highest composite score.

    On tie, the first variant in the list wins (stable sort).

    Args:
        variants: List of scored image variants.

    Returns:
        ImageSelectionResult with winner and all variants.

    Raises:
        ValueError: If variants list is empty.
    """
    if not variants:
        raise ValueError("Cannot select from empty variant list")

    winner = max(variants, key=lambda v: v.composite_score)
    all_pass = all(v.attribute_pass_pct >= 0.8 for v in variants)

    logger.info(
        "Selected %s for %s (composite=%.4f, all_pass=%s)",
        winner.variant_type,
        winner.ad_id,
        winner.composite_score,
        all_pass,
    )

    return ImageSelectionResult(
        winner=winner,
        all_variants=variants,
        all_pass_threshold=all_pass,
    )
