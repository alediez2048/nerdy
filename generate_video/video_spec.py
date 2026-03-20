"""Video spec builder for Kling 2.6 (PC-01).

Converts session config (persona, key message, 8-part framework fields)
into a VideoSpec and assembles a Kling-ready prompt string.
"""

from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from iterate.retry import retry_with_backoff

logger = logging.getLogger(__name__)

BRAND_SAFETY_NEGATIVE = "blur, distort, low quality, brand logos, trademarks, competitor names"


def _debug_log(hypothesis_id: str, location: str, message: str, data: dict[str, Any]) -> None:
    # region agent log
    try:
        debug_path = Path("/app/.cursor/debug-c163a9.log")
        debug_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "sessionId": "c163a9",
            "runId": "pre-fix",
            "hypothesisId": hypothesis_id,
            "location": location,
            "message": message,
            "data": data,
            "timestamp": int(time.time() * 1000),
        }
        with debug_path.open("a") as f:
            f.write(json.dumps(payload) + "\n")
    except Exception:
        pass
    # endregion


@dataclass
class VideoSpec:
    """Structured video specification for Kling 2.6 generation."""

    scene: str
    visual_style: str
    camera_movement: str
    subject_action: str
    setting: str
    lighting_mood: str
    audio_mode: str
    audio_detail: str
    color_palette: str
    negative_prompt: str
    duration: int
    aspect_ratio: str
    text_overlay_sequence: list[str] = field(default_factory=list)
    persona: str = "auto"
    campaign_goal: str = "conversion"
    spec_extraction_tokens: int = 0


_PERSONA_VIDEO_DIRECTION: dict[str, str] = {
    "athlete_recruit": (
        "Fast-paced, competitive energy. Campus or athletic field setting. "
        "Handheld camera, dynamic tracking. Student in athletic context — "
        "showing ambition, SAT prep alongside sports. Energetic, motivating mood."
    ),
    "suburban_optimizer": (
        "Calm, organized progression. Clean home study space. Steady camera, "
        "slow dolly-in. Parent and student reviewing results side by side. "
        "Before/after score progression. Professional, optimistic tone."
    ),
    "immigrant_navigator": (
        "Warm family scenes, step-by-step progression. Welcoming home or "
        "library setting. Medium shot, reassuring. Multicultural family "
        "navigating the process together. Supportive, guiding mood."
    ),
    "cultural_investor": (
        "Technology-focused, data overlays. Modern study setup, clean lines. "
        "Dolly-in camera. Student consolidating multiple resources into one "
        "platform. Efficient, sophisticated tone."
    ),
    "system_optimizer": (
        "Data dashboard aesthetic, minimal motion. Fast cuts between metrics. "
        "Static or slow-motion camera. Score charts, clean typography. "
        "McKinsey one-pager feel. Precise, analytical mood."
    ),
    "neurodivergent_advocate": (
        "Warm, inclusive 1:1 tutoring. Comfortable home or quiet space. "
        "Slow-motion or steady camera. Patient tutor and engaged student. "
        "Calm lighting, adaptive environment. Understanding, supportive mood."
    ),
    "burned_returner": (
        "Transformation story with contrast. Before: frustration, low scores. "
        "After: confidence, improvement. Tracking shot following journey. "
        "Fresh start energy, new beginning aesthetic."
    ),
}


def _has_explicit_fields(config: dict[str, Any]) -> bool:
    """True if the user provided at least scene + subject_action."""
    return bool(config.get("video_scene", "").strip()) and bool(
        config.get("video_subject_action", "").strip()
    )


def _call_gemini_for_video_spec(prompt: str) -> tuple[dict[str, Any], int]:
    """Call Gemini Flash to auto-derive video spec fields. Returns (parsed_json, total_tokens)."""
    from generate.gemini_client import call_gemini

    def _do_call() -> tuple[dict[str, Any], int]:
        resp = call_gemini(prompt, model="gemini-2.0-flash", temperature=0.4, max_output_tokens=1024)
        text = resp.text or ""
        stripped = text.strip()
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", stripped)
        if match:
            stripped = match.group(1).strip()
        return json.loads(stripped), resp.total_tokens

    return retry_with_backoff(_do_call)


def _auto_derive_spec(
    brief: dict[str, Any],
    config: dict[str, Any],
) -> tuple[dict[str, Any], int]:
    """Use Gemini Flash to generate the 8-part framework from persona + brief."""
    persona = config.get("persona", "auto")
    audience = config.get("audience", "parents")
    campaign_goal = config.get("campaign_goal", "conversion")
    key_message = config.get("key_message", "") or brief.get("key_message", "")

    persona_hint = _PERSONA_VIDEO_DIRECTION.get(persona, "")
    if not persona_hint:
        persona_hint = (
            "General education ad. Student studying or family discussing test prep. "
            "Warm, encouraging, professional. UGC realistic style."
        )

    prompt = f"""Generate a video specification for a Varsity Tutors SAT test prep ad.

Audience: {audience}
Campaign goal: {campaign_goal}
Key message: {key_message}
Product: {brief.get('product', 'SAT Tutoring')}
Persona direction: {persona_hint}

Output ONLY valid JSON with these exact keys:
{{
  "scene": "<one-sentence summary of the scene>",
  "visual_style": "<e.g. UGC realistic, cinematic, phone-captured>",
  "camera_movement": "<e.g. handheld, dolly-in, tracking, static, slow-motion>",
  "subject_action": "<who is in the scene and what they are doing>",
  "setting": "<location, time of day, environment>",
  "lighting_mood": "<lighting style and emotional tone>",
  "audio_detail": "<ambient sounds or silence>",
  "color_palette": "<colors, brand colors if applicable>"
}}"""

    try:
        result, spec_tokens = _call_gemini_for_video_spec(prompt)
        # region agent log
        _debug_log(
            "H6",
            "generate_video/video_spec.py:_auto_derive_spec",
            "auto-derived spec response",
            {
                "result_type": type(result).__name__,
                "is_dict": isinstance(result, dict),
                "is_list": isinstance(result, list),
                "keys": sorted(list(result.keys())) if isinstance(result, dict) else [],
                "length": len(result) if isinstance(result, (list, dict, str)) else None,
            },
        )
        # endregion
        if not isinstance(result, dict):
            raise ValueError(f"Auto-derived video spec must be a dict, got {type(result).__name__}")
        return result, spec_tokens
    except Exception as e:
        logger.warning("Auto-derive video spec failed: %s — using persona defaults", e)
        return {
            "scene": f"Student preparing for SAT exam with Varsity Tutors — {key_message}",
            "visual_style": "UGC realistic, shot on phone",
            "camera_movement": "handheld",
            "subject_action": f"Student studying, showing progress — {key_message}",
            "setting": "Bright home study area, afternoon sunlight",
            "lighting_mood": "Natural, warm, encouraging",
            "audio_detail": "",
            "color_palette": "#17e2ea, #0a2240",
        }, 0


def build_video_spec(
    expanded_brief: dict[str, Any],
    session_config: dict[str, Any],
    ad_copy: dict[str, Any],
) -> VideoSpec:
    """Build a VideoSpec from session config + brief + ad copy.

    If user provided explicit 8-part fields, use them directly.
    If fields are empty, auto-derive from persona + brief via Gemini Flash.
    """
    # region agent log
    _debug_log(
        "H2",
        "generate_video/video_spec.py:build_video_spec:inputs",
        "build_video_spec inputs",
        {
            "ad_copy_type": type(ad_copy).__name__,
            "ad_copy_keys": sorted(list(ad_copy.keys())) if isinstance(ad_copy, dict) else [],
            "brief_id": expanded_brief.get("brief_id", ""),
            "has_explicit_fields": _has_explicit_fields(session_config),
        },
    )
    # endregion
    spec_tokens = 0
    if _has_explicit_fields(session_config):
        derived = {}
        scene = session_config.get("video_scene", "").strip()
        visual_style = session_config.get("video_visual_style", "").strip() or "UGC realistic"
        camera_movement = session_config.get("video_camera_movement", "").strip() or "handheld"
        subject_action = session_config.get("video_subject_action", "").strip()
        setting = session_config.get("video_setting", "").strip() or "Bright study environment"
        lighting_mood = session_config.get("video_lighting_mood", "").strip() or "Natural, warm"
        audio_detail = session_config.get("video_audio_detail", "").strip()
        color_palette = session_config.get("video_color_palette", "").strip() or "#17e2ea, #0a2240"
    else:
        derived, spec_tokens = _auto_derive_spec(expanded_brief, session_config)
        scene = derived.get("scene", "Student studying for SAT")
        visual_style = derived.get("visual_style", "UGC realistic")
        camera_movement = derived.get("camera_movement", "handheld")
        subject_action = derived.get("subject_action", "Student at desk")
        setting = derived.get("setting", "Home study area")
        lighting_mood = derived.get("lighting_mood", "Natural, warm")
        audio_detail = derived.get("audio_detail", "")
        color_palette = derived.get("color_palette", "#17e2ea, #0a2240")

    user_negative = session_config.get("video_negative_prompt", "").strip()
    negative_prompt = user_negative if user_negative else BRAND_SAFETY_NEGATIVE

    text_overlay = [
        ad_copy.get("primary_text", ""),
        ad_copy.get("headline", ""),
        ad_copy.get("cta_button", ""),
    ]

    spec = VideoSpec(
        scene=scene,
        visual_style=visual_style,
        camera_movement=camera_movement,
        subject_action=subject_action,
        setting=setting,
        lighting_mood=lighting_mood,
        audio_mode=session_config.get("video_audio_mode", "silent"),
        audio_detail=audio_detail,
        color_palette=color_palette,
        negative_prompt=negative_prompt,
        duration=session_config.get("video_duration", 8),
        aspect_ratio=session_config.get("video_aspect_ratio", "9:16"),
        text_overlay_sequence=text_overlay,
        persona=session_config.get("persona", "auto"),
        campaign_goal=session_config.get("campaign_goal", "conversion"),
        spec_extraction_tokens=spec_tokens,
    )
    # region agent log
    _debug_log(
        "H9",
        "generate_video/video_spec.py:build_video_spec:output",
        "built video spec",
        {
            "brief_id": expanded_brief.get("brief_id", ""),
            "visual_style": spec.visual_style,
            "camera_movement": spec.camera_movement,
            "lighting_mood": spec.lighting_mood,
            "color_palette": spec.color_palette,
            "duration": spec.duration,
            "aspect_ratio": spec.aspect_ratio,
            "has_high_contrast_keyword": "contrast" in spec.lighting_mood.lower() or "dramatic" in spec.lighting_mood.lower(),
        },
    )
    # endregion
    return spec


def build_kling_prompt(spec: VideoSpec) -> str:
    """Assemble VideoSpec into a Kling-ready prompt string (100–150 words).

    Structure: subject/action first, then scene context, style, camera,
    setting, lighting, audio cues, color palette, brand instructions.
    The negative_prompt field is NOT included — it goes as a separate API param.
    """
    parts = []

    if spec.subject_action:
        parts.append(spec.subject_action.rstrip(".") + ".")

    if spec.scene and spec.scene != spec.subject_action:
        parts.append(f"Scene: {spec.scene.rstrip('.')}.")

    if spec.visual_style:
        parts.append(f"Visual style: {spec.visual_style.rstrip('.')}.")

    if spec.camera_movement:
        parts.append(f"Camera: {spec.camera_movement.rstrip('.')}.")

    if spec.setting:
        parts.append(f"Setting: {spec.setting.rstrip('.')}.")

    if spec.lighting_mood:
        parts.append(f"Lighting and mood: {spec.lighting_mood.rstrip('.')}.")

    if spec.audio_mode == "with_audio" and spec.audio_detail:
        parts.append(f"Audio: {spec.audio_detail.rstrip('.')}.")

    if spec.color_palette:
        parts.append(f"Color palette: {spec.color_palette.rstrip('.')}.")

    parts.append(
        "Characters wear unbranded, generic clothing. "
        "No visible logos, text, or watermarks in the scene."
    )

    prompt = " ".join(parts)
    # region agent log
    _debug_log(
        "H10",
        "generate_video/video_spec.py:build_kling_prompt",
        "built video prompt",
        {
            "visual_style": spec.visual_style,
            "camera_movement": spec.camera_movement,
            "lighting_mood": spec.lighting_mood,
            "prompt_preview": prompt[:240],
            "has_dramatic_keyword": "dramatic" in prompt.lower(),
            "has_contrast_keyword": "contrast" in prompt.lower(),
            "has_cool_keyword": "cool" in prompt.lower(),
        },
    )
    # endregion
    return prompt
