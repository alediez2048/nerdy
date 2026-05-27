"""Unified media quality evaluator (PI-02 / PI-05).

Single source of truth for image and video variant scoring. One Gemini
2.5 Flash multimodal call per variant returns all dimension scores,
gate evaluations, and rationales in a single structured JSON response.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from iterate.retry import retry_with_backoff

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "gemini-2.5-flash"

# ---- Image rubric (PI-02) ----
IMAGE_DIMENSIONS: tuple[dict[str, Any], ...] = (
    {"name": "thumb_stop_potential", "weight": 0.20,
     "criterion": "Does it stop the scroll in the first 0.3s? Strong visual hook."},
    {"name": "mobile_legibility", "weight": 0.15,
     "criterion": "Key elements readable at 320px width (mobile feed size)."},
    {"name": "single_focal_point", "weight": 0.10,
     "criterion": "Clear hierarchy — no competing subjects."},
    {"name": "brand_consistency", "weight": 0.10,
     "criterion": "Varsity Tutors visual identity — teal/navy/white palette."},
    {"name": "emotional_impact", "weight": 0.15,
     "criterion": "Evokes a specific emotion (aspiration, determination, warmth)."},
    {"name": "message_alignment", "weight": 0.10,
     "criterion": "Visual reinforces the ad's headline and copy."},
    {"name": "audience_match", "weight": 0.10,
     "criterion": "Fits the target audience (parent of HS student vs student)."},
    {"name": "production_quality", "weight": 0.10,
     "criterion": "Composition, color balance, no obvious AI tells."},
)

IMAGE_GATES: tuple[dict[str, Any], ...] = (
    {"name": "has_ai_artifacts", "cap": 0.5,
     "criterion": "Warped hands, mangled text, impossible geometry."},
    {"name": "has_uncanny_faces", "cap": 0.6,
     "criterion": "Asymmetric features, melted skin, lifeless eyes."},
    {"name": "brand_safety_violation", "cap": 0.3,
     "criterion": "Competitor logos, inappropriate context, unsafe imagery."},
)


@dataclass
class DimensionScore:
    score: int          # 1–10
    weight: float       # taken from the rubric, not the LLM
    rationale: str


@dataclass
class GateEvaluation:
    triggered: bool
    rationale: str


@dataclass
class MediaEvaluationResult:
    ad_id: str
    variant_type: str
    media_type: Literal["image", "video"]
    media_path: str
    model_used: str
    tokens_consumed: int
    dimensions: dict[str, DimensionScore]
    penalty_gates: dict[str, GateEvaluation]
    raw_score: float
    penalty_multiplier: float
    composite_score: float
    schema_version: str = "v2"
    failed: bool = False
    failure_reason: str | None = None
    error_message: str | None = None


def compute_composite(
    dimensions: dict[str, DimensionScore],
    penalty_gates: dict[str, GateEvaluation],
    gate_rubric: tuple[dict[str, Any], ...],
) -> tuple[float, float, float]:
    """Return (raw_score 0..1, penalty_mult, composite 0..100).

    Multiple triggered gates take the most-severe (lowest) cap.
    """
    raw = sum(d.score * d.weight for d in dimensions.values()) / 10.0
    triggered_caps = [
        g["cap"] for g in gate_rubric
        if penalty_gates.get(g["name"], GateEvaluation(False, "")).triggered
    ]
    penalty_mult = min(triggered_caps) if triggered_caps else 1.0
    composite = round(raw * penalty_mult * 100.0, 2)
    return round(raw, 4), penalty_mult, composite


def _build_image_prompt(ad_copy: dict[str, Any], session_config: dict[str, Any] | None) -> str:
    headline = ad_copy.get("headline", "")
    primary_text = ad_copy.get("primary_text", "") or ad_copy.get("body", "")
    cta = ad_copy.get("cta_button", "") or ad_copy.get("cta", "")
    audience = (session_config or {}).get("audience", "")
    persona = (session_config or {}).get("persona", "")

    dims_block = "\n".join(
        f"{i+1}. {d['name']} (weight {d['weight']:.2f}) — {d['criterion']}"
        for i, d in enumerate(IMAGE_DIMENSIONS)
    )
    gates_block = "\n".join(
        f"- {g['name']} (cap {g['cap']:.1f}) — {g['criterion']}"
        for g in IMAGE_GATES
    )
    return f"""You are a strict visual ad quality evaluator for Varsity Tutors SAT test prep on Facebook and Instagram.

CALIBRATION: You are scoring AI-GENERATED images, not human photography. Be critical. Scores cluster too high if you are not specific. Most AI images are mediocre. A score of 7 is genuinely good. 9–10 is exceptional and rare. Average score in a batch should be near 5–6. If you find yourself scoring everything above 7, you are being too lenient.

AD COPY (for message-alignment evaluation):
- Headline: {headline or "(none)"}
- Primary Text: {primary_text or "(none)"}
- CTA: {cta or "(none)"}
- Target audience: {audience or "(none)"}
- Persona: {persona or "(none)"}

DIMENSIONS — score 1–10 with a 1–2 sentence rationale. The rationale MUST name a specific visual element that earned that score (e.g. "the green CTA pill in the bottom-third"). Generic statements like "good composition" will be rejected.

{dims_block}

PENALTY GATES — answer true / false with a 1-sentence rationale. Trigger only when the issue is clearly visible.

{gates_block}

Return ONLY a JSON object with this exact shape:
{{
  "dimensions": {{
    "thumb_stop_potential": {{"score": 7, "rationale": "..."}},
    ...
  }},
  "penalty_gates": {{
    "has_ai_artifacts": {{"triggered": false, "rationale": "..."}},
    ...
  }}
}}"""


def _parse_response(text: str) -> dict[str, Any]:
    stripped = text.strip()
    m = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", stripped)
    if m:
        stripped = m.group(1).strip()
    return json.loads(stripped)


def evaluate_media(
    media_path: str,
    ad_copy: dict[str, Any],
    ad_id: str,
    variant_type: str,
    media_type: Literal["image", "video"] = "image",
    session_config: dict[str, Any] | None = None,
    model: str = DEFAULT_MODEL,
) -> MediaEvaluationResult:
    """Run the unified evaluator on one variant. Image path only (PI-02)."""
    if not Path(media_path).exists():
        return _failure_result(
            ad_id, variant_type, media_type, media_path,
            "file_not_found", f"{media_path} does not exist",
        )
    if media_type != "image":
        raise NotImplementedError(f"media_type={media_type} not yet supported")

    rubric_dims = IMAGE_DIMENSIONS
    rubric_gates = IMAGE_GATES
    prompt = _build_image_prompt(ad_copy, session_config)
    tokens = 0
    try:
        raw_payload, tokens = retry_with_backoff(
            lambda: _call_multimodal(media_path, prompt, model, media_type)
        )
        parsed = _parse_response(raw_payload)
    except (json.JSONDecodeError, ValueError) as e:
        return _failure_result(ad_id, variant_type, media_type, media_path,
                                "json_parse_failed", str(e), tokens=tokens)
    except Exception as e:
        return _failure_result(ad_id, variant_type, media_type, media_path,
                                "llm_call_failed", str(e), tokens=tokens)

    dimensions: dict[str, DimensionScore] = {}
    for d in rubric_dims:
        raw_d = parsed.get("dimensions", {}).get(d["name"], {})
        score = int(raw_d.get("score", 5))
        score = max(1, min(10, score))
        dimensions[d["name"]] = DimensionScore(
            score=score, weight=d["weight"],
            rationale=str(raw_d.get("rationale", "")).strip(),
        )
    gates: dict[str, GateEvaluation] = {}
    for g in rubric_gates:
        raw_g = parsed.get("penalty_gates", {}).get(g["name"], {})
        gates[g["name"]] = GateEvaluation(
            triggered=bool(raw_g.get("triggered", False)),
            rationale=str(raw_g.get("rationale", "")).strip(),
        )

    raw_score, penalty_mult, composite = compute_composite(dimensions, gates, rubric_gates)
    return MediaEvaluationResult(
        ad_id=ad_id, variant_type=variant_type, media_type=media_type,
        media_path=media_path, model_used=model, tokens_consumed=tokens,
        dimensions=dimensions, penalty_gates=gates,
        raw_score=raw_score, penalty_multiplier=penalty_mult,
        composite_score=composite,
    )


def _call_multimodal(
    media_path: str, prompt: str, model: str, media_type: str
) -> tuple[str, int]:
    """Call Gemini 2.5 Flash multimodal. Returns (text, total_tokens)."""
    from google.genai import types

    from generate.gemini_client import call_gemini_multimodal

    with open(media_path, "rb") as f:
        data = f.read()
    mime = "image/png" if media_type == "image" else "video/mp4"
    resp = call_gemini_multimodal(
        [types.Part.from_bytes(data=data, mime_type=mime), prompt],
        model=model, temperature=0.1, max_output_tokens=2048,
    )
    return resp.text, resp.total_tokens


def _failure_result(
    ad_id: str, variant_type: str, media_type: str, media_path: str,
    failure_reason: str, error_message: str, tokens: int = 0,
) -> MediaEvaluationResult:
    return MediaEvaluationResult(
        ad_id=ad_id, variant_type=variant_type, media_type=media_type,
        media_path=media_path, model_used=DEFAULT_MODEL, tokens_consumed=tokens,
        dimensions={}, penalty_gates={}, raw_score=0.0,
        penalty_multiplier=0.0, composite_score=0.0,
        failed=True, failure_reason=failure_reason, error_message=error_message,
    )
