"""Video spec extraction from expanded brief (P3-07, PRD 4.9.2).

Derives video generation specs from the same expanded brief used for
image specs. Produces anchor + alternative variant specs.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

_PACING_MAP = {
    "urgency": "fast",
    "confidence": "medium",
    "aspiration": "medium",
    "empathy": "slow",
}

_MOOD_MAP = {
    "aspiration": "uplifting and optimistic",
    "urgency": "energetic and motivating",
    "empathy": "warm and understanding",
    "confidence": "assured and empowering",
}

_ALT_PACING = {"fast": "medium", "medium": "slow", "slow": "medium"}


@dataclass
class VideoSpec:
    """Specification for UGC video generation."""

    hook_action: str
    scene_description: str
    pacing: str  # fast | medium | slow
    mood: str
    subject_demographic: str
    text_overlay_content: str
    audio_mode: str  # silent | music | voiceover
    duration: int = 6
    aspect_ratio: str = "9:16"


def extract_video_spec(expanded_brief: dict) -> VideoSpec:
    """Derive video spec from expanded brief.

    Grounded in brief facts — no hallucinated claims.

    Args:
        expanded_brief: The expanded brief dict.

    Returns:
        VideoSpec with all fields populated.
    """
    audience = expanded_brief.get("audience", "parents")
    product = expanded_brief.get("product", "tutoring")
    key_benefit = expanded_brief.get("key_benefit", "personalized learning")
    hook_text = expanded_brief.get("hook_text", "")
    emotional_angles = expanded_brief.get("emotional_angles", ["aspiration"])
    primary_emotion = emotional_angles[0] if emotional_angles else "aspiration"

    pacing = _PACING_MAP.get(primary_emotion, "medium")
    mood = _MOOD_MAP.get(primary_emotion, "uplifting and optimistic")

    # Scene grounded in product and audience
    if audience == "students":
        scene = f"Student confidently preparing for exams with {product}, showing progress"
    else:
        scene = f"Parent and student reviewing {product} results together, celebrating improvement"

    subject_demo = "high school student" if audience == "students" else "parent and teen"

    return VideoSpec(
        hook_action=hook_text or f"Discover how {product} transforms results",
        scene_description=scene,
        pacing=pacing,
        mood=mood,
        subject_demographic=subject_demo,
        text_overlay_content=key_benefit,
        audio_mode="music",
        duration=6,
        aspect_ratio="9:16",
    )


def generate_variant_specs(video_spec: VideoSpec) -> tuple[VideoSpec, VideoSpec]:
    """Generate anchor + alternative variant specs.

    Anchor: direct interpretation of the brief.
    Alternative: different scene/pacing while preserving message.

    Args:
        video_spec: The base video spec.

    Returns:
        Tuple of (anchor_spec, alternative_spec).
    """
    anchor = VideoSpec(
        hook_action=video_spec.hook_action,
        scene_description=video_spec.scene_description,
        pacing=video_spec.pacing,
        mood=video_spec.mood,
        subject_demographic=video_spec.subject_demographic,
        text_overlay_content=video_spec.text_overlay_content,
        audio_mode=video_spec.audio_mode,
        duration=video_spec.duration,
        aspect_ratio=video_spec.aspect_ratio,
    )

    alt_pacing = _ALT_PACING.get(video_spec.pacing, "medium")
    alt_scene = video_spec.scene_description.replace(
        "preparing for exams", "studying at home"
    ).replace(
        "reviewing", "discussing"
    )

    alternative = VideoSpec(
        hook_action=video_spec.hook_action,
        scene_description=alt_scene,
        pacing=alt_pacing,
        mood=video_spec.mood,
        subject_demographic=video_spec.subject_demographic,
        text_overlay_content=video_spec.text_overlay_content,
        audio_mode=video_spec.audio_mode,
        duration=video_spec.duration,
        aspect_ratio=video_spec.aspect_ratio,
    )

    return anchor, alternative
