"""Video quality scorer — 5-dimension video evaluation via Gemini multimodal (PD-14).

Scores videos on hook strength, visual quality, narrative flow,
copy-video coherence, and UGC authenticity. Runs as a second pass after
the existing binary attribute gate (video_evaluator.py) — this measures
*how good* the video is, not whether it passes.

Uses Gemini's native video understanding (upload + analyze frames + audio).
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from iterate.retry import retry_with_backoff

logger = logging.getLogger(__name__)

VIDEO_DIMENSIONS = (
    "hook_strength",
    "visual_quality",
    "narrative_flow",
    "copy_video_coherence",
    "ugc_authenticity",
)


@dataclass
class VideoScoreResult:
    """Result of scoring a video on 5 quality dimensions."""

    ad_id: str
    video_path: str
    scores: dict[str, float]
    avg_score: float
    rationales: dict[str, str]
    tokens_consumed: int = 0


def _build_prompt(ad_copy: dict[str, Any], session_config: dict[str, Any] | None) -> str:
    """Build the Gemini prompt for video quality scoring."""
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

    return f"""You are a video ad quality evaluator for Varsity Tutors SAT test prep campaigns.

Evaluate this ad video on 5 dimensions. Score each 1-10 with a one-sentence rationale.

BRAND CONTEXT:
- Brand: Varsity Tutors (Nerdy)
- Product: SAT test prep, 1-on-1 tutoring
- Platform: Facebook/Instagram (short-form vertical video ads, 4-10 seconds)
- Tone: empowering, knowledgeable, approachable, results-focused{audience_context}{persona_context}

AD COPY (for coherence evaluation):
- Headline: {headline or "(none)"}
- Primary Text: {primary_text or "(none)"}
- CTA: {cta_button or "(none)"}

SCORING DIMENSIONS:

1. hook_strength — Do the first 2 seconds grab attention and stop the scroll?
   Look for: immediate visual interest, motion, emotion, or curiosity trigger.
   Score 1 if slow/boring start, 5 if acceptable, 10 if impossible to scroll past.

2. visual_quality — Smooth motion, good lighting, no artifacts or glitches?
   Look for: flickering, distortion, unnatural physics, blurriness, uncanny valley.
   Score 1 if glitchy/unwatchable, 5 if passable, 10 if polished and natural.

3. narrative_flow — Clear beginning-middle-end? Pacing appropriate for a short social ad?
   Look for: logical scene progression, builds toward CTA, doesn't feel rushed or dragging.
   Score 1 if disjointed/random, 5 if basic progression, 10 if compelling mini-story.

4. copy_video_coherence — Does the video reinforce the ad text and CTA?
   The visual content should amplify the written message, not contradict or ignore it.
   Score 1 if contradicts copy, 5 if loosely related, 10 if perfectly amplifies the message.

5. ugc_authenticity — Does it feel genuine and relatable, not corporate or uncanny?
   UGC-style ads outperform polished corporate creative on social platforms.
   Score 1 if obviously AI-generated/corporate, 5 if neutral, 10 if feels like real user content.

Return ONLY valid JSON (no markdown, no code fences):
{{
  "hook_strength": {{"score": N, "rationale": "..."}},
  "visual_quality": {{"score": N, "rationale": "..."}},
  "narrative_flow": {{"score": N, "rationale": "..."}},
  "copy_video_coherence": {{"score": N, "rationale": "..."}},
  "ugc_authenticity": {{"score": N, "rationale": "..."}}
}}"""


def _parse_response(text: str) -> dict[str, Any]:
    """Parse Gemini JSON response, handling markdown fences."""
    stripped = text.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", stripped)
    if match:
        stripped = match.group(1).strip()
    return json.loads(stripped)


def _upload_and_wait(video_path: str) -> Any:
    """Upload video to Gemini and wait for processing to complete."""
    from google import genai

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set")

    client = genai.Client(api_key=api_key)
    video_file = client.files.upload(file=video_path)

    # Poll until processing is complete (same pattern as video_evaluator.py)
    while video_file.state.name == "PROCESSING":
        time.sleep(2)
        video_file = client.files.get(name=video_file.name)

    if video_file.state.name == "FAILED":
        raise RuntimeError(f"Video processing failed: {video_path}")

    return video_file


def score_video(
    video_path: str,
    ad_copy: dict[str, Any],
    ad_id: str = "",
    session_config: dict[str, Any] | None = None,
) -> VideoScoreResult:
    """Score a video on 5 quality dimensions via Gemini multimodal.

    Uploads the video file to Gemini, waits for processing, then
    evaluates on 5 dimensions. Returns zero scores if the file is
    missing or the API call fails.
    """
    if not Path(video_path).exists():
        logger.warning("Video file not found for scoring: %s", video_path)
        return _empty_result(ad_id, video_path)

    prompt = _build_prompt(ad_copy, session_config)

    def _do_call() -> VideoScoreResult:
        video_file = _upload_and_wait(video_path)

        from generate.gemini_client import call_gemini_multimodal
        resp = call_gemini_multimodal(
            [video_file, prompt], temperature=0.2, max_output_tokens=1024
        )
        return _build_result(resp.text, resp.total_tokens, ad_id, video_path)

    try:
        return retry_with_backoff(_do_call)
    except Exception as e:
        logger.warning("Video scoring failed for %s: %s", ad_id, e)
        return _empty_result(ad_id, video_path)


def _build_result(
    response_text: str, tokens: int, ad_id: str, video_path: str
) -> VideoScoreResult:
    """Parse Gemini response into VideoScoreResult."""
    try:
        parsed = _parse_response(response_text)
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning("Failed to parse video score response: %s", e)
        return _empty_result(ad_id, video_path, tokens)

    scores: dict[str, float] = {}
    rationales: dict[str, str] = {}

    for dim in VIDEO_DIMENSIONS:
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

    return VideoScoreResult(
        ad_id=ad_id,
        video_path=video_path,
        scores=scores,
        avg_score=round(avg, 2),
        rationales=rationales,
        tokens_consumed=tokens,
    )


def _empty_result(
    ad_id: str, video_path: str, tokens: int = 0
) -> VideoScoreResult:
    """Return a zero-scored result for error cases."""
    return VideoScoreResult(
        ad_id=ad_id,
        video_path=video_path,
        scores={dim: 0.0 for dim in VIDEO_DIMENSIONS},
        avg_score=0.0,
        rationales={dim: "" for dim in VIDEO_DIMENSIONS},
        tokens_consumed=tokens,
    )
