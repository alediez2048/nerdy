"""Chain-of-thought ad evaluator (P0-06, R3-Q6).

LLM-as-Judge with 5-step CoT prompt. Calibrated against labeled reference ads.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

DIMENSIONS = (
    "clarity",
    "value_proposition",
    "cta",
    "brand_voice",
    "emotional_resonance",
)

# P0-06: Equal weighting. Full campaign-goal-adaptive is P1-05.
EQUAL_WEIGHTS = {d: 0.2 for d in DIMENSIONS}

CLARITY_FLOOR = 6.0
BRAND_VOICE_FLOOR = 5.0
QUALITY_THRESHOLD = 7.0

EVALUATOR_PROMPT_VERSION = "p0-06-v3"


def _build_prompt(ad_text: dict[str, Any], campaign_goal: str) -> str:
    """Build the 5-step CoT evaluation prompt (R3-Q6)."""
    primary = ad_text.get("primary_text", "")
    headline = ad_text.get("headline", "")
    description = ad_text.get("description", "")
    cta = ad_text.get("cta_button", "")
    ad_id = ad_text.get("ad_id", "unknown")

    ad_block = f"""
PRIMARY TEXT:
{primary}

HEADLINE: {headline}
DESCRIPTION: {description}
CTA BUTTON: {cta}
"""

    return f"""You are a calibrated ad copy evaluator for education/tutoring ads on Meta (Facebook/Instagram). You must use the FULL 1-10 scale. Campaign goal: {campaign_goal}.

IMPORTANT SCORING GUIDANCE:
- Score what the ad actually achieves. Do NOT default to middle scores.
- Ads with specific data points, testimonials, clear mechanisms, and emotional hooks deserve 7-8+.
- Length is NOT a penalty — longer ads with structured benefits (bullet points, proof points) can score 8+ if each element adds value.
- Reserve 9-10 for truly exceptional ads, and 3-4 for genuinely weak ones.
- If an ad has a strong hook AND specific differentiation AND emotional resonance, it should score 7+ on those dimensions even if imperfect.

CRITICAL SCORING CALIBRATION — use these anchors:

SCORE 9-10 (Exceptional — rare):
  Example: "Is your child's SAT score holding them back from their dream school? College admissions are more competitive than ever. Varsity Tutors pairs your student with expert 1-on-1 tutors who adapt to how they learn. See the difference personalized prep can make." [CTA: Start Free Practice Test]
  WHY 9: Crystal clear single message, specific differentiation (1-on-1, adaptive), low-friction CTA, empowering brand voice, taps parent college anxiety.

SCORE 7-8 (Good — strong ads):
  Example: "Her SAT Score Jumped 360 Points! From 1010 to 1370 in Just 2 Months. 1:1 tutoring matched to how your child learns. Flexible scheduling around their busy school life. Fill out the quick form to get matched with an SAT-prep expert."
  WHY 7-8: Specific proof point (360 points), testimonial-style hook, clear mechanism (1:1 matched tutoring), low-friction CTA, taps parent aspiration. Strong but slightly long.

SCORE 5-6 (Mediocre — competent but forgettable):
  Example: "Stressed about the SAT? You're not alone. Varsity Tutors offers personalized 1-on-1 prep with tutors who specialize in the test. Flexible scheduling, online sessions, and a free practice test to get started."
  WHY 5-6: Not scroll-stopping, generic "personalized" with no specific outcome, bland tone, mild emotional engagement.

SCORE 3-4 (Weak — clear problems):
  Example: "SAT prep. We do it. Online. With tutors. Sometimes it works. Try us."
  WHY 3-4: No hook, no value prop, undermines credibility, zero brand personality, no emotional engagement.

COMPLIANCE FAILURES (automatic score penalties):
  - "Guaranteed 1500+" → Brand Voice capped at 3 (off-brand, compliance violation)
  - Competitor disparagement by name → Brand Voice capped at 3
  - "100% guaranteed" / absolute promises → Value Proposition capped at 4

AD TO EVALUATE (ad_id: {ad_id}):
{ad_block}

Follow this 5-step sequence exactly:

Step 1: READ the ad completely.

Step 2: DECOMPOSE — Before scoring, identify:
  - The hook (first line/sentence) — is it scroll-stopping or generic?
  - The value proposition — is it specific and differentiated, or could any tutoring company say this?
  - The call to action — is it specific and low-friction, or vague?
  - The emotional angle — does it tap a real emotion, or is it flat?

Step 3: COMPARE against the calibration anchors above. Ask yourself:
  - Is this closer to the 7-8 example or the 3-4 example?
  - Would a real parent/student stop scrolling for this?
  - Does it have specific proof points, stats, or testimonials? If yes, value_proposition is likely 7+.
  - Could a generic tutoring company use this exact ad? If yes, Brand Voice is ≤5.

Step 4: SCORE each dimension with a CONTRASTIVE rationale. Use the full 1-10 scale — reward genuine quality:
  - "This ad scores [X] on [dimension] because [specific reason]."
  - "A version scoring [X+2] would [specific concrete change]."
  - If the ad has compliance violations, note them and cap the relevant dimension.

Step 5: FLAG CONFIDENCE per dimension (1-10). Below 7 = flag for review.

Output ONLY valid JSON matching this schema (no markdown, no code fences):
{{
  "ad_id": "{ad_id}",
  "scores": {{
    "clarity": {{"score": <float>, "rationale": "<string>", "contrastive": "<string>", "confidence": <int>}},
    "value_proposition": {{"score": <float>, "rationale": "<string>", "contrastive": "<string>", "confidence": <int>}},
    "cta": {{"score": <float>, "rationale": "<string>", "contrastive": "<string>", "confidence": <int>}},
    "brand_voice": {{"score": <float>, "rationale": "<string>", "contrastive": "<string>", "confidence": <int>}},
    "emotional_resonance": {{"score": <float>, "rationale": "<string>", "contrastive": "<string>", "confidence": <int>}}
  }},
  "weakest_dimension": "<one of: clarity, value_proposition, cta, brand_voice, emotional_resonance>",
  "flags": ["<list of flags, e.g. low_confidence:clarity if confidence<7>"]
}}
"""


def _call_gemini(prompt: str, ad_id: str) -> dict[str, Any]:
    """Call Gemini API for evaluation. Extracted for testability.

    Retries on 429/500/503 with exponential backoff (R3-Q2).
    """
    import os
    import time

    from google import genai
    from google.genai import types

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set in environment")

    max_retries = 3
    base_delay = 2.0

    for attempt in range(max_retries):
        try:
            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.2,
                    max_output_tokens=2048,
                ),
            )
            text = response.text or ""
            return _parse_evaluation_response(text, ad_id)
        except Exception as e:
            err_str = str(e).lower()
            if "429" in err_str or "resource_exhausted" in err_str or "500" in err_str or "503" in err_str:
                if attempt < max_retries - 1:
                    delay = min(base_delay * (2**attempt), 60)
                    logger.warning("API rate limit or server error, retrying in %.0fs: %s", delay, e)
                    time.sleep(delay)
                else:
                    raise
            else:
                raise


def _parse_evaluation_response(text: str, ad_id: str) -> dict[str, Any]:
    """Parse JSON from model response. Handles markdown code blocks."""
    # Strip markdown code fences if present
    stripped = text.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", stripped)
    if match:
        stripped = match.group(1).strip()
    data = json.loads(stripped)

    # Normalize scores: ensure all dimensions present
    scores = data.get("scores", {})
    for dim in DIMENSIONS:
        if dim not in scores:
            scores[dim] = {
                "score": 5.0,
                "rationale": "Missing from model output",
                "contrastive": "N/A",
                "confidence": 5,
            }
        else:
            s = scores[dim]
            if isinstance(s.get("score"), int):
                s["score"] = float(s["score"])
            if "confidence" not in s:
                s["confidence"] = 7

    data["ad_id"] = data.get("ad_id") or ad_id
    data["scores"] = scores
    return data


def _compute_aggregate(scores: dict[str, dict[str, Any]]) -> float:
    """Weighted average using equal weights (P0-06)."""
    total = 0.0
    for dim in DIMENSIONS:
        if dim in scores:
            total += scores[dim]["score"] * EQUAL_WEIGHTS[dim]
    return round(total, 2)


def _apply_floor_awareness(
    scores: dict[str, dict[str, Any]], aggregate: float
) -> tuple[bool, list[str]]:
    """Basic floor awareness: Clarity >= 6.0, Brand Voice >= 5.0."""
    violations = []
    if scores.get("clarity", {}).get("score", 0) < CLARITY_FLOOR:
        violations.append("clarity_floor")
    if scores.get("brand_voice", {}).get("score", 0) < BRAND_VOICE_FLOOR:
        violations.append("brand_voice_floor")
    meets = aggregate >= QUALITY_THRESHOLD and len(violations) == 0
    return meets, violations


@dataclass
class EvaluationResult:
    """Structured evaluation output (R3-Q6 schema)."""

    ad_id: str
    scores: dict[str, dict[str, Any]]
    aggregate_score: float
    campaign_goal: str
    meets_threshold: bool
    weakest_dimension: str
    flags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """JSON-serializable dict for ledger."""
        return {
            "ad_id": self.ad_id,
            "scores": self.scores,
            "aggregate_score": self.aggregate_score,
            "campaign_goal": self.campaign_goal,
            "meets_threshold": self.meets_threshold,
            "weakest_dimension": self.weakest_dimension,
            "flags": self.flags,
        }


def evaluate_ad(
    ad_text: dict[str, Any],
    campaign_goal: str = "conversion",
) -> EvaluationResult:
    """Evaluate an ad using 5-step CoT prompt (R3-Q6).

    Args:
        ad_text: Dict with primary_text, headline, description, cta_button, ad_id
        campaign_goal: "awareness" or "conversion" (P0-06 uses equal weights for both)

    Returns:
        EvaluationResult with scores, aggregate, meets_threshold, flags
    """
    ad_id = ad_text.get("ad_id", "unknown")
    prompt = _build_prompt(ad_text, campaign_goal)
    raw = _call_gemini(prompt, ad_id)

    scores = raw["scores"]
    aggregate = _compute_aggregate(scores)
    meets, floor_violations = _apply_floor_awareness(scores, aggregate)
    flags = list(raw.get("flags", []))
    flags.extend([f"floor_violation:{v}" for v in floor_violations])

    return EvaluationResult(
        ad_id=raw["ad_id"],
        scores=scores,
        aggregate_score=aggregate,
        campaign_goal=campaign_goal,
        meets_threshold=meets,
        weakest_dimension=raw.get("weakest_dimension") or min(
            scores.keys(), key=lambda d: scores[d]["score"]
        ),
        flags=flags,
    )
