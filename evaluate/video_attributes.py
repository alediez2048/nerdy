"""Video attribute evaluator — 10-attribute checklist (P3-08, PRD 4.9.4).

Evaluates video variants against a structured checklist. Required
attributes must all pass; non-required failures are logged as warnings.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

VIDEO_ATTRIBUTES = [
    {"name": "hook_timing", "required": True, "description": "Attention-grabbing action within first 1.5 seconds"},
    {"name": "ugc_authenticity", "required": True, "description": "Feels organic/user-generated, not overly polished"},
    {"name": "pacing", "required": True, "description": "Matches spec (fast/medium/slow); no dead frames"},
    {"name": "text_legibility", "required": False, "description": "Any text overlays are readable at mobile resolution"},
    {"name": "brand_safety", "required": True, "description": "No inappropriate content, artifacts, or brand conflicts"},
    {"name": "subject_clarity", "required": False, "description": "Main subject/action is clearly visible and identifiable"},
    {"name": "aspect_ratio_compliance", "required": False, "description": "Video fills 9:16 frame without letterboxing"},
    {"name": "visual_continuity", "required": False, "description": "No jarring cuts, glitches, or frame jumps"},
    {"name": "emotional_tone_match", "required": False, "description": "Video mood matches the spec's intended emotion"},
    {"name": "audio_appropriateness", "required": False, "description": "Audio (if present) is appropriate; silence is clean"},
]

REQUIRED_ATTRIBUTES = [a["name"] for a in VIDEO_ATTRIBUTES if a["required"]]


@dataclass
class AttributeScore:
    """Score for a single video attribute."""

    name: str
    passed: bool
    confidence: float
    diagnostic: str


@dataclass
class VideoAttributeResult:
    """Result of evaluating a video against the 10-attribute checklist."""

    ad_id: str
    variant_id: str
    attribute_scores: dict[str, AttributeScore]
    overall_pass: bool
    pass_pct: float
    warnings: list[str] = field(default_factory=list)


def is_video_acceptable(result: VideoAttributeResult) -> bool:
    """Check if all Required attributes pass.

    Args:
        result: The video attribute evaluation result.

    Returns:
        True if all Required attributes passed.
    """
    for req_name in REQUIRED_ATTRIBUTES:
        score = result.attribute_scores.get(req_name)
        if score is None or not score.passed:
            return False
    return True


def evaluate_video_attributes(
    video_path: str,
    video_spec: object,
    ad_id: str = "",
    variant_id: str = "",
) -> VideoAttributeResult:
    """Evaluate a video against the 10-attribute checklist.

    In production, sends key frames + spec to Gemini Flash multimodal.
    This implementation provides the evaluation structure; the actual
    API call is integrated during pipeline assembly.

    Args:
        video_path: Path to the video file.
        video_spec: VideoSpec with expected attributes.
        ad_id: The ad identifier.
        variant_id: The variant identifier.

    Returns:
        VideoAttributeResult with per-attribute scores.
    """
    from evaluate.frame_extractor import extract_key_frames

    frames = extract_key_frames(video_path)
    logger.info("Extracted %d frames from %s for evaluation", len(frames), video_path)

    # Placeholder: in production, frames + spec sent to Gemini Flash
    scores: dict[str, AttributeScore] = {}
    warnings: list[str] = []

    for attr in VIDEO_ATTRIBUTES:
        score = AttributeScore(
            name=attr["name"],
            passed=True,  # Placeholder — real eval via API
            confidence=0.9,
            diagnostic="OK",
        )
        scores[attr["name"]] = score

    passed_count = sum(1 for s in scores.values() if s.passed)
    pass_pct = passed_count / len(scores) if scores else 0.0
    overall = is_video_acceptable(
        VideoAttributeResult(ad_id, variant_id, scores, True, pass_pct, [])
    )

    return VideoAttributeResult(
        ad_id=ad_id,
        variant_id=variant_id,
        attribute_scores=scores,
        overall_pass=overall,
        pass_pct=pass_pct,
        warnings=warnings,
    )
