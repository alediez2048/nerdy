"""Video targeted regen loop with diagnostics (P3-10).

Diagnoses weakest attributes/dimensions and produces targeted regen
context. Budget enforcement: max 3 videos per ad (2 initial + 1 regen).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from evaluate.video_attributes import VideoAttributeResult
from evaluate.video_coherence import VideoCoherenceResult

logger = logging.getLogger(__name__)

MAX_VIDEOS_PER_AD = 3  # 2 initial + 1 regen


@dataclass
class VideoDiagnostic:
    """Diagnostic context for targeted video regen."""

    failed_attributes: list[str]
    failed_dimensions: list[str]
    diagnostics: list[str]
    regen_guidance: str


def diagnose_video_failure(
    attribute_result: VideoAttributeResult,
    coherence_result: VideoCoherenceResult,
) -> VideoDiagnostic:
    """Diagnose why a video variant failed and produce regen guidance.

    Args:
        attribute_result: The attribute evaluation result.
        coherence_result: The coherence check result.

    Returns:
        VideoDiagnostic with failed items and targeted guidance.
    """
    failed_attrs: list[str] = []
    failed_dims: list[str] = []
    diagnostics: list[str] = []

    # Check failed attributes
    for name, score in attribute_result.attribute_scores.items():
        if not score.passed:
            failed_attrs.append(name)
            diagnostics.append(f"Attribute '{name}': {score.diagnostic}")

    # Check failed coherence dimensions
    for name, dim_score in coherence_result.dimension_scores.items():
        if dim_score.score < 6.0:
            failed_dims.append(name)
            diagnostics.append(f"Coherence '{name}' scored {dim_score.score:.1f}: {dim_score.rationale}")

    # Build targeted regen guidance
    guidance_parts: list[str] = []
    if failed_attrs:
        guidance_parts.append(f"Fix attributes: {', '.join(failed_attrs)}")
    if failed_dims:
        guidance_parts.append(f"Improve coherence: {', '.join(failed_dims)}")
    guidance = "; ".join(guidance_parts) if guidance_parts else "General quality improvement needed"

    return VideoDiagnostic(
        failed_attributes=failed_attrs,
        failed_dimensions=failed_dims,
        diagnostics=diagnostics,
        regen_guidance=guidance,
    )
