"""Text-image coherence checker — multimodal verification (P1-16, PRD 4.6).

Scores each copy + image pair across 4 coherence dimensions (1-10).
Coherence avg < 6.0 = incoherent. Feeds into Pareto selection at 60% weight.
Shared semantic brief (R1-Q10) prevents incoherence by design; this verifies.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Any


logger = logging.getLogger(__name__)

COHERENCE_DIMENSIONS = (
    "message_alignment",
    "audience_match",
    "emotional_consistency",
    "visual_narrative",
)

_INCOHERENCE_THRESHOLD = 6.0


@dataclass
class CoherenceResult:
    """Result of evaluating text-image coherence for one variant."""

    ad_id: str
    variant_type: str
    dimension_scores: dict[str, float]
    coherence_avg: float
    tokens_consumed: int = 0


def _call_coherence_eval(image_path: str, prompt: str) -> tuple[dict[str, float], int]:
    """Call Gemini Flash multimodal for coherence evaluation. Returns (result, tokens)."""
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


def check_coherence(
    copy: dict[str, Any],
    image_path: str,
    ad_id: str,
    variant_type: str,
) -> CoherenceResult:
    """Evaluate text-image coherence for a copy + image pair.

    Args:
        copy: Ad copy dict with headline, body, cta fields.
        image_path: Path to the image file.
        ad_id: The ad identifier.
        variant_type: One of "anchor", "tone_shift", "composition_shift".

    Returns:
        CoherenceResult with per-dimension scores and average.
    """
    headline = copy.get("headline", "")
    body = copy.get("body", "")
    cta = copy.get("cta", "")

    prompt = f"""Evaluate how well this advertisement image matches its ad copy.

Ad copy:
- Headline: {headline}
- Body: {body}
- CTA: {cta}

Score each coherence dimension from 1 (completely mismatched) to 10 (perfectly aligned):

1. message_alignment: Does the image reinforce the ad's core message?
2. audience_match: Does the image appeal to the target audience (parents/students)?
3. emotional_consistency: Does the image's emotional tone match the copy's tone?
4. visual_narrative: Does the image tell a story consistent with the ad's value proposition?

Output ONLY valid JSON:
{{"message_alignment": <1-10>, "audience_match": <1-10>, "emotional_consistency": <1-10>, "visual_narrative": <1-10>}}"""

    tokens = 0
    try:
        raw, tokens = _call_coherence_eval(image_path, prompt)
    except Exception as e:
        logger.warning(
            "Coherence eval failed for %s/%s: %s, defaulting to mid-range",
            ad_id, variant_type, e,
        )
        raw = {d: 5.0 for d in COHERENCE_DIMENSIONS}

    dimension_scores: dict[str, float] = {}
    for dim in COHERENCE_DIMENSIONS:
        val = raw.get(dim, 5.0)
        dimension_scores[dim] = float(min(10.0, max(1.0, float(val))))

    coherence_avg = round(
        sum(dimension_scores.values()) / len(COHERENCE_DIMENSIONS), 2
    )

    return CoherenceResult(
        ad_id=ad_id,
        variant_type=variant_type,
        dimension_scores=dimension_scores,
        coherence_avg=coherence_avg,
        tokens_consumed=tokens,
    )


def is_incoherent(result: CoherenceResult) -> bool:
    """Check if a coherence result is below the incoherence threshold.

    Args:
        result: The coherence evaluation result.

    Returns:
        True if coherence_avg < 6.0.
    """
    return result.coherence_avg < _INCOHERENCE_THRESHOLD


def all_variants_incoherent(results: list[CoherenceResult]) -> bool:
    """Check if all variants are incoherent — triggers targeted regen (P1-17).

    Args:
        results: List of coherence results for all variants.

    Returns:
        True if every variant is incoherent.
    """
    return all(is_incoherent(r) for r in results)
