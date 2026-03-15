"""Video variant selection by composite score (P3-10).

Selects the best video variant using the same composite scoring
formula as image selection: attribute_pass_pct * 0.4 + coherence_avg * 0.6.
"""

from __future__ import annotations

import logging

from evaluate.video_attributes import VideoAttributeResult, is_video_acceptable
from evaluate.video_coherence import VideoCoherenceResult, is_coherent

logger = logging.getLogger(__name__)


def compute_video_composite_score(
    attribute_result: VideoAttributeResult,
    coherence_result: VideoCoherenceResult,
) -> float:
    """Compute composite score for a video variant.

    Composite = attribute_pass_pct * 0.4 + coherence_avg * 0.6

    Args:
        attribute_result: Video attribute evaluation result.
        coherence_result: Video coherence check result.

    Returns:
        Composite score (float).
    """
    return attribute_result.pass_pct * 0.4 + coherence_result.coherence_avg * 0.6


def select_best_video(
    variants: list[tuple[str, dict]],
) -> str | None:
    """Select the best video variant by composite score.

    Only considers variants where all Required attributes pass
    and coherence is acceptable (>= 6 on all dimensions).

    Args:
        variants: List of (variant_id, {"attr": VideoAttributeResult, "coh": VideoCoherenceResult}).

    Returns:
        variant_id of the best passing variant, or None if none pass.
    """
    best_id: str | None = None
    best_score = -1.0

    for variant_id, evals in variants:
        attr_result = evals["attr"]
        coh_result = evals["coh"]

        if not is_video_acceptable(attr_result):
            logger.info("Variant %s failed Required attributes", variant_id)
            continue

        if not is_coherent(coh_result):
            logger.info("Variant %s failed coherence check", variant_id)
            continue

        composite = compute_video_composite_score(attr_result, coh_result)
        if composite > best_score:
            best_score = composite
            best_id = variant_id

    if best_id:
        logger.info("Selected video variant %s (composite=%.2f)", best_id, best_score)
    else:
        logger.warning("No video variant passed selection criteria")

    return best_id
