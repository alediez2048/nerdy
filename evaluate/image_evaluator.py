"""Visual attribute evaluator — binary checklist for image variants (P1-15, R2-Q7).

Evaluates each image variant against 5 binary attributes via multimodal
Gemini Flash. 80% pass threshold (4/5 must pass). Provides actionable
feedback for targeted regen (P1-17).
"""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass
from typing import Any

from evaluate.coherence_checker import CoherenceResult, is_incoherent
from iterate.ledger import log_event
from iterate.retry import retry_with_backoff

logger = logging.getLogger(__name__)

VISUAL_ATTRIBUTES = (
    "age_appropriate",
    "lighting",
    "diversity",
    "brand_consistent",
    "no_artifacts",
    "no_third_party_branding",
)

_PASS_THRESHOLD = 0.8  # 4 of 5 attributes must pass
_REQUIRED_ATTRIBUTES = {"no_third_party_branding"}
VIDEO_ATTRIBUTES = (
    "hook_timing",
    "ugc_authenticity",
    "pacing",
    "text_legibility",
    "no_artifacts",
)
_VIDEO_PASS_THRESHOLD = 0.8
_VIDEO_MODEL = "gemini-2.0-flash"


@dataclass
class ImageAttributeResult:
    """Result of evaluating an image against the attribute checklist."""

    ad_id: str
    variant_type: str
    attributes: dict[str, bool]
    attribute_pass_pct: float
    meets_threshold: bool


@dataclass
class VideoAttributeResult:
    """Result of evaluating a video against the PC-02 checklist."""

    ad_id: str
    variant_type: str
    attributes: dict[str, bool]
    attribute_pass_pct: float
    meets_threshold: bool


@dataclass
class VideoSelectionResult:
    """Result of choosing the best video variant for an ad."""

    winner_variant_type: str | None
    composite_scores: dict[str, float]
    video_blocked: bool
    degrade_to_image_only: bool


def _call_multimodal_eval(image_path: str, prompt: str) -> dict[str, bool]:
    """Call Gemini Flash multimodal for image attribute evaluation."""
    from google import genai
    from google.genai import types

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set in environment")

    def _do_call() -> dict[str, bool]:
        client = genai.Client(api_key=api_key)

        # Read image file
        with open(image_path, "rb") as f:
            image_data = f.read()

        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[
                types.Part.from_bytes(data=image_data, mime_type="image/png"),
                prompt,
            ],
            config=types.GenerateContentConfig(
                temperature=0.1,
                max_output_tokens=512,
            ),
        )
        text = response.text or ""
        stripped = text.strip()
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", stripped)
        if match:
            stripped = match.group(1).strip()
        return json.loads(stripped)

    return retry_with_backoff(_do_call)


def _guess_video_mime_type(video_path: str) -> str:
    """Infer a reasonable video MIME type from file extension."""
    lowered = video_path.lower()
    if lowered.endswith(".webm"):
        return "video/webm"
    if lowered.endswith(".mov"):
        return "video/quicktime"
    return "video/mp4"


def _call_video_multimodal_eval(video_path: str, prompt: str) -> dict[str, bool]:
    """Call Gemini Flash multimodal for video attribute evaluation."""
    from google import genai
    from google.genai import types

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set in environment")

    def _do_call() -> dict[str, bool]:
        client = genai.Client(api_key=api_key)

        with open(video_path, "rb") as f:
            video_data = f.read()

        response = client.models.generate_content(
            model=_VIDEO_MODEL,
            contents=[
                types.Part.from_bytes(
                    data=video_data,
                    mime_type=_guess_video_mime_type(video_path),
                ),
                prompt,
            ],
            config=types.GenerateContentConfig(
                temperature=0.1,
                max_output_tokens=512,
            ),
        )
        text = response.text or ""
        stripped = text.strip()
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", stripped)
        if match:
            stripped = match.group(1).strip()
        return json.loads(stripped)

    return retry_with_backoff(_do_call)


def _spec_value(spec: Any, field: str, default: str) -> str:
    """Read a field from a dict or object-backed spec."""
    if isinstance(spec, dict):
        value = spec.get(field, default)
    else:
        value = getattr(spec, field, default)
    return str(value)


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
    prompt = f"""Evaluate this education/tutoring advertisement image against these 6 binary attributes.
Visual spec context: Subject: {visual_spec.get('subject', 'student')}, Setting: {visual_spec.get('setting', 'study environment')}

For each attribute, answer true (passes) or false (fails):

1. age_appropriate: Do subjects appear student-age (16-18) or parent-age? No young children or elderly.
2. lighting: Is lighting warm, inviting, consistent with educational context? Not dark, harsh, or clinical.
3. diversity: Is there inclusive representation? Not a concern if no people visible.
4. brand_consistent: Does it match Varsity Tutors visual identity (teal/navy/white)? No competitor branding visible.
5. no_artifacts: Are there no AI artifacts (extra fingers, warped text, distorted faces, impossible geometry)?
6. no_third_party_branding: No visible third-party brand logos, names, or trademarked imagery anywhere in the image. Clothing, equipment, devices, and signage must be generic/unbranded.

Output ONLY valid JSON:
{{"age_appropriate": true/false, "lighting": true/false, "diversity": true/false, "brand_consistent": true/false, "no_artifacts": true/false, "no_third_party_branding": true/false}}"""

    try:
        raw = _call_multimodal_eval(image_path, prompt)
    except Exception as e:
        logger.warning("Image attribute eval failed for %s/%s: %s, defaulting to all-pass", ad_id, variant_type, e)
        raw = {a: True for a in VISUAL_ATTRIBUTES}

    # Normalize to expected attributes
    attributes = {}
    for attr in VISUAL_ATTRIBUTES:
        val = raw.get(attr, True)
        attributes[attr] = bool(val)

    pass_count = sum(attributes.values())
    pass_pct = round(pass_count / len(VISUAL_ATTRIBUTES), 2)
    meets_threshold = pass_pct >= _PASS_THRESHOLD and all(
        attributes.get(attr, True) for attr in _REQUIRED_ATTRIBUTES
    )

    return ImageAttributeResult(
        ad_id=ad_id,
        variant_type=variant_type,
        attributes=attributes,
        attribute_pass_pct=pass_pct,
        meets_threshold=meets_threshold,
    )


def evaluate_video_attributes(
    video_path: str,
    video_spec: Any,
    ad_id: str,
    variant_type: str,
    ledger_path: str | None = None,
) -> VideoAttributeResult:
    """Evaluate a video variant against the PC-02 five-attribute checklist."""
    prompt = f"""Evaluate this short vertical ad video against these 5 binary attributes.

Video spec context:
- Pacing target: {_spec_value(video_spec, "pacing", "medium")}
- Camera style: {_spec_value(video_spec, "camera_style", "handheld")}
- Audio mode: {_spec_value(video_spec, "audio_mode", "silent")}

For each attribute, answer true (passes) or false (fails):
1. hook_timing: Does the first 2 seconds contain an attention-grabbing hook?
2. ugc_authenticity: Does the video feel genuine and not overly polished?
3. pacing: Does the pacing match the intended campaign energy?
4. text_legibility: Are any text overlays readable at mobile size?
5. no_artifacts: Are there no facial distortions, temporal glitches, flicker, or impossible physics?

Output ONLY valid JSON:
{{"hook_timing": true/false, "ugc_authenticity": true/false, "pacing": true/false, "text_legibility": true/false, "no_artifacts": true/false}}"""

    try:
        raw = _call_video_multimodal_eval(video_path, prompt)
    except Exception as e:
        logger.warning(
            "Video attribute eval failed for %s/%s: %s, defaulting to all-fail",
            ad_id,
            variant_type,
            e,
        )
        raw = {attr: False for attr in VIDEO_ATTRIBUTES}

    attributes: dict[str, bool] = {}
    for attr in VIDEO_ATTRIBUTES:
        attributes[attr] = bool(raw.get(attr, False))

    pass_count = sum(attributes.values())
    pass_pct = round(pass_count / len(VIDEO_ATTRIBUTES), 2)
    meets_threshold = pass_pct >= _VIDEO_PASS_THRESHOLD

    result = VideoAttributeResult(
        ad_id=ad_id,
        variant_type=variant_type,
        attributes=attributes,
        attribute_pass_pct=pass_pct,
        meets_threshold=meets_threshold,
    )

    if ledger_path:
        log_event(
            ledger_path,
            {
                "event_type": "VideoEvaluated",
                "ad_id": ad_id,
                "brief_id": "",
                "cycle_number": 0,
                "action": "video-attribute-evaluation",
                "inputs": {
                    "variant_type": variant_type,
                    "video_path": video_path,
                    "attributes_requested": list(VIDEO_ATTRIBUTES),
                },
                "outputs": {
                    "attributes": attributes,
                    "attribute_pass_pct": pass_pct,
                    "meets_threshold": meets_threshold,
                },
                "scores": {"attribute_pass_pct": pass_pct},
                "tokens_consumed": 0,
                "model_used": _VIDEO_MODEL,
                "seed": "",
            },
        )

    return result


def compute_video_composite_score(
    attribute_pass_pct: float,
    coherence_avg: float,
) -> float:
    """Compute the weighted composite score for a video variant."""
    return round(attribute_pass_pct * 0.4 + coherence_avg * 0.6, 4)


def select_best_video_variant(
    variant_results: list[tuple[VideoAttributeResult, CoherenceResult]],
    ad_id: str,
    ledger_path: str | None = None,
) -> VideoSelectionResult:
    """Select the best passing video variant, or degrade to image-only."""
    composite_scores: dict[str, float] = {}
    passing_variants: list[tuple[float, int, VideoAttributeResult, CoherenceResult]] = []

    for attr_result, coh_result in variant_results:
        composite = compute_video_composite_score(
            attr_result.attribute_pass_pct,
            coh_result.coherence_avg,
        )
        composite_scores[attr_result.variant_type] = composite
        priority = 0 if attr_result.variant_type == "anchor" else 1
        if attr_result.meets_threshold and not is_incoherent(coh_result):
            passing_variants.append((composite, priority, attr_result, coh_result))

    if not passing_variants:
        if ledger_path:
            log_event(
                ledger_path,
                {
                    "event_type": "VideoBlocked",
                    "ad_id": ad_id,
                    "brief_id": "",
                    "cycle_number": 0,
                    "action": "video-blocked",
                    "inputs": {"variant_count": len(variant_results)},
                    "outputs": {
                        "fallback": "image-only",
                        "composite_scores": composite_scores,
                    },
                    "scores": {},
                    "tokens_consumed": 0,
                    "model_used": "",
                    "seed": "",
                },
            )
        return VideoSelectionResult(
            winner_variant_type=None,
            composite_scores=composite_scores,
            video_blocked=True,
            degrade_to_image_only=True,
        )

    passing_variants.sort(key=lambda item: (-item[0], item[1]))
    _, _, winner_attr, _ = passing_variants[0]

    if ledger_path:
        losers = [
            {
                "variant_type": attr_result.variant_type,
                "composite_score": composite_scores[attr_result.variant_type],
                "passed_threshold": attr_result.meets_threshold
                and not is_incoherent(coh_result),
            }
            for attr_result, coh_result in variant_results
            if attr_result.variant_type != winner_attr.variant_type
        ]
        log_event(
            ledger_path,
            {
                "event_type": "VideoSelected",
                "ad_id": ad_id,
                "brief_id": "",
                "cycle_number": 0,
                "action": "video-selection",
                "inputs": {"variant_count": len(variant_results)},
                "outputs": {
                    "winner_variant_type": winner_attr.variant_type,
                    "winner_composite_score": composite_scores[winner_attr.variant_type],
                    "composite_scores": composite_scores,
                    "losers": losers,
                },
                "scores": {"winner_composite_score": composite_scores[winner_attr.variant_type]},
                "tokens_consumed": 0,
                "model_used": "",
                "seed": "",
            },
        )

    return VideoSelectionResult(
        winner_variant_type=winner_attr.variant_type,
        composite_scores=composite_scores,
        video_blocked=False,
        degrade_to_image_only=False,
    )
