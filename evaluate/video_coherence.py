"""Script-video coherence checker — 4-dimension scoring (P3-09, PRD 4.9.5).

Scores ad copy + video pairs across 4 coherence dimensions. Below 6 on
any dimension marks the pair as incoherent and surfaces diagnostics
for targeted regen.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

COHERENCE_DIMENSIONS = [
    {"name": "message_alignment", "description": "Does the video reinforce the ad copy's core message?"},
    {"name": "audience_match", "description": "Does the video's subject/setting match the target audience?"},
    {"name": "emotional_consistency", "description": "Does the video's mood match the copy's emotional register?"},
    {"name": "narrative_flow", "description": "Does the video's pacing/story complement the copy's structure?"},
]

_COHERENCE_THRESHOLD = 6.0


@dataclass
class CoherenceDimensionScore:
    """Score for a single coherence dimension."""

    name: str
    score: float
    rationale: str


@dataclass
class VideoCoherenceResult:
    """Result of checking script-video coherence."""

    ad_id: str
    variant_id: str
    dimension_scores: dict[str, CoherenceDimensionScore]
    coherence_avg: float
    is_coherent_flag: bool
    failing_dimensions: list[str] = field(default_factory=list)


def is_coherent(result: VideoCoherenceResult) -> bool:
    """Check if all coherence dimensions score >= 6.

    Args:
        result: The coherence check result.

    Returns:
        True if all dimensions >= 6.0.
    """
    for dim_score in result.dimension_scores.values():
        if dim_score.score < _COHERENCE_THRESHOLD:
            return False
    return True


def check_video_coherence(
    ad_copy: dict,
    video_path: str,
    video_spec: object,
    ad_id: str = "",
    variant_id: str = "",
) -> VideoCoherenceResult:
    """Check coherence between ad copy and video across 4 dimensions.

    In production, sends copy + video frames + spec to Gemini Flash.
    This implementation provides the evaluation structure.

    Args:
        ad_copy: The ad copy dict (headline, primary_text, etc.).
        video_path: Path to the video file.
        video_spec: VideoSpec with generation parameters.
        ad_id: The ad identifier.
        variant_id: The variant identifier.

    Returns:
        VideoCoherenceResult with per-dimension scores.
    """
    from evaluate.frame_extractor import extract_key_frames

    frames = extract_key_frames(video_path)
    logger.info("Checking coherence for %s/%s with %d frames", ad_id, variant_id, len(frames))

    # Placeholder scores — real eval via Gemini Flash multimodal
    dim_scores: dict[str, CoherenceDimensionScore] = {}
    for dim in COHERENCE_DIMENSIONS:
        dim_scores[dim["name"]] = CoherenceDimensionScore(
            name=dim["name"],
            score=7.0,
            rationale=f"{dim['description']} — evaluation pending",
        )

    scores = [ds.score for ds in dim_scores.values()]
    avg = sum(scores) / len(scores) if scores else 0
    failing = [name for name, ds in dim_scores.items() if ds.score < _COHERENCE_THRESHOLD]

    result = VideoCoherenceResult(
        ad_id=ad_id,
        variant_id=variant_id,
        dimension_scores=dim_scores,
        coherence_avg=avg,
        is_coherent_flag=len(failing) == 0,
        failing_dimensions=failing,
    )

    return result
