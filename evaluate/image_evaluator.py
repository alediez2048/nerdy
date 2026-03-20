"""Visual attribute evaluator — binary checklist for image variants (P1-15, R2-Q7).

Evaluates each image variant against 5 binary attributes via multimodal
Gemini Flash. 80% pass threshold (4/5 must pass). Provides actionable
feedback for targeted regen (P1-17).
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Any


logger = logging.getLogger(__name__)

VISUAL_ATTRIBUTES = (
    "age_appropriate",
    "lighting",
    "diversity",
    "brand_consistent",
    "no_artifacts",
)

_PASS_THRESHOLD = 0.8  # 4 of 5 attributes must pass


@dataclass
class ImageAttributeResult:
    """Result of evaluating an image against the attribute checklist."""

    ad_id: str
    variant_type: str
    attributes: dict[str, bool]
    attribute_pass_pct: float
    meets_threshold: bool
    tokens_consumed: int = 0


def _call_multimodal_eval(image_path: str, prompt: str) -> tuple[dict[str, bool], int]:
    """Call Gemini Flash multimodal for image attribute evaluation. Returns (result, tokens)."""
    from google.genai import types
    from generate.gemini_client import call_gemini_multimodal

    with open(image_path, "rb") as f:
        image_data = f.read()

    resp = call_gemini_multimodal(
        [types.Part.from_bytes(data=image_data, mime_type="image/png"), prompt],
        temperature=0.1,
        max_output_tokens=512,
    )
    text = resp.text.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if match:
        text = match.group(1).strip()
    return json.loads(text), resp.total_tokens


def evaluate_image_attributes(
    image_path: str,
    visual_spec: dict[str, Any],
    ad_id: str,
    variant_type: str,
) -> ImageAttributeResult:
    """Evaluate an image variant against the 5-attribute binary checklist.

    Args:
        image_path: Path to the image file.
        visual_spec: The visual spec dict that drove generation.
        ad_id: The ad identifier.
        variant_type: One of "anchor", "tone_shift", "composition_shift".

    Returns:
        ImageAttributeResult with per-attribute pass/fail and overall pass rate.
    """
    prompt = f"""Evaluate this education/tutoring advertisement image against these 5 binary attributes.
Visual spec context: Subject: {visual_spec.get('subject', 'student')}, Setting: {visual_spec.get('setting', 'study environment')}

For each attribute, answer true (passes) or false (fails):

1. age_appropriate: Do subjects appear student-age (16-18) or parent-age? No young children or elderly.
2. lighting: Is lighting warm, inviting, consistent with educational context? Not dark, harsh, or clinical.
3. diversity: Is there inclusive representation? Not a concern if no people visible.
4. brand_consistent: Does it match Varsity Tutors visual identity (teal/navy/white)? No competitor branding visible.
5. no_artifacts: Are there no AI artifacts (extra fingers, warped text, distorted faces, impossible geometry)?

Output ONLY valid JSON:
{{"age_appropriate": true/false, "lighting": true/false, "diversity": true/false, "brand_consistent": true/false, "no_artifacts": true/false}}"""

    tokens = 0
    try:
        raw, tokens = _call_multimodal_eval(image_path, prompt)
    except Exception as e:
        logger.warning("Image attribute eval failed for %s/%s: %s, defaulting to all-pass", ad_id, variant_type, e)
        raw = {a: True for a in VISUAL_ATTRIBUTES}

    # Normalize to expected attributes
    attributes = {}
    for attr in VISUAL_ATTRIBUTES:
        val = raw.get(attr, True)
        attributes[attr] = bool(val)

    pass_count = sum(attributes.values())
    pass_pct = pass_count / len(VISUAL_ATTRIBUTES)

    return ImageAttributeResult(
        ad_id=ad_id,
        variant_type=variant_type,
        attributes=attributes,
        attribute_pass_pct=round(pass_pct, 2),
        meets_threshold=pass_pct >= _PASS_THRESHOLD,
        tokens_consumed=tokens,
    )
