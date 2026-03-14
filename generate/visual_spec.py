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
from dataclasses import dataclass, field
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


def extract_visual_spec(
    expanded_brief: dict[str, Any],
    campaign_goal: str,
    audience: str,
    ad_id: str,
) -> VisualSpec:
    """Extract a structured visual spec from an expanded brief.

    Args:
        expanded_brief: The expanded brief dict.
        campaign_goal: "awareness" or "conversion".
        audience: "parents" or "students".
        ad_id: The ad identifier.

    Returns:
        VisualSpec with all fields populated.
    """
    brief_id = expanded_brief.get("brief_id", "unknown")

    mood = "aspirational, warm, community-oriented" if campaign_goal == "awareness" else "action-oriented, focused, achievement-driven"
    subject_hint = "family or parent-child study scenes" if audience == "parents" else "peer study groups or individual student achievement"

    prompt = f"""Extract a structured visual specification for an education/tutoring ad image.

Brief context:
- Product: {expanded_brief.get('product', 'SAT prep tutoring')}
- Audience: {audience}
- Campaign goal: {campaign_goal}
- Key message: {expanded_brief.get('key_message', '')}

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

    return VisualSpec(
        ad_id=ad_id,
        brief_id=brief_id,
        subject=raw.get("subject", "Student studying"),
        setting=raw.get("setting", "Study environment"),
        color_palette=color_palette,
        composition=raw.get("composition", "Centered, balanced"),
        campaign_goal_cue=raw.get("campaign_goal_cue", mood),
        text_overlay=raw.get("text_overlay", ""),
    )


def build_image_prompt(spec: VisualSpec, variant_type: str) -> str:
    """Convert a visual spec into a text prompt for image generation.

    Args:
        spec: The VisualSpec to convert.
        variant_type: One of "anchor", "tone_shift", "composition_shift".

    Returns:
        Text prompt for Nano Banana Pro.
    """
    base = (
        f"Professional education advertisement photo. "
        f"Subject: {spec.subject}. "
        f"Setting: {spec.setting}. "
        f"Color palette: {', '.join(spec.color_palette)}. "
        f"Composition: {spec.composition}. "
        f"Mood: {spec.campaign_goal_cue}. "
        f"Style: Clean, modern, professional photography for social media ad."
    )

    modifier = _VARIANT_MODIFIERS.get(variant_type, "")
    if modifier:
        base = f"{base}\n\nVariant adjustment: {modifier}"

    base = f"{base}\n\nNegative: {spec.negative_prompt}"

    return base
