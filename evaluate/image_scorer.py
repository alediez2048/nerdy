"""Image quality scorer — 5-dimension visual evaluation via Gemini multimodal (PD-13).

Scores images on visual clarity, brand consistency, emotional impact,
copy-image coherence, and platform fit. Runs as a second pass after the
existing binary attribute gate (image_evaluator.py) — this measures
*how good* the image is, not whether it passes.
"""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from iterate.retry import retry_with_backoff

logger = logging.getLogger(__name__)

IMAGE_DIMENSIONS = (
    "visual_clarity",
    "brand_consistency",
    "emotional_impact",
    "copy_image_coherence",
    "platform_fit",
)


@dataclass
class ImageScoreResult:
    """Result of scoring an image on 5 quality dimensions."""

    ad_id: str
    image_path: str
    scores: dict[str, float]
    avg_score: float
    rationales: dict[str, str]
    tokens_consumed: int = 0


def _build_prompt(ad_copy: dict[str, Any], session_config: dict[str, Any] | None) -> str:
    """Build the Gemini prompt for image quality scoring."""
    headline = ad_copy.get("headline", "")
    primary_text = ad_copy.get("primary_text", "")
    cta_button = ad_copy.get("cta_button", "")

    audience = ""
    persona = ""
    if session_config:
        audience = session_config.get("audience", "")
        persona = session_config.get("persona", "")

    audience_context = f"\nTarget audience: {audience}" if audience else ""
    persona_context = f"\nPersona: {persona}" if persona else ""

    return f"""You are a strict visual ad quality evaluator for Varsity Tutors SAT test prep campaigns.

You are scoring AI-GENERATED images, not human photography. Be critical. Most AI-generated ad images are mediocre — generic compositions, flat emotions, stock-photo aesthetics. A score of 7 should be genuinely good. A score of 9-10 should be exceptional and rare.

CALIBRATION: Your scores should average around 5-6 across a batch. If you find yourself scoring everything 8+, you are being too lenient. Push yourself to differentiate — find specific flaws.

BRAND CONTEXT:
- Brand: Varsity Tutors (Nerdy)
- Product: SAT test prep, 1-on-1 tutoring
- Brand palette: teal (#17e2ea), dark navy (#0a2240), white
- Tone: empowering, knowledgeable, approachable, results-focused{audience_context}{persona_context}

AD COPY (for coherence evaluation):
- Headline: {headline or "(none)"}
- Primary Text: {primary_text or "(none)"}
- CTA: {cta_button or "(none)"}

SCORING DIMENSIONS (be strict — use the full 1-10 range):

1. visual_clarity — Is the subject immediately identifiable within 1 second?
   1-3: Multiple competing focal points, confusing layout, unclear subject
   4-5: Subject identifiable but composition is generic or cluttered
   6-7: Clear focal point, clean composition, minor issues
   8-10: Striking composition that commands attention — RARE for AI images

2. brand_consistency — Does this look like a Varsity Tutors ad specifically?
   1-3: Could be any brand — no education context, wrong colors, wrong tone
   4-5: Generic education imagery — looks like stock photo, not brand-specific
   6-7: Appropriate education context but missing brand-specific elements (teal palette, tutoring setting)
   8-10: Unmistakably Varsity Tutors — would recognize without the logo. VERY rare.
   PENALTY: AI-generated faces with uncanny valley features → max 5

3. emotional_impact — Does the image make you FEEL something specific?
   1-3: Flat, lifeless, generic stock-photo energy — no emotional response
   4-5: Mildly pleasant but forgettable — "nice image" but won't stop a scroll
   6-7: Evokes a recognizable emotion (aspiration, determination, warmth)
   8-10: Emotionally compelling — you can feel the student's journey. EXCEPTIONAL.
   PENALTY: Generic smiling person with no context → max 4

4. copy_image_coherence — Does the visual SPECIFICALLY reinforce the ad text?
   1-3: Image has nothing to do with the copy message — random visual
   4-5: Loosely related (both about education) but image doesn't amplify the specific message
   6-7: Image supports the copy's theme and emotional register
   8-10: Image and copy tell the exact same story — removing either would lose meaning
   PENALTY: Generic student image paired with specific copy about score improvement → max 5

5. platform_fit — Would this ACTUALLY perform well in a mobile Instagram/Facebook feed?
   1-3: Would get scrolled past — boring thumbnail, bad aspect ratio usage, tiny details
   4-5: Acceptable but wouldn't stop a scroll — no visual hook in the first 0.5s
   6-7: Good mobile composition, readable at small size, decent use of space
   8-10: Scroll-stopping — designed for thumb-zone, high contrast, immediate impact

Return ONLY valid JSON (no markdown, no code fences):
{{
  "visual_clarity": {{"score": N, "rationale": "..."}},
  "brand_consistency": {{"score": N, "rationale": "..."}},
  "emotional_impact": {{"score": N, "rationale": "..."}},
  "copy_image_coherence": {{"score": N, "rationale": "..."}},
  "platform_fit": {{"score": N, "rationale": "..."}}
}}"""


def _parse_response(text: str) -> dict[str, Any]:
    """Parse Gemini JSON response, handling markdown fences."""
    stripped = text.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", stripped)
    if match:
        stripped = match.group(1).strip()
    return json.loads(stripped)


def score_image(
    image_path: str,
    ad_copy: dict[str, Any],
    ad_id: str = "",
    session_config: dict[str, Any] | None = None,
) -> ImageScoreResult:
    """Score an image on 5 quality dimensions via Gemini multimodal.

    Requires the image file to exist on disk. Returns zero scores if
    the file is missing or the API call fails.
    """
    if not Path(image_path).exists():
        logger.warning("Image file not found for scoring: %s", image_path)
        return _empty_result(ad_id, image_path)

    prompt = _build_prompt(ad_copy, session_config)

    def _do_call() -> ImageScoreResult:
        from google import genai

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY not set")

        client = genai.Client(api_key=api_key)
        image_file = client.files.upload(file=image_path)

        from generate.gemini_client import call_gemini_multimodal
        resp = call_gemini_multimodal(
            [image_file, prompt], temperature=0.2, max_output_tokens=1024
        )
        return _build_result(resp.text, resp.total_tokens, ad_id, image_path)

    try:
        return retry_with_backoff(_do_call)
    except Exception as e:
        logger.warning("Image scoring failed for %s: %s", ad_id, e)
        return _empty_result(ad_id, image_path)


def _build_result(
    response_text: str, tokens: int, ad_id: str, image_path: str
) -> ImageScoreResult:
    """Parse Gemini response into ImageScoreResult."""
    try:
        parsed = _parse_response(response_text)
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning("Failed to parse image score response: %s", e)
        return _empty_result(ad_id, image_path, tokens)

    scores: dict[str, float] = {}
    rationales: dict[str, str] = {}

    for dim in IMAGE_DIMENSIONS:
        val = parsed.get(dim, {})
        if isinstance(val, dict):
            scores[dim] = float(val.get("score", 0))
            rationales[dim] = str(val.get("rationale", ""))
        elif isinstance(val, (int, float)):
            scores[dim] = float(val)
            rationales[dim] = ""
        else:
            scores[dim] = 0.0
            rationales[dim] = ""

    valid_scores = [s for s in scores.values() if s > 0]
    avg = sum(valid_scores) / len(valid_scores) if valid_scores else 0.0

    return ImageScoreResult(
        ad_id=ad_id,
        image_path=image_path,
        scores=scores,
        avg_score=round(avg, 2),
        rationales=rationales,
        tokens_consumed=tokens,
    )


def _empty_result(
    ad_id: str, image_path: str, tokens: int = 0
) -> ImageScoreResult:
    """Return a zero-scored result for error cases."""
    return ImageScoreResult(
        ad_id=ad_id,
        image_path=image_path,
        scores={dim: 0.0 for dim in IMAGE_DIMENSIONS},
        avg_score=0.0,
        rationales={dim: "" for dim in IMAGE_DIMENSIONS},
        tokens_consumed=tokens,
    )
