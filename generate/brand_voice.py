"""Audience-specific brand voice profiles (P1-03, R1-Q6).

Provides VoiceProfile with tone, emotional drivers, vocabulary guidance,
and few-shot examples for generator and evaluator. Parent-facing vs
student-facing profiles with distinct tonal guidance.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_DEFAULT_BRAND_KB = "data/brand_knowledge.json"
_DEFAULT_REFERENCE_ADS = "data/reference_ads.json"

# Core brand attributes (apply to ALL audiences)
BRAND_CONSTANTS = ["empowering", "knowledgeable", "approachable", "results-focused"]

# Audience normalization
_AUDIENCE_MAP = {
    "parent": "parents",
    "parents": "parents",
    "student": "students",
    "students": "students",
    "family": "families",
    "families": "families",
    "both": "families",
}


@dataclass
class VoiceProfile:
    """Audience-specific brand voice profile with few-shot examples."""

    audience: str
    tone: list[str] = field(default_factory=list)
    emotional_drivers: list[str] = field(default_factory=list)
    vocabulary_guidance: dict[str, list[str]] = field(default_factory=dict)
    few_shot_examples: list[str] = field(default_factory=list)
    anti_examples: list[str] = field(default_factory=list)
    brand_constants: list[str] = field(default_factory=lambda: list(BRAND_CONSTANTS))


def _load_json(path: str, key: str | None = None) -> dict[str, Any] | list[Any]:
    """Load JSON file. If key given, return that key's value."""
    p = Path(path)
    if not p.is_absolute():
        p = Path(__file__).resolve().parents[1] / p
    if not p.exists():
        return {} if key else {}
    with open(p, encoding="utf-8") as f:
        data = json.load(f)
    if key:
        return data.get(key, {} if key != "ads" else [])
    return data


def _extract_drivers(raw: list[Any]) -> list[str]:
    """Extract driver/point strings from audience data."""
    out: list[str] = []
    for item in raw or []:
        if isinstance(item, dict):
            s = item.get("driver") or item.get("point") or ""
            if s:
                out.append(str(s))
        elif isinstance(item, str):
            out.append(item)
    return out


def _get_reference_examples(
    audience: str,
    brand: str = "Varsity Tutors",
    min_brand_voice: float = 6.5,
    max_examples: int = 5,
) -> list[str]:
    """Extract few-shot examples from reference ads by audience and quality."""
    data = _load_json(_DEFAULT_REFERENCE_ADS)
    ads = data.get("ads", []) if isinstance(data, dict) else []
    if not ads:
        return []

    # Map audience to audience_guess values
    aud_match = {"parents": ["parents"], "students": ["students", "both"], "families": ["parents", "both"]}
    matches = aud_match.get(audience, ["parents", "students", "both"])

    candidates: list[tuple[float, str]] = []
    for ad in ads:
        if ad.get("brand") != brand:
            continue
        guess = ad.get("audience_guess", "")
        if guess not in matches:
            continue
        scores = ad.get("human_scores") or ad.get("ai_rationales") or {}
        bv = scores.get("brand_voice")
        if bv is None:
            bv = 6.0
        if isinstance(bv, (int, float)) and bv >= min_brand_voice:
            text = (ad.get("primary_text") or "").strip()
            if text and len(text) > 30:
                candidates.append((float(bv), text[:300]))

    candidates.sort(key=lambda x: -x[0])
    return [t for _, t in candidates[:max_examples]]


def _get_anti_examples(audience: str) -> list[str]:
    """Return 1-2 off-brand examples for the audience."""
    if audience == "parents":
        return [
            "SAT prep. We do it. Online. With tutors. Sometimes it works. Try us.",
            "🔥 LIMITED TIME! Get 50% off our premium package!!! Don't miss out!!!",
        ]
    if audience == "students":
        return [
            "Hey kiddo, stressed about the big test? We've got you, fam!",
            "BUY NOW! Best SAT prep ever! Guaranteed 1500+ or your money back!",
        ]
    return [
        "SAT prep. We do it. Try us.",
    ]


def _normalize_audience(audience: str) -> str:
    """Normalize audience string to canonical key."""
    return _AUDIENCE_MAP.get(audience.lower().strip(), audience.lower() or "parents")


def get_voice_profile(audience: str) -> VoiceProfile:
    """Get audience-specific voice profile. Falls back to default for unknown audiences."""
    aud = _normalize_audience(audience)
    kb = _load_json(_DEFAULT_BRAND_KB)
    audiences = kb.get("audiences", {})

    if aud == "parents":
        a = audiences.get("parent", {})
        tone_raw = a.get("tone_register", "authoritative, reassuring, outcome-focused")
        tone = [t.strip() for t in tone_raw.split(",")] if isinstance(tone_raw, str) else list(tone_raw)
        return VoiceProfile(
            audience="parents",
            tone=tone or ["authoritative", "reassuring", "empathetic", "results-focused"],
            emotional_drivers=_extract_drivers(a.get("emotional_drivers", []))
            or ["College admissions anxiety", "Desire for expert guidance", "Value for money"],
            vocabulary_guidance={
                "prefer": ["your child", "expert", "personalized", "flexible", "results", "confidence"],
                "avoid": ["hey", "dude", "guaranteed", "limited time", "act now"],
            },
            few_shot_examples=_get_reference_examples("parents")
            or [
                "Is your child's SAT score holding them back from their dream school?",
                "Her SAT Score Jumped 360 Points! From 1010 to 1370 in Just 2 Months.",
            ],
            anti_examples=_get_anti_examples("parents"),
            brand_constants=list(BRAND_CONSTANTS),
        )

    if aud == "students":
        a = audiences.get("student", {})
        tone_raw = a.get("tone_register", "relatable, motivating, peer-like")
        tone = [t.strip() for t in tone_raw.split(",")] if isinstance(tone_raw, str) else list(tone_raw)
        return VoiceProfile(
            audience="students",
            tone=tone or ["relatable", "motivating", "confident", "peer-level"],
            emotional_drivers=_extract_drivers(a.get("emotional_drivers", []))
            or ["Test anxiety", "Desire for quick results", "Competitive edge", "Peer proof"],
            vocabulary_guidance={
                "prefer": ["you", "your potential", "strategies", "practice", "confidence", "ready"],
                "avoid": ["your child", "parents", "we understand moms", "limited offer"],
            },
            few_shot_examples=_get_reference_examples("students")
            or [
                "The SAT rewards strategy, not just knowledge. Smart students need smart test strategy.",
                "Your child already knows the material - they just need to learn how to use it efficiently.",
            ],
            anti_examples=_get_anti_examples("students"),
            brand_constants=list(BRAND_CONSTANTS),
        )

    # Default: families / both / unknown — use parent profile as base
    logger.warning("Unknown audience %r, using default (families) profile", audience)
    return get_voice_profile("parents")


def get_voice_for_prompt(audience: str) -> str:
    """Format VoiceProfile as prompt-injectable string for generator."""
    profile = get_voice_profile(audience)
    lines = [
        f"## Brand Voice — {profile.audience}",
        "",
        f"Tone: {', '.join(profile.tone)}",
        f"Emotional drivers: {', '.join(profile.emotional_drivers[:4])}",
        "",
        "Vocabulary — prefer: " + ", ".join(profile.vocabulary_guidance.get("prefer", [])[:6]),
        "Vocabulary — avoid: " + ", ".join(profile.vocabulary_guidance.get("avoid", [])[:6]),
        "",
        "On-brand examples:",
    ]
    for i, ex in enumerate(profile.few_shot_examples[:3], 1):
        lines.append(f"  {i}. \"{ex[:150]}{'...' if len(ex) > 150 else ''}\"")
    lines.append("")
    lines.append("Core brand (all audiences): " + ", ".join(profile.brand_constants))
    return "\n".join(lines)


def get_voice_for_evaluation(audience: str) -> str:
    """Format VoiceProfile as evaluator rubric string for Brand Voice dimension."""
    profile = get_voice_profile(audience)
    lines = [
        f"## Brand Voice Rubric — Target audience: {profile.audience}",
        "",
        f"Expected tone: {', '.join(profile.tone)}",
        f"Emotional drivers for this audience: {', '.join(profile.emotional_drivers[:4])}",
        "",
        "SCORE 9-10 (Perfectly on-brand for this audience):",
        "  - Matches tone descriptors; speaks directly to audience's emotional drivers",
        "  - Uses preferred vocabulary; avoids off-brand phrases",
    ]
    if profile.few_shot_examples:
        lines.append(f"  - Example: \"{profile.few_shot_examples[0][:120]}...\"")
    lines.append("")
    lines.append("SCORE 1-2 (Off-brand):")
    if profile.anti_examples:
        lines.append(f"  - Example: \"{profile.anti_examples[0]}\"")
    lines.append("  - Wrong tone for audience; too salesy, too casual, or generic")
    lines.append("")
    lines.append("Core brand constants (all audiences): " + ", ".join(profile.brand_constants))
    return "\n".join(lines)
