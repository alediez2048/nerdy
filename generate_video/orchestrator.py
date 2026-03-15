"""Video generation orchestrator (P3-07).

Coordinates video spec extraction, variant generation, and ledger logging.
Generates 2 video variants per ad (anchor + alternative).
Graceful degradation: video failure never blocks ad delivery.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from generate_video.veo_client import VideoResult, generate_video
from generate_video.video_spec import VideoSpec, extract_video_spec, generate_variant_specs
from iterate.ledger import log_event

logger = logging.getLogger(__name__)


@dataclass
class VideoVariant:
    """A generated video variant."""

    ad_id: str
    variant_type: str  # "anchor" | "alternative"
    video_spec: VideoSpec
    result: VideoResult | None
    error: str | None = None


def _generate_single_video(
    video_spec: VideoSpec,
    seed: int,
) -> VideoResult:
    """Generate a single video from spec. Separated for mocking."""
    return generate_video(video_spec, seed)


def generate_video_variants(
    ad_id: str,
    expanded_brief: dict,
    ledger_path: str | None = None,
    seed: int = 42,
) -> list[VideoVariant]:
    """Generate 2 video variants (anchor + alternative) for an ad.

    Extracts video spec from brief, generates variant specs,
    and calls Veo API for each. Failures are logged but do not
    crash the pipeline (graceful degradation).

    Args:
        ad_id: The ad identifier.
        expanded_brief: The expanded brief dict.
        ledger_path: Optional ledger path for logging.
        seed: Base seed for reproducibility.

    Returns:
        List of VideoVariant objects (may contain errors).
    """
    # Extract spec and generate variants
    base_spec = extract_video_spec(expanded_brief)
    anchor_spec, alt_spec = generate_variant_specs(base_spec)

    variant_configs = [
        ("anchor", anchor_spec, seed),
        ("alternative", alt_spec, seed + 1000),
    ]

    variants: list[VideoVariant] = []

    for variant_type, spec, variant_seed in variant_configs:
        try:
            result = _generate_single_video(spec, variant_seed)
            variant = VideoVariant(
                ad_id=ad_id,
                variant_type=variant_type,
                video_spec=spec,
                result=result,
            )
        except Exception as e:
            logger.error("Video generation failed for %s/%s: %s",
                         ad_id, variant_type, e)
            variant = VideoVariant(
                ad_id=ad_id,
                variant_type=variant_type,
                video_spec=spec,
                result=None,
                error=str(e),
            )

        variants.append(variant)

        # Log to ledger
        if ledger_path:
            log_event(ledger_path, {
                "event_type": "VideoGenerated",
                "ad_id": ad_id,
                "brief_id": expanded_brief.get("brief_id", ""),
                "cycle_number": 0,
                "action": "video-generation",
                "inputs": {
                    "variant_type": variant_type,
                    "scene_description": spec.scene_description,
                    "pacing": spec.pacing,
                },
                "outputs": {
                    "video_path": variant.result.video_path if variant.result else None,
                    "success": variant.result is not None,
                    "error": variant.error,
                },
                "scores": {},
                "tokens_consumed": variant.result.tokens_consumed if variant.result else 0,
                "model_used": variant.result.model_used if variant.result else "veo-3.1-fast",
                "seed": str(variant_seed),
            })

    return variants
