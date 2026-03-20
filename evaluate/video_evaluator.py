"""Video attribute evaluator + coherence checker (PC-02).

Separate from image_evaluator.py — different attributes, different thresholds,
different failure modes. Lessons from Veo attempt: never evaluate a missing file.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from iterate.retry import retry_with_backoff

logger = logging.getLogger(__name__)

VIDEO_ATTRIBUTES = (
    "hook_timing",
    "ugc_authenticity",
    "pacing",
    "text_legibility",
    "no_artifacts",
)

_ATTR_PASS_THRESHOLD = 0.8  # 4/5 must pass
_COHERENCE_THRESHOLD = 4.0  # lower than image (6.0) — short UGC clips score lower


@dataclass
class VideoEvalResult:
    """Result of evaluating a video against the attribute checklist."""

    ad_id: str
    variant_type: str
    attributes: dict[str, bool]
    attribute_pass_pct: float
    meets_threshold: bool
    tokens_consumed: int = 0


@dataclass
class VideoCoherenceResult:
    """Result of checking video-to-copy coherence."""

    ad_id: str
    variant_type: str
    dimensions: dict[str, float]
    avg_score: float
    is_coherent: bool
    tokens_consumed: int = 0


def _call_multimodal_video_eval(video_path: str, prompt: str) -> tuple[dict[str, bool], int]:
    """Call Gemini Flash multimodal with video for attribute evaluation."""
    from google.genai import types

    from generate.gemini_client import call_gemini_multimodal

    def _do_call() -> tuple[dict[str, bool], int]:
        with open(video_path, "rb") as f:
            video_data = f.read()

        contents = [
            types.Part.from_bytes(data=video_data, mime_type="video/mp4"),
            prompt,
        ]
        resp = call_gemini_multimodal(
            contents,
            model="gemini-2.0-flash",
            temperature=0.1,
            max_output_tokens=512,
        )
        text = resp.text or ""
        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            parsed = json.loads(match.group(0))
        else:
            parsed = json.loads(text)
        return parsed, resp.total_tokens

    return retry_with_backoff(_do_call)


def _call_coherence_eval(video_path: str, prompt: str) -> tuple[dict[str, float], int]:
    """Call Gemini Flash multimodal for coherence scoring."""
    from google.genai import types

    from generate.gemini_client import call_gemini_multimodal

    def _do_call() -> tuple[dict[str, float], int]:
        with open(video_path, "rb") as f:
            video_data = f.read()

        contents = [
            types.Part.from_bytes(data=video_data, mime_type="video/mp4"),
            prompt,
        ]
        resp = call_gemini_multimodal(
            contents,
            model="gemini-2.0-flash",
            temperature=0.1,
            max_output_tokens=512,
        )
        text = resp.text or ""
        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            parsed = json.loads(match.group(0))
        else:
            parsed = json.loads(text)
        return parsed, resp.total_tokens

    return retry_with_backoff(_do_call)


def evaluate_video_attributes(
    video_path: str,
    video_spec: dict[str, Any],
    ad_id: str,
    variant_type: str,
) -> VideoEvalResult:
    """Evaluate video against 5 binary attributes.

    If video_path does not exist, returns immediate failure — no API call.
    """
    if not Path(video_path).exists():
        logger.warning("Video file missing for %s/%s: %s", ad_id, variant_type, video_path)
        return VideoEvalResult(
            ad_id=ad_id,
            variant_type=variant_type,
            attributes={attr: False for attr in VIDEO_ATTRIBUTES},
            attribute_pass_pct=0.0,
            meets_threshold=False,
            tokens_consumed=0,
        )

    prompt = """Evaluate this video ad for a Varsity Tutors SAT test prep campaign.

Score each attribute as true (pass) or false (fail):

1. hook_timing — Does the video grab attention in the first 2 seconds?
2. ugc_authenticity — Does it feel genuine and authentic (handheld feel, natural lighting)?
3. pacing — Does the pacing match the energy level (appropriate for a social ad)?
4. text_legibility — If text overlays are present, are they readable at mobile size?
5. no_artifacts — Is the video free of facial distortion, temporal glitches, physics violations, and flickering?

Output ONLY valid JSON:
{"hook_timing": true/false, "ugc_authenticity": true/false, "pacing": true/false, "text_legibility": true/false, "no_artifacts": true/false}"""

    eval_tokens = 0
    try:
        raw, eval_tokens = _call_multimodal_video_eval(video_path, prompt)
    except Exception as e:
        logger.warning("Video attribute eval failed for %s/%s: %s", ad_id, variant_type, e)
        raw = {attr: False for attr in VIDEO_ATTRIBUTES}

    attributes = {attr: bool(raw.get(attr, False)) for attr in VIDEO_ATTRIBUTES}
    pass_count = sum(attributes.values())
    pass_pct = pass_count / len(VIDEO_ATTRIBUTES)

    return VideoEvalResult(
        ad_id=ad_id,
        variant_type=variant_type,
        attributes=attributes,
        attribute_pass_pct=pass_pct,
        meets_threshold=pass_pct >= _ATTR_PASS_THRESHOLD,
        tokens_consumed=eval_tokens,
    )


def check_video_coherence(
    ad_copy: dict[str, Any],
    video_path: str,
    ad_id: str,
    variant_type: str,
) -> VideoCoherenceResult:
    """Check video-to-copy coherence across 4 dimensions.

    Threshold is 4.0 (not 6.0 as for images). Short UGC clips inherently
    score lower on traditional coherence metrics.

    If video_path does not exist, returns immediate incoherent result.
    """
    dims = ("message_alignment", "audience_match", "emotional_consistency", "narrative_flow")

    if not Path(video_path).exists():
        logger.warning("Video file missing for coherence %s/%s: %s", ad_id, variant_type, video_path)
        return VideoCoherenceResult(
            ad_id=ad_id,
            variant_type=variant_type,
            dimensions={d: 0.0 for d in dims},
            avg_score=0.0,
            is_coherent=False,
            tokens_consumed=0,
        )

    primary_text = ad_copy.get("primary_text", "")
    headline = ad_copy.get("headline", "")
    cta = ad_copy.get("cta_button", "")

    prompt = f"""Evaluate how well this video matches the ad copy below.

Ad copy:
- Primary text: {primary_text}
- Headline: {headline}
- CTA: {cta}

Score each dimension 1-10:
1. message_alignment — Does the video convey the same message as the copy?
2. audience_match — Is the video appropriate for the target audience?
3. emotional_consistency — Does the video's tone match the copy's emotional register?
4. narrative_flow — Does the video have clear beginning-middle-end within its duration?

Output ONLY valid JSON:
{{"message_alignment": N, "audience_match": N, "emotional_consistency": N, "narrative_flow": N}}"""

    coh_tokens = 0
    try:
        raw, coh_tokens = _call_coherence_eval(video_path, prompt)
    except Exception as e:
        logger.warning("Video coherence check failed for %s/%s: %s", ad_id, variant_type, e)
        raw = {d: 0.0 for d in dims}

    dimensions = {d: float(raw.get(d, 0.0)) for d in dims}
    avg = sum(dimensions.values()) / len(dimensions) if dimensions else 0.0

    return VideoCoherenceResult(
        ad_id=ad_id,
        variant_type=variant_type,
        dimensions=dimensions,
        avg_score=avg,
        is_coherent=avg >= _COHERENCE_THRESHOLD,
        tokens_consumed=coh_tokens,
    )


def compute_composite_score(
    eval_result: VideoEvalResult,
    coherence_result: VideoCoherenceResult,
) -> float:
    """Compute composite video quality score.

    40% attribute pass percentage + 60% normalized coherence (avg/10).
    """
    attr_component = 0.4 * eval_result.attribute_pass_pct
    coh_component = 0.6 * (coherence_result.avg_score / 10.0)
    return attr_component + coh_component
