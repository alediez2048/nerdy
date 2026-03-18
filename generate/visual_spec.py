"""Visual spec extraction from expanded briefs (P1-14, PRD 4.6.2, R1-Q10).

Extracts structured visual specifications from expanded briefs using Gemini
Flash. The visual spec drives image generation via Nano Banana Pro.
Shared semantic brief ensures text-image coherence by design.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
from dataclasses import dataclass
from typing import Any

from iterate.retry import retry_with_backoff

logger = logging.getLogger(__name__)

# Varsity Tutors brand colors
_BRAND_COLORS = ["#00838F", "#1A237E", "#FFFFFF"]

_VARIANT_MODIFIERS = {
    "anchor": "",
    "tone_shift": (
        "Adjust the emotional register: warmer lighting, softer color tones, "
        "more aspirational and encouraging expression. Keep the same subject "
        "and setting but shift the mood to feel more inviting and hopeful."
    ),
    "composition_shift": (
        "Change the framing and composition: if the original is a medium shot, "
        "use a close-up. If centered, use rule-of-thirds offset. If single "
        "subject, add environmental context. Different visual perspective, "
        "same core message."
    ),
}


@dataclass
class VisualSpec:
    """Structured visual specification for image generation."""

    ad_id: str
    brief_id: str
    subject: str
    setting: str
    color_palette: list[str]
    composition: str
    campaign_goal_cue: str
    text_overlay: str
    aspect_ratio: str = "1:1"
    negative_prompt: str = "No competitor branding, no AI artifacts, no text in image"

    def spec_hash(self) -> str:
        """Deterministic hash for cache/dedup."""
        raw = f"{self.subject}|{self.setting}|{self.composition}|{self.campaign_goal_cue}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _call_gemini_for_spec(prompt: str) -> dict[str, Any]:
    """Call Gemini Flash to extract visual spec from brief."""
    from google import genai
    from google.genai import types

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set in environment")

    def _do_call() -> dict[str, Any]:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.3,
                max_output_tokens=1024,
            ),
        )
        text = response.text or ""
        stripped = text.strip()
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", stripped)
        if match:
            stripped = match.group(1).strip()
        return json.loads(stripped)

    return retry_with_backoff(_do_call)


_PERSONA_VISUAL_DIRECTION: dict[str, str] = {
    "athlete_recruit": "Athletic student in sports context — on campus, near practice field, wearing team gear. Competitive energy, scholarship aspiration. Show laptop with SAT prep alongside sports equipment.",
    "suburban_optimizer": "Organized home study space — clean desk, good lighting, focused student with parent nearby. Professional, optimistic. Show diagnostic report or score chart on screen.",
    "immigrant_navigator": "Diverse family learning together — warm, welcoming atmosphere. Multicultural home or library setting. Show guidance and step-by-step support.",
    "cultural_investor": "Modern study setup with multiple resources — tech-forward, books alongside laptop. STEM-oriented student. Show consolidation of tools into one platform.",
    "system_optimizer": "Data dashboard aesthetic — minimal, clean, McKinsey-style. White/light background, sans-serif typography. INPUT/OUTPUT table or score chart. NO lifestyle imagery, NO stock photos of people.",
    "neurodivergent_advocate": "Warm, inclusive 1:1 tutoring scene — comfortable setting, patient tutor, student at ease. Calm lighting, adaptive environment. Show connection and understanding.",
    "burned_returner": "Fresh start transformation — before/after aesthetic. Student gaining confidence, moving from frustration to focus. Show progress and new beginning.",
}


_CREATIVE_BRIEF_DIRECTIONS: dict[str, str] = {
    "gap_report": "Data dashboard aesthetic — INPUT/OUTPUT table, score charts, clean sans-serif. McKinsey one-pager. NO photos, NO lifestyle imagery. White/light background with one accent color.",
    "ugc_testimonial": "UGC-style: phone-captured look, authentic expressions, real parent or student speaking directly to camera. Warm, natural lighting, casual setting.",
    "before_after": "Split-screen before/after: left side shows frustration/low score, right side shows confidence/high score. Clear visual transformation. Score numbers prominent.",
    "lifestyle": "Aspirational lifestyle scene: student celebrating, family together, campus life. Warm lighting, authentic emotions, achievement moments.",
    "stat_focused": "Bold stat as hero element: large number (e.g., '10X', '200+', '$40K'), minimal supporting imagery. Clean typography, high contrast, data-forward.",
}


def extract_visual_spec(
    expanded_brief: dict[str, Any],
    campaign_goal: str,
    audience: str,
    ad_id: str,
    persona: str | None = None,
    creative_brief: str = "auto",
    copy_on_image: bool = False,
    aspect_ratio: str = "1:1",
    headline_text: str = "",
) -> VisualSpec:
    """Extract a structured visual spec from an expanded brief.

    Args:
        expanded_brief: The expanded brief dict.
        campaign_goal: "awareness" or "conversion".
        audience: "parents" or "students".
        ad_id: The ad identifier.
        persona: Optional persona key for persona-specific visual direction.
        creative_brief: Creative brief preset (auto, gap_report, ugc_testimonial, etc.)
        copy_on_image: Whether to include headline text in the image.
        headline_text: Generated ad headline to use as deterministic overlay text.

    Returns:
        VisualSpec with all fields populated.
    """
    brief_id = expanded_brief.get("brief_id", "unknown")

    mood = "aspirational, warm, community-oriented" if campaign_goal == "awareness" else "action-oriented, focused, achievement-driven"
    subject_hint = "family or parent-child study scenes" if audience == "parents" else "peer study groups or individual student achievement"

    # PB-10: Persona-specific visual direction overrides generic hints
    persona_direction = ""
    if persona and persona in _PERSONA_VISUAL_DIRECTION:
        persona_direction = f"\nPERSONA CREATIVE DIRECTION (override generic guidance with this):\n{_PERSONA_VISUAL_DIRECTION[persona]}"
        subject_hint = _PERSONA_VISUAL_DIRECTION[persona].split(".")[0]

    # PB-11: Creative brief preset overrides persona direction
    brief_direction = ""
    if creative_brief and creative_brief != "auto" and creative_brief in _CREATIVE_BRIEF_DIRECTIONS:
        brief_direction = f"\nCREATIVE BRIEF STYLE (highest priority — override all other visual guidance):\n{_CREATIVE_BRIEF_DIRECTIONS[creative_brief]}"

    # PB-11: Copy on image
    text_overlay_hint = ""
    if copy_on_image:
        text_overlay_hint = "\nINCLUDE TEXT OVERLAY: Generate text_overlay with the ad headline. The image MUST include readable text."

    prompt = f"""Extract a structured visual specification for an education/tutoring ad image.

Brief context:
- Product: {expanded_brief.get('product', 'SAT Tutoring')}
- Audience: {audience}
- Campaign goal: {campaign_goal}
- Key message: {expanded_brief.get('key_message', '')}
{persona_direction}
{brief_direction}
{text_overlay_hint}

Brand colors: {', '.join(_BRAND_COLORS)} (teal, navy, white)
Mood: {mood}
Subject guidance: {subject_hint}

Output ONLY valid JSON:
{{
  "subject": "<demographic, activity, emotional expression>",
  "setting": "<location, lighting, time of day>",
  "color_palette": ["<brand colors + mood accents>"],
  "composition": "<framing, perspective, depth of field>",
  "campaign_goal_cue": "<visual cue matching campaign goal>",
  "text_overlay": "<headline text if applicable, empty string if none>"
}}"""

    try:
        raw = _call_gemini_for_spec(prompt)
    except Exception as e:
        logger.warning("Visual spec extraction failed for %s: %s, using defaults", ad_id, e)
        raw = {
            "subject": f"Student studying for SAT, {subject_hint}",
            "setting": "Bright study environment, natural lighting",
            "color_palette": _BRAND_COLORS,
            "composition": "Rule of thirds, centered subject",
            "campaign_goal_cue": mood,
            "text_overlay": "",
        }

    color_palette = raw.get("color_palette", _BRAND_COLORS)
    if not isinstance(color_palette, list):
        color_palette = _BRAND_COLORS

    text_overlay = headline_text.strip() if copy_on_image else str(raw.get("text_overlay", "")).strip()
    negative_prompt = "No competitor branding, no AI artifacts"
    if not copy_on_image:
        negative_prompt = f"{negative_prompt}, no text in image"

    spec = VisualSpec(
        ad_id=ad_id,
        brief_id=brief_id,
        subject=raw.get("subject", "Student studying"),
        setting=raw.get("setting", "Study environment"),
        color_palette=color_palette,
        composition=raw.get("composition", "Centered, balanced"),
        campaign_goal_cue=raw.get("campaign_goal_cue", mood),
        text_overlay=text_overlay,
        aspect_ratio=aspect_ratio,
        negative_prompt=negative_prompt,
    )
    return spec


def build_image_prompt(spec: VisualSpec, variant_type: str, creative_brief: str = "auto") -> str:
    """Convert a visual spec into a text prompt for image generation.

    Args:
        spec: The VisualSpec to convert.
        variant_type: One of "anchor", "tone_shift", "composition_shift".
        creative_brief: Creative brief key for style override.

    Returns:
        Text prompt for Nano Banana Pro.
    """
    style_override = _CREATIVE_BRIEF_DIRECTIONS.get(creative_brief, "")
    if style_override:
        style_line = style_override
    else:
        style_line = "Clean, modern, professional photography for social media ad."

    base = (
        f"Education advertisement image. "
        f"Subject: {spec.subject}. "
        f"Setting: {spec.setting}. "
        f"Color palette: {', '.join(spec.color_palette)}. "
        f"Composition: {spec.composition}. "
        f"Mood: {spec.campaign_goal_cue}. "
        f"Style: {style_line}"
    )

    if spec.text_overlay:
        base = f"{base}\n\nText overlay: Include the following text prominently in the image: \"{spec.text_overlay}\""

    modifier = _VARIANT_MODIFIERS.get(variant_type, "")
    if modifier:
        base = f"{base}\n\nVariant adjustment: {modifier}"

    base = f"{base}\n\nNegative: {spec.negative_prompt}"

    return base
