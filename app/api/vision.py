# Ad-Ops-Autopilot — Brand asset vision probes (PJ-03)
"""Gemini 2.5 Flash multimodal probes per asset_type.

Each probe takes raw file bytes + MIME and returns a structured dict the
LLM can interpret in the next ``/agent/converse`` turn (PJ-04). The
returned shape is documented per-function so PJ-05's ``ingest_asset``
tool can build a consistent confirm-with-user message.

These functions are designed to be called from a Celery task (PJ-03's
``brand_asset_vision_task``) — they're synchronous and may take 10-25s
per call. Do NOT call inline from the FastAPI request thread.

Host-side ``AGENT_GEMINI_API_KEY`` per PJ-00 §3 decision 11 (GRILL Q1):
new users can upload assets before they've added their own BYO key.
"""
from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

logger = logging.getLogger(__name__)

VISION_MODEL = "gemini-2.5-flash"


class VisionConfigError(RuntimeError):
    """AGENT_GEMINI_API_KEY is unset and no GEMINI_API_KEY fallback."""


class VisionProbeError(RuntimeError):
    """Provider call failed in a way callers can't recover from."""


def _agent_key() -> str:
    """Resolve the host-side key. Prefer AGENT_GEMINI_API_KEY; fall back
    to GEMINI_API_KEY for local dev convenience."""
    key = os.getenv("AGENT_GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY") or ""
    if not key:
        raise VisionConfigError(
            "AGENT_GEMINI_API_KEY (or GEMINI_API_KEY fallback) must be set"
        )
    return key


# ---------------------------------------------------------------------------
# Prompts. Each prompt instructs Gemini to return JSON only — no prose.
# ---------------------------------------------------------------------------

LOGO_PROMPT = """\
You are analyzing a brand LOGO image. Return ONLY valid JSON matching this
schema, no prose, no markdown:
{
  "dominant_colors": ["#RRGGBB", "#RRGGBB", "#RRGGBB"],
  "background": "transparent" | "solid" | "photo",
  "detected_fonts": [{"family": "string", "confidence": 0.0-1.0}],
  "notes": "one short sentence describing the mark"
}
Up to 3 dominant_colors ordered most-to-least dominant. detected_fonts is
empty when the logo has no wordmark."""


STYLE_GUIDE_PROMPT = """\
You are reading a brand STYLE GUIDE PDF. Return ONLY valid JSON matching
this schema, no prose, no markdown:
{
  "palette_hex": ["#RRGGBB", ...],
  "font_names": ["string", ...],
  "do_dont_rules": {"do": ["..."], "dont": ["..."]},
  "ocr_text_excerpt": "first 400 chars of meaningful text"
}
Skip cover pages and table of contents. Read the first 3 pages of content."""


REFERENCE_PROMPT = """\
You are analyzing a REFERENCE image (mood board, past ad, competitor
screenshot, etc.). Return ONLY valid JSON, no prose:
{
  "color_tone": "warm | cool | neutral | high-contrast",
  "mood_descriptors": ["aspirational", "minimalist", ...]
}
Up to 5 mood_descriptors as single words / short phrases."""


FONT_PROMPT = """\
You are analyzing a font file. Based on the filename and any rendered
samples visible, return ONLY valid JSON, no prose:
{"font_family": "best guess of family name"}"""


# ---------------------------------------------------------------------------
# Internal Gemini call. Kept local so it picks up AGENT_GEMINI_API_KEY
# rather than the BYO GEMINI_API_KEY the pipeline uses.
# ---------------------------------------------------------------------------


def _call_multimodal(prompt: str, file_bytes: bytes, mime: str) -> str:
    """Make one Gemini 2.5 Flash multimodal call with the host key.

    Returns the raw response text. Caller is responsible for JSON parsing.
    """
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=_agent_key())
    response = client.models.generate_content(
        model=VISION_MODEL,
        contents=[
            types.Part.from_bytes(data=file_bytes, mime_type=mime),
            prompt,
        ],
        config=types.GenerateContentConfig(
            temperature=0.0,
            max_output_tokens=1024,
            # thinking_budget=0 keeps latency in the chat-acceptable window.
            thinking_config=types.ThinkingConfig(thinking_budget=0),
        ),
    )
    return response.text or ""


# ---------------------------------------------------------------------------
# JSON parsing helper — tolerates markdown fences the model sometimes adds.
# ---------------------------------------------------------------------------


def _parse_json(raw: str) -> dict[str, Any]:
    r"""Strip ``\`\`\`json`` fences and parse. Returns ``{"raw": ...}`` on failure."""
    stripped = raw.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", stripped)
    if match:
        stripped = match.group(1).strip()
    try:
        return json.loads(stripped)
    except json.JSONDecodeError as e:
        logger.warning("Vision probe returned non-JSON: %s", e)
        return {"raw": raw, "parse_error": str(e)}


# ---------------------------------------------------------------------------
# Public probe functions. One per asset_type.
# ---------------------------------------------------------------------------


def probe_logo(file_bytes: bytes, mime: str) -> dict[str, Any]:
    """Logo probe → ``{dominant_colors, background, detected_fonts, notes}``."""
    raw = _call_multimodal(LOGO_PROMPT, file_bytes, mime or "image/png")
    return _parse_json(raw)


def probe_style_guide(file_bytes: bytes, mime: str = "application/pdf") -> dict[str, Any]:
    """Style guide PDF probe → ``{palette_hex, font_names, do_dont_rules, ocr_text_excerpt}``."""
    raw = _call_multimodal(STYLE_GUIDE_PROMPT, file_bytes, mime or "application/pdf")
    return _parse_json(raw)


def probe_reference(file_bytes: bytes, mime: str) -> dict[str, Any]:
    """Reference image probe → ``{color_tone, mood_descriptors}``."""
    raw = _call_multimodal(REFERENCE_PROMPT, file_bytes, mime or "image/png")
    return _parse_json(raw)


def probe_font(file_bytes: bytes, filename: str) -> dict[str, Any]:
    """Font file probe → ``{font_family}``. Lighter probe — falls back to
    filename inference when the model has nothing visual to read."""
    fallback = {
        "font_family": os.path.splitext(os.path.basename(filename or ""))[0]
        or "unknown",
    }
    try:
        raw = _call_multimodal(FONT_PROMPT, file_bytes, "font/ttf")
        parsed = _parse_json(raw)
        if "font_family" not in parsed:
            parsed.update(fallback)
        return parsed
    except Exception as e:
        logger.warning("Font probe failed, falling back to filename: %s", e)
        return fallback


# ---------------------------------------------------------------------------
# Dispatch table consumed by the Celery task.
# ---------------------------------------------------------------------------

PROBES = {
    "logo": lambda b, m, f: probe_logo(b, m),
    "style_guide": lambda b, m, f: probe_style_guide(b, m),
    "reference": lambda b, m, f: probe_reference(b, m),
    "font": lambda b, m, f: probe_font(b, f),
}
