"""Ad copy generator using reference-decompose-recombine (P1-02, R2-Q1).

Takes ExpandedBrief, selects structural atoms from the pattern database,
and produces complete Meta ad copy (primary text, headline, description, CTA)
via Gemini Flash. Compatible with P1-04 evaluator input format.
"""

from __future__ import annotations

import json
import logging
import os
import random
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from generate.brief_expansion import ExpandedBrief
from generate.brand_voice import get_voice_for_prompt
from generate.competitive import query_patterns
from generate.seeds import get_ad_seed, load_global_seed
from iterate.ledger import log_event
from iterate.retry import retry_with_backoff

load_dotenv()

logger = logging.getLogger(__name__)

_DEFAULT_CONFIG = "data/config.yaml"

# Valid Meta CTA options — original + persona-specific (PB-05)
VALID_CTAS = frozenset({
    # Original
    "Learn More",
    "Get Started",
    "Sign Up",
    "Start Free Practice Test",
    "Book Now",
    # Persona-specific (PB-05)
    "Book Diagnostic",
    "Talk to an SAT specialist today",
    "See what score range is realistic in 8–10 weeks",
    "See how many scholarship dollars your score could unlock",
    "See what 1-on-1 changes",
    "Tell us about your child",
    "Tell us what went wrong",
    "See how we help students walk into the SAT feeling ready",
    "Get a tutor who keeps your child accountable",
    "See what real SAT tutoring looks like",
    "Let's build the plan that works for this child",
    "Give your child an expert they'll actually listen to",
})

# Audience normalization for pattern query (brief uses parent/parents, patterns use parents/students/both)
_AUDIENCE_MAP = {"parent": "parents", "parents": "parents", "student": "students", "students": "students"}

_CREATIVE_BRIEF_COPY_DIRECTIONS: dict[str, str] = {
    "gap_report": (
        "Write in an analytical, data-forward tone. Lead with a diagnostic insight "
        "or score gap. Use numbers, percentages, and comparisons. Frame the ad as "
        "a performance report — 'Here's where your child stands, here's the gap, "
        "here's the plan.' No flowery language. Short, direct sentences."
    ),
    "ugc_testimonial": (
        "Write as if a real parent or student is sharing their experience. Use first "
        "person ('My daughter...', 'I was worried...'). Conversational, authentic "
        "tone — not polished marketing copy. Include a specific detail or moment "
        "that makes it feel real. End with a genuine recommendation, not a hard sell."
    ),
    "before_after": (
        "Structure the copy as a transformation story. Start with the 'before' "
        "state (frustration, low score, anxiety) then pivot to the 'after' (confidence, "
        "score jump, readiness). Use a clear contrast. Include specific numbers for "
        "the score improvement. The hook should hint at the transformation."
    ),
    "lifestyle": (
        "Write aspirational, warm copy that paints a picture of life after SAT success. "
        "Focus on the emotional outcome — not just the score, but what it means "
        "(college acceptance, scholarship, family pride). Use vivid, sensory language. "
        "The tone should feel celebratory and forward-looking."
    ),
    "stat_focused": (
        "Lead with a bold, attention-grabbing statistic. The number IS the hook. "
        "Keep supporting copy minimal and punchy. Every sentence should reinforce "
        "the stat. Use short paragraphs or single-line statements. The CTA should "
        "feel like the obvious next step after seeing the number."
    ),
}


@dataclass
class GeneratedAd:
    """Complete Meta ad copy produced by reference-decompose-recombine."""

    ad_id: str
    primary_text: str
    headline: str
    description: str
    cta_button: str
    structural_atoms_used: list[dict[str, Any]] = field(default_factory=list)
    expanded_brief_id: str = ""
    generation_metadata: dict[str, Any] = field(default_factory=dict)

    def to_evaluator_input(self) -> dict[str, Any]:
        """Convert to format expected by P1-04 evaluator."""
        return {
            "ad_id": self.ad_id,
            "primary_text": self.primary_text,
            "headline": self.headline,
            "description": self.description,
            "cta_button": self.cta_button,
        }


def _get_audience_for_patterns(audience: str) -> str:
    """Map brief audience to pattern query key."""
    return _AUDIENCE_MAP.get(audience.lower(), "parents")


def _select_structural_atoms(
    campaign_goal: str,
    audience: str,
    top_n: int = 3,
    ad_seed: int | None = None,
) -> list[dict[str, Any]]:
    """Select 2-3 diverse structural atoms from pattern database.

    Queries by audience and optionally campaign_goal. Patterns may not have
    awareness/conversion in tags, so falls back to audience-only if empty.

    Uses ad_seed to shuffle candidates so different briefs with the same
    audience/goal get different atoms.  Deduplicates by hook_type to ensure
    structural diversity (at most 1 pattern per hook_type).
    """
    aud = _get_audience_for_patterns(audience)
    # Fetch a broader pool so we have enough after dedup
    pool_size = max(top_n * 3, 10)
    patterns = query_patterns(audience=aud, campaign_goal=campaign_goal, top_n=pool_size)
    if not patterns:
        patterns = query_patterns(audience=aud, top_n=pool_size)
    if not patterns:
        patterns = query_patterns(top_n=pool_size)

    # Seed-based shuffle so each brief gets a different ordering
    if ad_seed is not None:
        rng = random.Random(ad_seed)
        patterns = list(patterns)
        rng.shuffle(patterns)

    # Deduplicate by hook_type — at most 1 pattern per hook_type
    seen_hooks: set[str] = set()
    atoms: list[dict[str, Any]] = []
    for p in patterns:
        hook = p.get("hook_type", "")
        if hook in seen_hooks and hook:
            continue
        if hook:
            seen_hooks.add(hook)
        atoms.append({
            "pattern_id": p.get("pattern_id", ""),
            "hook_type": hook,
            "body_pattern": p.get("body_pattern", ""),
            "cta_style": p.get("cta_style", ""),
            "emotional_register": p.get("emotional_register", ""),
            "hook_text": (p.get("hook_text") or p.get("ad_text", ""))[:100],
        })
        if len(atoms) >= top_n:
            break
    return atoms


def _build_generation_prompt(
    expanded_brief: ExpandedBrief,
    atoms: list[dict[str, Any]],
    creative_brief: str = "auto",
) -> str:
    """Construct recombination prompt with Nerdy rules, persona context, and Meta ad structure."""
    brief = expanded_brief.original_brief
    campaign_goal = brief.get("campaign_goal", "awareness")
    audience = brief.get("audience", "parents")

    atoms_block = "\n".join(
        f"- {a.get('hook_type', '?')} hook, {a.get('body_pattern', '?')} body, {a.get('cta_style', '?')} CTA: \"{a.get('hook_text', '')}...\""
        for a in atoms
    )

    emotional = ", ".join(expanded_brief.emotional_angles[:3]) if expanded_brief.emotional_angles else "N/A"
    value_props = ", ".join(expanded_brief.value_propositions[:3]) if expanded_brief.value_propositions else "N/A"
    differentiators = ", ".join(expanded_brief.key_differentiators[:3]) if expanded_brief.key_differentiators else "N/A"
    constraints = "; ".join(expanded_brief.constraints[:3]) if expanded_brief.constraints else "None"

    # CTA options — persona-specific preferred + goal defaults
    persona_cta = ""
    # Try persona profile preferred_cta from brand KB
    if hasattr(expanded_brief, "persona") and expanded_brief.persona:
        try:
            from generate.brief_expansion import _load_brand_knowledge, _get_persona_profile
            kb = _load_brand_knowledge()
            profile = _get_persona_profile(kb, expanded_brief.persona)
            if profile and profile.get("preferred_cta"):
                persona_cta = f"\nPreferred CTA for this persona: {profile['preferred_cta']}"
        except Exception:
            pass
    # Fallback: extract from hooks
    if not persona_cta and hasattr(expanded_brief, "suggested_hooks") and expanded_brief.suggested_hooks:
        ctas_from_hooks = list({h.get("cta_text", "") for h in expanded_brief.suggested_hooks if h.get("cta_text")})
        if ctas_from_hooks:
            persona_cta = f"\nPreferred CTA for this persona: {ctas_from_hooks[0]}"

    cta_options = {
        "awareness": ["Learn More", "Get Started"],
        "conversion": ["Sign Up", "Start Free Practice Test", "Book Now", "Book Diagnostic"],
    }
    goal_ctas = cta_options.get(campaign_goal, list(VALID_CTAS)[:5])
    cta_hint = ", ".join(goal_ctas)

    # Persona hooks as inspiration
    hooks_block = ""
    if hasattr(expanded_brief, "suggested_hooks") and expanded_brief.suggested_hooks:
        hook_lines = [f'  "{h["hook_text"]}"' for h in expanded_brief.suggested_hooks[:3]]
        hooks_block = f"""
## Proven Hooks for This Persona (use as INSPIRATION — do NOT copy verbatim)
{chr(10).join(hook_lines)}"""

    # Offer context for conversion
    offer_block = ""
    if hasattr(expanded_brief, "offer_context") and expanded_brief.offer_context and campaign_goal == "conversion":
        offer = expanded_brief.offer_context
        offer_block = f"""
## Offer Context (weave into copy naturally, don't list features)
- {offer.get('score_improvement', '')}
- Model: {offer.get('model', '')}"""

    # Persona voice
    persona_voice = ""
    if hasattr(expanded_brief, "persona") and expanded_brief.persona:
        from generate.brand_voice import get_voice_for_persona
        persona_voice = get_voice_for_persona(expanded_brief.persona)

    voice_block = persona_voice or get_voice_for_prompt(audience)

    creative_direction_block = ""
    if creative_brief and creative_brief != "auto" and creative_brief in _CREATIVE_BRIEF_COPY_DIRECTIONS:
        creative_direction_block = f"""
## CREATIVE BRIEF STYLE (highest priority — override default tone)
{_CREATIVE_BRIEF_COPY_DIRECTIONS[creative_brief]}
"""

    return f"""You are writing a Meta (Facebook/Instagram) ad for Varsity Tutors SAT Tutoring. Use the reference-decompose-recombine approach: draw from proven structural patterns, adapt and recombine — do NOT copy verbatim.

## NERDY LANGUAGE RULES (MANDATORY)
- ALWAYS say "your child" — NEVER "your student"
- ALWAYS say "SAT Tutoring" — NEVER "SAT Prep"
- Use plain parent language, not corporate marketing speak
- NO fake urgency: "spots filling fast", "limited enrollment", "don't miss out"
- NO vague promises: "unlock potential", "maximize score", "tailored support"
- Include SPECIFIC mechanisms: how the digital SAT works, diagnostic process, session structure
- Score claims MUST have conditions: "200 points in 16 sessions", NOT bare "gain 200 points"
- Calendar urgency is OK: test dates, application deadlines, weeks remaining

## META AD STRUCTURE (follow this format)
Hook (1 scroll-stopping sentence) → Short pattern interrupt explanation (2–3 lines max) → Micro-commitment CTA

## Expanded Brief Context
- Audience: {audience}
- Campaign goal: {campaign_goal}
- Emotional angles: {emotional}
- Value propositions: {value_props}
- Key differentiators: {differentiators}
- Constraints: {constraints}
{hooks_block}

## Proven Structural Patterns (draw from these, recombine creatively)
{atoms_block}
{offer_block}

## Meta Ad Format
- Primary text: Hook in first line (~125 chars visible), then 2-3 lines of pattern interrupt. Can be longer but front-load the hook.
- Headline: 5-8 words, benefit-driven
- Description: Concise, often truncated on mobile
- CTA button: Best fit from: {cta_hint}{persona_cta}

{voice_block}
{creative_direction_block}
Output ONLY valid JSON (no markdown, no code fences):
{{
  "primary_text": "<full primary text>",
  "headline": "<headline>",
  "description": "<description>",
  "cta_button": "<exact CTA from options above>"
}}"""


def _parse_generation_response(
    response: str,
    ad_id: str,
    structural_atoms_used: list[dict[str, Any]],
    expanded_brief_id: str,
    metadata: dict[str, Any],
) -> GeneratedAd:
    """Parse JSON response into GeneratedAd. Handles malformed input gracefully."""
    stripped = response.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", stripped)
    if match:
        stripped = match.group(1).strip()

    try:
        data = json.loads(stripped)
    except json.JSONDecodeError as e:
        logger.warning("Ad generation: malformed JSON, returning partial ad: %s", e)
        return GeneratedAd(
            ad_id=ad_id,
            primary_text="",
            headline="",
            description="",
            cta_button="Learn More",
            structural_atoms_used=structural_atoms_used,
            expanded_brief_id=expanded_brief_id,
            generation_metadata={**metadata, "parse_error": str(e)},
        )

    primary = str(data.get("primary_text", "") or "").strip()
    headline = str(data.get("headline", "") or "").strip()
    description = str(data.get("description", "") or "").strip()
    cta = str(data.get("cta_button", "") or "Learn More").strip()

    # Accept valid CTAs or reasonable variants (strip trailing punctuation)
    cta_clean = cta.rstrip(".!").strip()
    if not cta_clean or (cta_clean not in VALID_CTAS and cta not in VALID_CTAS):
        # Try fuzzy match: check if any valid CTA starts with the generated one
        matched = next((v for v in VALID_CTAS if v.lower().startswith(cta_clean.lower()[:20])), None)
        cta = matched or "Learn More"
    else:
        cta = cta_clean if cta_clean in VALID_CTAS else cta

    return GeneratedAd(
        ad_id=ad_id,
        primary_text=primary or "(No primary text generated)",
        headline=headline or "(No headline)",
        description=description or "(No description)",
        cta_button=cta,
        structural_atoms_used=structural_atoms_used,
        expanded_brief_id=expanded_brief_id,
        generation_metadata=metadata,
    )


def _call_gemini(prompt: str) -> str:
    """Call Gemini Flash for ad generation."""
    from google import genai
    from google.genai import types

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set in environment")

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.7,
            max_output_tokens=1024,
        ),
    )
    return response.text or ""


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


def _compliance_pre_check(ad: GeneratedAd) -> list[str]:
    """Scan generated ad for critical Nerdy violations before publishing.

    Returns list of violation descriptions. Empty = clean.
    """
    from generate.compliance import check_compliance

    full_text = f"{ad.primary_text} {ad.headline} {ad.description}"
    result = check_compliance(full_text)
    return [f"{v.rule_name}: {v.matched_text}" for v in result.critical_violations]


def generate_ad(
    expanded_brief: ExpandedBrief,
    seed: int | None = None,
    cycle_number: int = 0,
    ledger_path: str | None = None,
    creative_brief: str = "auto",
) -> GeneratedAd:
    """Generate Meta ad copy from expanded brief using reference-decompose-recombine.

    Selects structural atoms from pattern database, builds recombination prompt,
    calls Gemini Flash, parses response, logs AdGenerated event to ledger.

    Args:
        expanded_brief: Output from P1-01 expand_brief().
        seed: Optional seed for deterministic ad_id. If None, derived from brief_id + cycle.
        cycle_number: Regeneration cycle (0 = first draft).
        ledger_path: Override ledger path.
        creative_brief: Creative brief style to influence copy tone and structure.

    Returns:
        GeneratedAd with all 4 Meta components, compatible with P1-04 evaluator.
    """
    brief = expanded_brief.original_brief
    brief_id = brief.get("brief_id", "brief_unknown")
    campaign_goal = brief.get("campaign_goal", "awareness")
    audience = brief.get("audience", "parents")

    global_seed = load_global_seed()
    actual_seed = seed if seed is not None else get_ad_seed(global_seed, brief_id, cycle_number)

    ad_id = f"ad_{brief_id}_c{cycle_number}_{actual_seed}"

    atoms = _select_structural_atoms(campaign_goal, audience, ad_seed=actual_seed)
    prompt = _build_generation_prompt(expanded_brief, atoms, creative_brief=creative_brief)

    def _do_call() -> str:
        return _call_gemini(prompt)

    response = retry_with_backoff(_do_call)
    tokens_estimate = (len(prompt) + len(response)) // 4
    metadata = {
        "model_used": "gemini-2.0-flash",
        "tokens_consumed": tokens_estimate,
        "seed": actual_seed,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    result = _parse_generation_response(
        response, ad_id, atoms, brief_id, metadata
    )

    # PB-12: Compliance pre-check — log violations if found
    violations = _compliance_pre_check(result)
    if violations:
        logger.warning(
            "Ad %s has %d compliance violations: %s",
            ad_id, len(violations), violations,
        )
        result.generation_metadata["compliance_violations"] = violations

    cfg = _load_config()
    led_path = ledger_path or cfg.get("ledger_path", "data/ledger.jsonl")

    log_event(
        led_path,
        {
            "event_type": "AdGenerated",
            "ad_id": result.ad_id,
            "brief_id": brief_id,
            "cycle_number": cycle_number,
            "action": "generation",
            "tokens_consumed": tokens_estimate,
            "model_used": "gemini-2.0-flash",
            "seed": str(actual_seed),
            "inputs": {
                "expanded_brief_id": brief_id,
                "structural_atoms_count": len(atoms),
                "voice_profile_audience": audience,
            },
            "outputs": {
                "primary_text": result.primary_text,
                "primary_text_len": len(result.primary_text),
                "headline": result.headline,
                "description": result.description,
                "cta_button": result.cta_button,
            },
        },
    )

    return result
