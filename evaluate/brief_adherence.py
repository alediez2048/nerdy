"""Brief adherence scorer — measures how well an ad follows the session brief (PD-12).

Scores 5 dimensions (1-10) comparing the ad output against the session config:
audience match, goal alignment, persona fit, message delivery, format adherence.

Orthogonal to copy quality — a high-quality ad can still score low on adherence
if it ignores the persona, misses the key message, or uses the wrong format.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from iterate.retry import retry_with_backoff

logger = logging.getLogger(__name__)

ADHERENCE_DIMENSIONS = (
    "audience_match",
    "goal_alignment",
    "persona_fit",
    "message_delivery",
    "format_adherence",
)


@dataclass
class BriefAdherenceResult:
    """Result of scoring an ad against the session brief."""

    ad_id: str
    scores: dict[str, float]
    avg_score: float
    rationales: dict[str, str]
    tokens_consumed: int = 0


def _build_prompt(ad_copy: dict[str, Any], session_config: dict[str, Any]) -> str:
    """Build the Gemini prompt for brief adherence scoring."""
    audience = session_config.get("audience", "auto")
    campaign_goal = session_config.get("campaign_goal", "auto")
    persona = session_config.get("persona", "auto")
    key_message = session_config.get("key_message", "")
    creative_brief = session_config.get("creative_brief", "auto")

    headline = ad_copy.get("headline", "")
    primary_text = ad_copy.get("primary_text", "")
    description = ad_copy.get("description", "")
    cta_button = ad_copy.get("cta_button", "")

    return f"""You are an ad quality auditor for Varsity Tutors SAT test prep campaigns.

Score how well this ad adheres to the creative brief. This is NOT about ad quality —
it's about whether the ad followed the instructions it was given.

CREATIVE BRIEF:
- Target Audience: {audience}
- Campaign Goal: {campaign_goal}
- Persona: {persona}
- Key Message: {key_message or "(none specified)"}
- Creative Brief Style: {creative_brief}

AD OUTPUT:
- Headline: {headline or "(none)"}
- Primary Text: {primary_text or "(none)"}
- Description: {description or "(none)"}
- CTA Button: {cta_button or "(none)"}

Score each dimension 1-10 with a one-sentence rationale:

1. audience_match — Does the ad speak directly to the target audience ({audience})?
   A parent-facing ad should use "your child" language; a student-facing ad should use "you/your" language.
   Score 1 if wrong audience entirely, 5 if ambiguous, 10 if perfectly targeted.

2. goal_alignment — Does the ad serve the campaign goal ({campaign_goal})?
   "conversion" needs a strong CTA with urgency. "awareness" needs brand positioning.
   Score 1 if wrong goal, 5 if partially aligned, 10 if perfectly serves the goal.

3. persona_fit — Does the tone and emotional register match the persona ({persona})?
   Each persona has distinct emotional needs and communication style.
   Score 1 if generic/wrong tone, 5 if partially matches, 10 if nails the persona voice.

4. message_delivery — Is the key message "{key_message or "(none specified)"}" present or clearly conveyed?
   Can be literal or paraphrased. Score 1 if absent, 5 if vaguely implied, 10 if central to the ad.
   If no key message was specified, score based on whether the ad has a clear central message at all.

5. format_adherence — Does the ad match the creative brief style ({creative_brief})?
   "ugc_testimonial" should feel like a real person's story. "direct_response" should be punchy and action-oriented.
   Score 1 if wrong format, 5 if partially matches, 10 if perfect format match.
   If creative brief is "auto", score based on whether the format is appropriate for the audience and goal.

Return ONLY valid JSON (no markdown, no code fences):
{{
  "audience_match": {{"score": N, "rationale": "..."}},
  "goal_alignment": {{"score": N, "rationale": "..."}},
  "persona_fit": {{"score": N, "rationale": "..."}},
  "message_delivery": {{"score": N, "rationale": "..."}},
  "format_adherence": {{"score": N, "rationale": "..."}}
}}"""


def _parse_response(text: str) -> dict[str, Any]:
    """Parse Gemini JSON response, handling markdown fences."""
    stripped = text.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", stripped)
    if match:
        stripped = match.group(1).strip()
    return json.loads(stripped)


def score_brief_adherence(
    ad_copy: dict[str, Any],
    session_config: dict[str, Any],
    ad_id: str = "",
    image_path: str | None = None,
    video_path: str | None = None,
) -> BriefAdherenceResult:
    """Score an ad against the session brief on 5 adherence dimensions.

    For copy-only ads, uses text prompt. For ads with images or videos,
    uses multimodal prompt so Gemini can evaluate visual adherence too.
    """
    prompt = _build_prompt(ad_copy, session_config)

    # Decide whether to use multimodal (image/video) or text-only
    use_multimodal = False
    media_path = None
    if video_path and Path(video_path).exists():
        use_multimodal = True
        media_path = video_path
    elif image_path and Path(image_path).exists():
        use_multimodal = True
        media_path = image_path

    if use_multimodal and media_path:
        from generate.gemini_client import call_gemini_multimodal

        from google import genai
        from google.genai import types

        import os
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY not set")

        def _do_multimodal() -> BriefAdherenceResult:
            client = genai.Client(api_key=api_key)
            media_file = client.files.upload(file=media_path)
            contents = [media_file, prompt]
            resp = call_gemini_multimodal(
                contents, temperature=0.2, max_output_tokens=1024
            )
            return _build_result(resp.text, resp.total_tokens, ad_id)

        return retry_with_backoff(_do_multimodal)
    else:
        from generate.gemini_client import call_gemini

        def _do_text() -> BriefAdherenceResult:
            resp = call_gemini(prompt, temperature=0.2, max_output_tokens=1024)
            return _build_result(resp.text, resp.total_tokens, ad_id)

        return retry_with_backoff(_do_text)


def _build_result(
    response_text: str, tokens: int, ad_id: str
) -> BriefAdherenceResult:
    """Parse Gemini response into BriefAdherenceResult."""
    try:
        parsed = _parse_response(response_text)
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning("Failed to parse brief adherence response: %s", e)
        return _empty_result(ad_id, tokens)

    scores: dict[str, float] = {}
    rationales: dict[str, str] = {}

    for dim in ADHERENCE_DIMENSIONS:
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

    return BriefAdherenceResult(
        ad_id=ad_id,
        scores=scores,
        avg_score=round(avg, 2),
        rationales=rationales,
        tokens_consumed=tokens,
    )


def _empty_result(ad_id: str, tokens: int = 0) -> BriefAdherenceResult:
    """Return a zero-scored result for error cases."""
    return BriefAdherenceResult(
        ad_id=ad_id,
        scores={dim: 0.0 for dim in ADHERENCE_DIMENSIONS},
        avg_score=0.0,
        rationales={dim: "" for dim in ADHERENCE_DIMENSIONS},
        tokens_consumed=tokens,
    )
