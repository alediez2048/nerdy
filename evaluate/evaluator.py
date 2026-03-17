"""Chain-of-thought ad evaluator (P0-06, P1-04, R3-Q6, R3-Q10).

LLM-as-Judge with 5-step CoT prompt. Contrastive rationales, confidence flags,
structural elements. Audience-specific Brand Voice rubric. Calibrated against labeled ads.
"""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from iterate.retry import retry_with_backoff

load_dotenv()

logger = logging.getLogger(__name__)

DIMENSIONS = (
    "clarity",
    "value_proposition",
    "cta",
    "brand_voice",
    "emotional_resonance",
)

# P1-05: Campaign-goal-adaptive weighting (replaces P0-06 equal weights)
from evaluate.dimensions import evaluate_with_weights  # noqa: E402
# Backward compat: equal weights still used by _compute_aggregate fallback
EQUAL_WEIGHTS = {d: 0.2 for d in DIMENSIONS}

CLARITY_FLOOR = 6.0
BRAND_VOICE_FLOOR = 5.0
QUALITY_THRESHOLD = 7.0

EVALUATOR_PROMPT_VERSION = "pb-06-v1"

_DEFAULT_CONFIG = "data/config.yaml"


@dataclass
class DimensionRationale:
    """Per-dimension contrastive rationale (R3-Q10)."""

    current_assessment: str
    score: float
    plus_two_description: str
    specific_gap: str
    confidence: float


def _build_evaluation_prompt(
    ad_text: dict[str, Any],
    campaign_goal: str,
    audience: str = "parents",
) -> str:
    """Build 5-step CoT evaluation prompt with audience-specific Brand Voice rubric."""
    from generate.brand_voice import get_voice_for_evaluation

    primary = ad_text.get("primary_text", "")
    headline = ad_text.get("headline", "")
    description = ad_text.get("description", "")
    cta = ad_text.get("cta_button", "")
    ad_id = ad_text.get("ad_id", "unknown")

    voice_rubric = get_voice_for_evaluation(audience)

    ad_block = f"""
PRIMARY TEXT:
{primary}

HEADLINE: {headline}
DESCRIPTION: {description}
CTA BUTTON: {cta}
"""

    return f"""You are a calibrated ad copy evaluator for education/tutoring ads on Meta (Facebook/Instagram). You must use the FULL 1-10 scale. Campaign goal: {campaign_goal}. Target audience: {audience}.

{voice_rubric}

IMPORTANT: Use decimal scores (6.2, 7.4, 8.1) — not just whole numbers. Each ad is unique; scores of exactly 7.0 across multiple ads are almost certainly wrong. Differentiate based on specific strengths and weaknesses.
If two dimensions have different strengths, they MUST have different scores. A clear ad with a weak value prop should NOT score 7.0 on both Clarity and Value Proposition.

CRITICAL SCORING CALIBRATION — use these anchors AND the mid-range examples:

SCORE 9-10 (Exceptional — rare):
  Example: "Is your child's SAT score holding them back from their dream school? College admissions are more competitive than ever. Varsity Tutors pairs your student with expert 1-on-1 tutors who adapt to how they learn. See the difference personalized prep can make." [CTA: Start Free Practice Test]
  WHY 9: Crystal clear single message, specific differentiation (1-on-1, adaptive), low-friction CTA, empowering brand voice, taps parent college anxiety.

SCORE 7-8 (Good — strong ads):
  Example: "Her SAT Score Jumped 360 Points! From 1010 to 1370 in Just 2 Months. 1:1 tutoring matched to how your child learns. Flexible scheduling around their busy school life. Fill out the quick form to get matched with an SAT-prep expert."
  WHY 7-8: Specific proof point (360 points), testimonial-style hook, clear mechanism (1:1 matched tutoring), low-friction CTA, taps parent aspiration.

SCORE 5-6 (Mediocre — competent but forgettable):
  Example: "Stressed about the SAT? You're not alone. Varsity Tutors offers personalized 1-on-1 prep with tutors who specialize in the test. Flexible scheduling, online sessions, and a free practice test to get started."
  WHY 5-6: Not scroll-stopping, generic "personalized" with no specific outcome, bland tone, mild emotional engagement.

SCORE 3-4 (Weak — clear problems):
  Example: "SAT prep. We do it. Online. With tutors. Sometimes it works. Try us."
  WHY 3-4: No hook, no value prop, undermines credibility, zero brand personality, no emotional engagement.

MID-RANGE GRANULAR EXAMPLES (use these to avoid clustering at whole numbers):

  Clarity:
    6.2: Main message is present but buried after a long preamble; reader has to work to find the point.
    6.5: Message is understandable but takes a second read; one competing idea dilutes the main point.
    6.8: Clear main message but the supporting detail introduces slight ambiguity about what's being offered.
    7.2: Strong single message with a decent hook, but one sentence feels redundant.
    7.5: Clear and concise with good flow; minor word choice issue softens the impact slightly.
    7.8: Crystal clear main message with a strong hook, but the transition to CTA could be smoother.
    8.3: Immediately clear, well-structured, with a compelling hook — only a tiny polish away from perfect.

  Value Proposition:
    6.2: Mentions a benefit but stays generic ("great tutoring") without specific differentiation.
    6.5: Has one specific element (e.g., "1-on-1") but no proof point or quantified outcome.
    6.8: Differentiator is present but not front-loaded; reader might miss it scanning quickly.
    7.2: Solid differentiator with a hint of proof, but doesn't fully quantify the benefit.
    7.5: Clear differentiator with a specific mechanism (e.g., "adaptive learning"), but no social proof.
    7.8: Strong specific benefit with a proof point, but the competitive advantage could be sharper.
    8.3: Specific, quantified, and differentiated — nearly unbeatable value framing.

  CTA:
    6.2: CTA exists but is generic ("Learn More") with no urgency or specificity.
    6.5: Slightly specific CTA but still feels like a template; no friction reduction.
    6.8: Reasonable CTA with some specificity, but the action feels bigger than it needs to.
    7.2: Good specific CTA but could reduce perceived commitment further.
    7.5: Clear, specific, low-friction CTA; minor improvement possible in urgency framing.
    7.8: Strong CTA with specificity and low friction, just missing a small urgency element.
    8.3: Highly specific, low-friction, with natural urgency — almost perfect conversion path.

  Brand Voice:
    6.2: On-brand in topic but tone feels corporate/stiff rather than empowering and approachable.
    6.5: Generally appropriate tone but missing the "knowledgeable insider" quality the brand needs.
    6.8: Mostly on-brand but one phrase feels too salesy or too casual for the brand personality.
    7.2: Good brand alignment with empowering language, but could be more results-focused.
    7.5: Strong brand voice — empowering and approachable; one line slightly breaks character.
    7.8: Consistently on-brand throughout with strong empowerment framing; tiny tonal inconsistency.
    8.3: Exemplary brand voice — every sentence feels authentically Varsity Tutors.

  Emotional Resonance:
    6.2: Attempts an emotional angle but it feels surface-level or cliched ("every parent wants the best").
    6.5: Identifies a real pain point but doesn't deepen it enough to create urgency.
    6.8: Taps a genuine emotion but the payoff/resolution feels generic rather than vivid.
    7.2: Good emotional hook with a real pain point; the transformation story could be more vivid.
    7.5: Strong emotional connection — parent can see themselves in the scenario; resolution is solid.
    7.8: Vivid emotional journey from problem to solution; just needs a slightly more specific payoff.
    8.3: Deeply resonant — specific, vivid scenario with a transformation that feels achievable and real.

COMPLIANCE FAILURES (automatic score penalties):
  - "Guaranteed 1500+" → Brand Voice capped at 3
  - Competitor disparagement without data → Brand Voice capped at 3
  - "100% guaranteed" / absolute promises → Value Proposition capped at 4

NERDY LANGUAGE PENALTIES (PB-06 — applied automatically after scoring):
  - Uses "your student" instead of "your child" → Brand Voice capped at 4.0
  - Uses "SAT Prep" instead of "SAT Tutoring" → Brand Voice -1.0
  - Corporate jargon ("unlock potential", "maximize score", "tailored support") → Clarity -1.0
  - Fake urgency ("spots filling fast", "limited enrollment", "don't miss out") → Brand Voice -1.5
  - "Online tutoring" framing → Brand Voice -1.0

NERDY SPECIFICITY BONUSES (reward these when present):
  - Conditional claim (score + timeframe: "200 points in 16 sessions") → Value Proposition +0.5
  - Specific mechanism (digital SAT tools, diagnostic, session structure) → Value Proposition +0.5
  - Real competitor data (pricing, results comparison with numbers) → Value Proposition +0.5

NERDY CALIBRATION ANCHORS (use these as primary reference):
  SCORE 9: "3.8 GPA. 1260 SAT. Something's off. Most mid-1200s students are 3–4 targeted fixes away from a 1400+. We diagnose exactly where points are hiding. See what score is realistic in 8–10 weeks."
  WHY 9: Crystal clear hook with GPA/SAT mismatch, specific mechanism (targeted fixes), persona-matched CTA (suburban optimizer), plain parent language.

  SCORE 7: "Your child can raise their SAT score ~100 points per month with 2 sessions per week and 20 minutes of daily practice. Our 1:1 tutors have scored in the 99th percentile and are matched specifically to how your child learns."
  WHY 7: Conditional claim with specifics, plain language, specific mechanism, but generic hook.

  SCORE 5: "Struggling with the SAT? Unlock your child's potential with our personalized SAT prep program. Expert tutors. Flexible scheduling. Learn More."
  WHY 5: Generic hook, corporate jargon ("unlock potential", "personalized"), no specific mechanism, vague CTA.

  SCORE 3: "SAT Prep available for your student. Spots filling fast! Limited enrollment. Don't miss out. Get Started."
  WHY 3: Wrong language ("your student", "SAT Prep"), fake urgency, no mechanism, no value prop.

AD TO EVALUATE (ad_id: {ad_id}):
{ad_block}

Follow this 5-step sequence exactly:

Step 1: READ the ad completely.

Step 2: DECOMPOSE — Before scoring, identify and output:
  - hook: first line/sentence — scroll-stopping or generic?
  - value_proposition: specific and differentiated, or generic?
  - cta: specific and low-friction, or vague?
  - emotional_angle: taps real emotion, or flat?

Step 3: COMPARE against the calibration anchors above.

Step 4: SCORE each dimension with a CONTRASTIVE rationale:
  - Current assessment: what the ad does for this dimension
  - Score (1-10)
  - Plus-two description: what a version scoring +2 higher would look like
  - Specific gap: the concrete gap between current and +2
  - Confidence (1-10): below 7 = flag for review

Step 5: FLAG low-confidence dimensions (confidence < 7).

Output ONLY valid JSON (no markdown, no code fences):
{{
  "ad_id": "{ad_id}",
  "structural_elements": {{
    "hook": "<identified hook>",
    "value_proposition": "<identified VP>",
    "cta": "<identified CTA>",
    "emotional_angle": "<identified emotional angle>"
  }},
  "scores": {{
    "clarity": {{"score": <float>, "rationale": "<string>", "contrastive": "<string>", "plus_two_description": "<string>", "specific_gap": "<string>", "confidence": <int>}},
    "value_proposition": {{"score": <float>, "rationale": "<string>", "contrastive": "<string>", "plus_two_description": "<string>", "specific_gap": "<string>", "confidence": <int>}},
    "cta": {{"score": <float>, "rationale": "<string>", "contrastive": "<string>", "plus_two_description": "<string>", "specific_gap": "<string>", "confidence": <int>}},
    "brand_voice": {{"score": <float>, "rationale": "<string>", "contrastive": "<string>", "plus_two_description": "<string>", "specific_gap": "<string>", "confidence": <int>}},
    "emotional_resonance": {{"score": <float>, "rationale": "<string>", "contrastive": "<string>", "plus_two_description": "<string>", "specific_gap": "<string>", "confidence": <int>}}
  }},
  "weakest_dimension": "<one of: clarity, value_proposition, cta, brand_voice, emotional_resonance>",
  "flags": ["<e.g. low_confidence:clarity if confidence<7>"]
}}

Note: plus_two_description and specific_gap can be derived from contrastive if needed. Rationale = current_assessment."""


def _call_gemini(prompt: str, ad_id: str) -> dict[str, Any]:
    """Call Gemini API for evaluation. Uses retry_with_backoff."""
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
                temperature=0.4,
                max_output_tokens=2048,
            ),
        )
        text = response.text or ""
        return _parse_evaluation_response(text, ad_id)

    return retry_with_backoff(_do_call)


def _parse_evaluation_response(text: str, ad_id: str) -> dict[str, Any]:
    """Parse JSON from model response. Handles markdown, malformed input."""
    stripped = text.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", stripped)
    if match:
        stripped = match.group(1).strip()

    try:
        data = json.loads(stripped)
    except json.JSONDecodeError:
        # Try to salvage: strip trailing commas before closing braces/brackets
        salvaged = re.sub(r",\s*([}\]])", r"\1", stripped)
        try:
            data = json.loads(salvaged)
            logger.info("Evaluator: salvaged malformed JSON after stripping trailing commas")
        except json.JSONDecodeError as e:
            logger.warning("Evaluator: malformed JSON, returning minimal result: %s", e)
            return {
                "ad_id": ad_id,
                "structural_elements": {},
                "scores": {d: {"score": 5.0, "rationale": "Parse error", "contrastive": "N/A", "confidence": 5} for d in DIMENSIONS},
                "weakest_dimension": "clarity",
                "flags": ["parse_error"],
            }

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
            # Clamp score to 1-10
            s["score"] = max(1.0, min(10.0, float(s["score"])))

    data["ad_id"] = data.get("ad_id") or ad_id
    data["scores"] = scores
    data["structural_elements"] = data.get("structural_elements") or {}
    return data


def _scores_to_rationales(scores: dict[str, dict[str, Any]]) -> dict[str, DimensionRationale]:
    """Build DimensionRationale from scores dict."""
    rationales: dict[str, DimensionRationale] = {}
    for dim in DIMENSIONS:
        s = scores.get(dim, {})
        rationale = s.get("rationale", "")
        contrastive = s.get("contrastive", "")
        plus_two = s.get("plus_two_description") or contrastive or "N/A"
        gap = s.get("specific_gap") or contrastive or "N/A"
        conf = s.get("confidence", 7)
        if isinstance(conf, int):
            conf = float(conf)
        rationales[dim] = DimensionRationale(
            current_assessment=rationale or "Not assessed",
            score=float(s.get("score", 5.0)),
            plus_two_description=plus_two,
            specific_gap=gap,
            confidence=conf,
        )
    return rationales


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


def _load_config() -> dict[str, Any]:
    """Load config for ledger_path."""
    import yaml

    p = Path(_DEFAULT_CONFIG)
    if not p.is_absolute():
        p = Path(__file__).resolve().parents[1] / p
    if not p.exists():
        return {"ledger_path": "data/ledger.jsonl"}
    with open(p, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


@dataclass
class EvaluationResult:
    """Structured evaluation output (R3-Q6, R3-Q10)."""

    ad_id: str
    scores: dict[str, dict[str, Any]]
    aggregate_score: float
    campaign_goal: str
    meets_threshold: bool
    weakest_dimension: str
    flags: list[str] = field(default_factory=list)
    rationales: dict[str, DimensionRationale] = field(default_factory=dict)
    structural_elements: dict[str, str] = field(default_factory=dict)
    confidence_flags: dict[str, float] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """JSON-serializable dict for ledger."""
        base = {
            "ad_id": self.ad_id,
            "scores": self.scores,
            "aggregate_score": self.aggregate_score,
            "campaign_goal": self.campaign_goal,
            "meets_threshold": self.meets_threshold,
            "weakest_dimension": self.weakest_dimension,
            "flags": self.flags,
        }
        if self.rationales:
            base["rationales"] = {
                d: {
                    "current_assessment": r.current_assessment,
                    "score": r.score,
                    "plus_two_description": r.plus_two_description,
                    "specific_gap": r.specific_gap,
                    "confidence": r.confidence,
                }
                for d, r in self.rationales.items()
            }
        if self.structural_elements:
            base["structural_elements"] = self.structural_elements
        if self.confidence_flags:
            base["confidence_flags"] = self.confidence_flags
        if self.metadata:
            base["metadata"] = self.metadata
        return base


def _apply_nerdy_adjustments(
    scores: dict[str, dict[str, Any]],
    ad_text: dict[str, Any],
    persona: str | None = None,
) -> dict[str, dict[str, Any]]:
    """Apply deterministic Nerdy language penalties and specificity bonuses (PB-06).

    Modifies scores in-place and returns them. Penalties/bonuses are applied
    AFTER the LLM evaluation to ensure consistency regardless of LLM variance.
    """
    full_text = " ".join([
        ad_text.get("primary_text", ""),
        ad_text.get("headline", ""),
        ad_text.get("description", ""),
    ]).lower()

    bv = scores.get("brand_voice", {})
    cl = scores.get("clarity", {})
    vp = scores.get("value_proposition", {})
    er = scores.get("emotional_resonance", {})

    bv_score = float(bv.get("score", 5.0))
    cl_score = float(cl.get("score", 5.0))
    vp_score = float(vp.get("score", 5.0))
    er_score = float(er.get("score", 5.0))

    # --- Penalties ---
    if "your student" in full_text:
        bv_score = min(bv_score, 4.0)
    if re.search(r"\bsat\s+prep\b", full_text):
        bv_score = max(1.0, bv_score - 1.0)
    if re.search(r"\bonline\s+tutoring\b", full_text):
        bv_score = max(1.0, bv_score - 1.0)
    if re.search(r"(?:spots?\s+filling|limited\s+enrollment|don'?t\s+miss\s+out|act\s+now)", full_text):
        bv_score = max(1.0, bv_score - 1.5)
    if re.search(r"(?:unlock\s+(?:their\s+)?potential|maximize\s+score|tailored\s+support|custom\s+strategies)", full_text):
        cl_score = max(1.0, cl_score - 1.0)

    # --- Bonuses ---
    if re.search(r"\d{2,3}\s*points?\s*.{0,30}(?:sessions?|weeks?|month)", full_text):
        vp_score = min(10.0, vp_score + 0.5)
    if re.search(r"(?:diagnostic|built-in\s+(?:calculator|tools?)|digital\s+sat\s+interface|session\s+structure)", full_text):
        vp_score = min(10.0, vp_score + 0.5)
    if re.search(r"(?:princeton|kaplan|khan).{0,40}\$\d+", full_text):
        vp_score = min(10.0, vp_score + 0.5)

    # --- Persona match bonus/penalty ---
    if persona:
        _PERSONA_KEYWORDS: dict[str, list[str]] = {
            "athlete_recruit": ["recruit", "scholarship", "ncaa", "coach", "athlete", "practice"],
            "system_optimizer": ["diagnostic", "process", "timeline", "roi", "data", "inputs", "outputs"],
            "neurodivergent_advocate": ["adhd", "learn differently", "accommodation", "extended time", "right fit"],
            "burned_returner": ["didn't work", "what went wrong", "different this time", "burned", "disappointed"],
            "immigrant_navigator": ["walk you through", "step by step", "first time", "the sat process"],
            "suburban_optimizer": ["gpa", "1200", "1400", "fixes", "realistic"],
            "cultural_investor": ["multiple resources", "one system", "consolidate", "mastery"],
        }
        keywords = _PERSONA_KEYWORDS.get(persona, [])
        if keywords and any(kw in full_text for kw in keywords):
            er_score = min(10.0, er_score + 0.5)

    # Write back
    bv["score"] = round(bv_score, 1)
    cl["score"] = round(cl_score, 1)
    vp["score"] = round(vp_score, 1)
    er["score"] = round(er_score, 1)

    return scores


def evaluate_ad(
    ad_text: dict[str, Any],
    campaign_goal: str = "conversion",
    audience: str = "parents",
    ledger_path: str | None = None,
    persona: str | None = None,
) -> EvaluationResult:
    """Evaluate an ad using 5-step CoT prompt (R3-Q6) with contrastive rationales (R3-Q10).

    Args:
        ad_text: Dict with primary_text, headline, description, cta_button, ad_id
        campaign_goal: "awareness" or "conversion"
        audience: "parents" or "students" — for Brand Voice rubric
        ledger_path: Override ledger path for logging

    Returns:
        EvaluationResult with scores, rationales, structural_elements, confidence_flags
    """
    from iterate.ledger import log_event

    ad_id = ad_text.get("ad_id", "unknown")
    prompt = _build_evaluation_prompt(ad_text, campaign_goal, audience)
    raw = _call_gemini(prompt, ad_id)

    scores = raw["scores"]
    # PB-06: Apply Nerdy-specific adjustments (penalties + bonuses)
    scores = _apply_nerdy_adjustments(scores, ad_text, persona=persona)
    # P1-05: Use campaign-goal-adaptive weighting instead of equal weights
    flat_scores = {d: scores.get(d, {}).get("score", 5.0) for d in DIMENSIONS}
    weighted = evaluate_with_weights(flat_scores, campaign_goal)
    aggregate = weighted.weighted_average
    meets = weighted.passes_threshold
    flags = list(raw.get("flags", []))
    flags.extend([f"floor_violation:{v.dimension}" for v in weighted.floor_violations])

    rationales = _scores_to_rationales(scores)
    structural_elements = raw.get("structural_elements") or {}
    confidence_flags = {
        d: r.confidence for d, r in rationales.items() if r.confidence < 7
    }
    if confidence_flags:
        flags.extend([f"low_confidence:{d}" for d in confidence_flags])

    tokens_estimate = (len(prompt) + 500) // 4
    metadata = {
        "model_used": "gemini-2.0-flash",
        "tokens_consumed": tokens_estimate,
        "prompt_version": EVALUATOR_PROMPT_VERSION,
    }

    result = EvaluationResult(
        ad_id=raw["ad_id"],
        scores=scores,
        aggregate_score=aggregate,
        campaign_goal=campaign_goal,
        meets_threshold=meets,
        weakest_dimension=raw.get("weakest_dimension")
        or min(DIMENSIONS, key=lambda d: scores.get(d, {}).get("score", 5.0)),
        flags=flags,
        rationales=rationales,
        structural_elements=structural_elements,
        confidence_flags=confidence_flags,
        metadata=metadata,
    )

    cfg = _load_config()
    led_path = ledger_path or cfg.get("ledger_path", "data/ledger.jsonl")
    brief_id = "unknown"
    if ad_id.startswith("ad_") and "_c" in ad_id:
        parts = ad_id.split("_")
        if len(parts) >= 2:
            brief_id = parts[1]

    log_event(
        led_path,
        {
            "event_type": "AdEvaluated",
            "ad_id": result.ad_id,
            "brief_id": brief_id,
            "cycle_number": 0,
            "action": "evaluation",
            "tokens_consumed": tokens_estimate,
            "model_used": "gemini-2.0-flash",
            "seed": "0",
            "inputs": {"ad_id": ad_id, "campaign_goal": campaign_goal, "audience": audience},
            "outputs": result.to_dict(),
        },
    )

    return result


# Backward compatibility: _build_prompt alias for tests that may reference it
def _build_prompt(ad_text: dict[str, Any], campaign_goal: str) -> str:
    """Legacy alias — use _build_evaluation_prompt with audience."""
    return _build_evaluation_prompt(ad_text, campaign_goal, "parents")
