"""Graceful degradation — video failure fallback to image-only (P3-10).

When all video attempts fail, the ad publishes with copy + image only.
Video failure never blocks ad delivery.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from iterate.ledger import log_event

logger = logging.getLogger(__name__)


@dataclass
class DegradationResult:
    """Result of handling a video generation failure."""

    ad_id: str
    fallback: str  # "image-only"
    reason: str
    failed_variant_count: int = 0


def handle_video_failure(
    ad_id: str,
    reason: str = "All video variants failed evaluation",
    failed_count: int = 0,
    ledger_path: str | None = None,
) -> DegradationResult:
    """Handle video generation failure with graceful degradation.

    Logs video-blocked status and returns fallback instruction.
    Does NOT raise exceptions — video failure is recoverable.

    Args:
        ad_id: The ad identifier.
        reason: Why video generation failed.
        failed_count: Number of failed video variants.
        ledger_path: Optional ledger path for logging.

    Returns:
        DegradationResult indicating image-only fallback.
    """
    result = DegradationResult(
        ad_id=ad_id,
        fallback="image-only",
        reason=reason,
        failed_variant_count=failed_count,
    )

    logger.warning("Video degradation for %s: %s — falling back to image-only",
                    ad_id, reason)

    if ledger_path:
        log_event(ledger_path, {
            "event_type": "VideoBlocked",
            "ad_id": ad_id,
            "brief_id": "",
            "cycle_number": 0,
            "action": "video-degradation",
            "inputs": {"reason": reason, "failed_variant_count": failed_count},
            "outputs": {"fallback": "image-only"},
            "scores": {},
            "tokens_consumed": 0,
            "model_used": "",
            "seed": "",
        })

    return result
