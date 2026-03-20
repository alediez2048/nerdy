"""LLM-powered brief expansion with grounding constraints (P1-01, PB-04).

Transforms minimal campaign briefs into rich creative briefs using ONLY
verified facts from the brand knowledge base. Injects competitive landscape
context, persona psychology, proven hooks, offer positioning, and Nerdy
messaging rules. Prevents hallucination at the source.
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

from generate.competitive import get_landscape_context
from generate.seeds import get_ad_seed, load_global_seed
from iterate.ledger import log_event
from iterate.retry import retry_with_backoff

load_dotenv()

logger = logging.getLogger(__name__)

# Default paths (relative to project root)
_DEFAULT_BRAND_KB = "data/brand_knowledge.json"
_DEFAULT_CONFIG = "data/config.yaml"

# Audience normalization
_AUDIENCE_TO_KB = {"parent": "parent", "parents": "parent", "student": "student", "students": "student"}
_AUDIENCE_TO_COMPETITIVE = {"parent": "parents", "parents": "parents", "student": "students", "students": "students"}

# Default persona per audience when persona is "auto" or None
_DEFAULT_PERSONA = {"parent": "suburban_optimizer", "parents": "suburban_optimizer", "student": None, "students": None}


@dataclass
class ExpandedBrief:
    """Rich creative brief produced from minimal input. All facts traceable to brand KB."""

    original_brief: dict[str, Any]
    audience_profile: dict[str, Any]
    brand_facts: list[dict[str, Any] | str]
    competitive_context: str
    emotional_angles: list[str]
    value_propositions: list[str]
    key_differentiators: list[str]
    constraints: list[str]
    # PB-04 additions
    persona: str | None = None
    suggested_hooks: list[dict[str, Any]] = field(default_factory=list)
    offer_context: dict[str, Any] | None = None
    messaging_rules: dict[str, Any] | None = None


def _load_brand_knowledge(path: str | None = None) -> dict[str, Any]:
    """Load brand knowledge base. Raises FileNotFoundError if missing."""
    p = Path(path or _DEFAULT_BRAND_KB)
    if not p.is_absolute():
        p = Path(__file__).resolve().parents[1] / p
    if not p.exists():
        raise FileNotFoundError(f"Brand knowledge base not found: {p}")
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def _get_audience_for_kb(audience: str) -> str:
    return _AUDIENCE_TO_KB.get(audience.lower(), "parent")


def _get_audience_for_competitive(audience: str) -> str:
    return _AUDIENCE_TO_COMPETITIVE.get(audience.lower(), "parents")


def _resolve_persona(persona: str | None, audience: str) -> str | None:
    """Resolve persona: explicit value, 'auto'/None → default for audience."""
    if persona and persona != "auto":
        return persona
    return _DEFAULT_PERSONA.get(audience.lower())


def _get_persona_profile(kb: dict[str, Any], persona: str) -> dict[str, Any] | None:
    """Load persona profile from brand KB."""
    return kb.get("personas", {}).get(persona)


def _get_offer_context(kb: dict[str, Any]) -> dict[str, Any] | None:
    """Load offer positioning from brand KB."""
    return kb.get("offer")


def _get_messaging_rules(kb: dict[str, Any]) -> dict[str, Any] | None:
    """Load messaging do's/don'ts from brand KB."""
    return kb.get("messaging_rules")


def _gather_brand_facts_for_brief(brief: dict[str, Any], kb: dict[str, Any]) -> dict[str, Any]:
    """Extract audience- and product-relevant facts for prompt injection."""
    audience_raw = brief.get("audience", "parents")
    audience_kb = _get_audience_for_kb(audience_raw)
    product_raw = (brief.get("product") or "").lower()

    facts: dict[str, Any] = {
        "brand": kb.get("brand", {}),
        "audience": {},
        "products": {},
        "compliance": kb.get("compliance", {}),
        "ctas": kb.get("ctas", {}),
    }

    audiences = kb.get("audiences", {})
    if audience_kb in audiences:
        facts["audience"] = audiences[audience_kb]

    products = kb.get("products", {})
    if "sat" in product_raw or "sat prep" in product_raw or "sat tutoring" in product_raw or not product_raw:
        # Try sat_tutoring first (PB-01), fall back to sat_prep
        if "sat_tutoring" in products:
            facts["products"] = {"sat_tutoring": products["sat_tutoring"]}
        elif "sat_prep" in products:
            facts["products"] = {"sat_prep": products["sat_prep"]}
    elif product_raw and products:
        for key, val in products.items():
            if product_raw in key or key in product_raw:
                facts["products"][key] = val
                break

    return facts


def _build_expansion_prompt(
    brief: dict[str, Any],
    brand_facts: dict[str, Any],
    competitive_context: str,
    persona_profile: dict[str, Any] | None = None,
    hooks: list[dict[str, Any]] | None = None,
    offer: dict[str, Any] | None = None,
    messaging: dict[str, Any] | None = None,
) -> str:
    """Construct grounding-constrained expansion prompt with persona context."""
    audience = brief.get("audience", "parents")
    campaign_goal = brief.get("campaign_goal", "awareness")
    product = brief.get("product", "SAT Tutoring")
    angle = brief.get("angle", "")
    hook = brief.get("hook", "")

    # Format verified facts
    facts_parts: list[str] = []
    brand = brand_facts.get("brand", {})
    if brand:
        facts_parts.append(f"Brand: {brand.get('name', 'Varsity Tutors')}")
        facts_parts.append(f"Voice: {', '.join(brand.get('voice', []))}")
        facts_parts.append(f"Positioning: {brand.get('positioning', '')}")

    aud = brand_facts.get("audience", {})
    if aud:
        pain_points = aud.get("pain_points", [])
        if pain_points:
            pts = [p.get("point", p) if isinstance(p, dict) else str(p) for p in pain_points]
            facts_parts.append(f"Audience pain points: {pts}")
        drivers = aud.get("emotional_drivers", [])
        if drivers:
            drv = [d.get("driver", d) if isinstance(d, dict) else str(d) for d in drivers]
            facts_parts.append(f"Emotional drivers: {drv}")
        facts_parts.append(f"Tone: {aud.get('tone_register', '')}")

    prods = brand_facts.get("products", {})
    for prod_val in prods.values():
        if isinstance(prod_val, dict):
            for c in prod_val.get("verified_claims", []):
                claim_text = c.get("claim", c) if isinstance(c, dict) else str(c)
                facts_parts.append(f"Verified claim: {claim_text}")

    compliance = brand_facts.get("compliance", {})
    never = compliance.get("never_claim", [])
    always = compliance.get("always_include", [])
    facts_block = "\n".join(facts_parts) if facts_parts else "(No facts loaded)"

    # Persona section
    persona_block = ""
    if persona_profile:
        persona_block = f"""
## Target Persona
Description: {persona_profile.get('description', '')}
Psychology: {persona_profile.get('psychology', '')}
Trigger: {persona_profile.get('trigger', '')}
Funnel position: {persona_profile.get('funnel_position', '')}
Key needs: {', '.join(persona_profile.get('key_needs', []))}
Preferred CTA: {persona_profile.get('preferred_cta', '')}

Tailor emotional angles and value propositions to this specific persona's psychology and needs."""

    # Hooks section
    hooks_block = ""
    if hooks:
        hook_lines = [f'{i+1}. "{h["hook_text"]}"' for i, h in enumerate(hooks)]
        hooks_block = f"""
## Proven Hooks for This Persona (use as inspiration, do NOT copy verbatim)
{chr(10).join(hook_lines)}"""

    # Offer section (conversion only)
    offer_block = ""
    if offer and campaign_goal == "conversion":
        offer_block = f"""
## Offer Context (for conversion campaigns)
Model: {offer.get('model', '')}
Score improvement: {offer.get('score_improvement', '')}
Recommended plan: {json.dumps(offer.get('recommended_plan', {}), indent=2)}
Include specific pricing comparisons vs competitors when relevant."""

    # Messaging rules
    messaging_block = ""
    if messaging:
        dos = [d.get("rule", d) if isinstance(d, dict) else str(d) for d in messaging.get("dos", [])]
        donts = [d.get("rule", d) if isinstance(d, dict) else str(d) for d in messaging.get("donts", [])]
        messaging_block = f"""
## Nerdy Messaging Rules (MANDATORY)
ALWAYS:
{chr(10).join(f'- {d}' for d in dos[:6])}

NEVER:
{chr(10).join(f'- {d}' for d in donts)}"""

    return f"""You are expanding a minimal ad brief into a rich creative brief for Varsity Tutors (Nerdy) SAT Tutoring ads on Meta (Facebook/Instagram).

CRITICAL: Use ONLY the following verified facts. Do NOT invent statistics, testimonials, pricing, or product claims. Creative framing is allowed — but factual content must come from verified facts only.

## Verified Facts (USE ONLY THESE)
{facts_block}

## Compliance Rules
Never claim: {never}
Always include: {always}
{persona_block}
{hooks_block}

## Market Context (for differentiation, not to copy)
{competitive_context}
{offer_block}
{messaging_block}

## Minimal Brief
- Audience: {audience}
- Campaign goal: {campaign_goal}
- Product: {product}
- Angle: {angle or '(none)'}
- Hook preference: {hook or '(none)'}

Expand this into a rich creative brief. Output ONLY valid JSON (no markdown, no code fences) with these exact keys:
{{
  "audience_profile": {{"pain_points": [...], "emotional_drivers": [...], "tone": "..."}},
  "brand_facts": [{{"claim": "...", "source": "..."}}],
  "competitive_context_summary": "1-2 sentence summary of how to differentiate",
  "emotional_angles": ["angle1", "angle2", "angle3"],
  "value_propositions": ["vp1", "vp2"],
  "key_differentiators": ["diff1", "diff2"],
  "constraints": ["constraint1", "constraint2"]
}}

Every item in brand_facts MUST be traceable to the verified facts above."""


def _parse_expansion_response(response: str, original_brief: dict[str, Any]) -> ExpandedBrief:
    """Parse JSON response from Gemini into ExpandedBrief."""
    stripped = response.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", stripped)
    if match:
        stripped = match.group(1).strip()

    try:
        data = json.loads(stripped)
    except json.JSONDecodeError as e:
        logger.warning("Brief expansion: malformed JSON response, returning partial: %s", e)
        return ExpandedBrief(
            original_brief=original_brief,
            audience_profile={},
            brand_facts=[],
            competitive_context="",
            emotional_angles=[],
            value_propositions=[],
            key_differentiators=[],
            constraints=[],
        )

    def _list(val: Any, default: list[str] | None = None) -> list:
        if val is None:
            return default or []
        if isinstance(val, list):
            return [str(x) for x in val]
        return [str(val)]

    def _dict(val: Any) -> dict:
        return val if isinstance(val, dict) else {}

    brand_facts_raw = data.get("brand_facts", [])
    brand_facts: list[dict[str, Any] | str] = []
    for bf in brand_facts_raw if isinstance(brand_facts_raw, list) else []:
        brand_facts.append(bf if isinstance(bf, dict) else str(bf))

    return ExpandedBrief(
        original_brief=original_brief,
        audience_profile=_dict(data.get("audience_profile")),
        brand_facts=brand_facts,
        competitive_context=data.get("competitive_context_summary", "") or "",
        emotional_angles=_list(data.get("emotional_angles")),
        value_propositions=_list(data.get("value_propositions")),
        key_differentiators=_list(data.get("key_differentiators")),
        constraints=_list(data.get("constraints")),
    )


def _call_gemini(prompt: str) -> tuple[str, int]:
    """Call Gemini Flash for brief expansion. Returns (text, total_tokens)."""
    from generate.gemini_client import call_gemini
    resp = call_gemini(prompt, temperature=0.3, max_output_tokens=2048)
    return resp.text, resp.total_tokens


def _load_config() -> dict[str, Any]:
    """Load config.yaml for ledger_path and other params."""
    import yaml

    p = Path(_DEFAULT_CONFIG)
    if not p.is_absolute():
        p = Path(__file__).resolve().parents[1] / p
    if not p.exists():
        return {"ledger_path": "data/ledger.jsonl"}
    with open(p, encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    return cfg


def expand_brief(
    brief: dict[str, Any],
    brand_kb_path: str | None = None,
    ledger_path: str | None = None,
    persona: str | None = None,
) -> ExpandedBrief:
    """Expand a minimal brief into a rich, grounded creative brief.

    Loads verified facts from brand_knowledge.json, injects competitive
    context, persona psychology, proven hooks, offer positioning, and
    Nerdy messaging rules. Logs expansion event to the decision ledger.

    Args:
        brief: Minimal brief with campaign_goal, audience, product; optional angle, hook, brief_id.
        brand_kb_path: Override path to brand_knowledge.json.
        ledger_path: Override path to ledger (default from config).
        persona: Persona key (e.g., "athlete_recruit"). "auto"/None uses audience default.

    Returns:
        ExpandedBrief with all fields populated from verified facts + LLM framing.
    """
    kb = _load_brand_knowledge(brand_kb_path)
    brand_facts = _gather_brand_facts_for_brief(brief, kb)

    audience = brief.get("audience", "parents")
    campaign_goal = brief.get("campaign_goal", "awareness")
    aud_comp = _get_audience_for_competitive(audience)
    competitive_context = get_landscape_context(audience=aud_comp, campaign_goal=campaign_goal)

    # PB-04: Resolve persona and load context
    resolved_persona = _resolve_persona(persona, audience)
    persona_profile = _get_persona_profile(kb, resolved_persona) if resolved_persona else None

    # Load hooks for persona
    hooks: list[dict[str, Any]] = []
    if resolved_persona:
        try:
            from generate.hooks import get_hooks_for_persona
            cfg = _load_config()
            global_seed = load_global_seed()
            brief_id = brief.get("brief_id", "brief_unknown")
            seed = get_ad_seed(global_seed, brief_id, 0)
            hooks = get_hooks_for_persona(resolved_persona, n=3, seed=seed)
        except Exception as e:
            logger.warning("Failed to load hooks for persona %s: %s", resolved_persona, e)

    # Load offer context (conversion only)
    offer = _get_offer_context(kb) if campaign_goal == "conversion" else None

    # Load messaging rules
    messaging = _get_messaging_rules(kb)

    prompt = _build_expansion_prompt(
        brief, brand_facts, competitive_context,
        persona_profile=persona_profile,
        hooks=hooks,
        offer=offer,
        messaging=messaging,
    )

    def _do_call() -> tuple[str, int]:
        return _call_gemini(prompt)

    response, tokens_used = retry_with_backoff(_do_call)
    result = _parse_expansion_response(response, brief)

    # Set PB-04 fields
    result.persona = resolved_persona
    result.suggested_hooks = hooks
    result.offer_context = offer
    result.messaging_rules = messaging

    # Log to ledger
    cfg = _load_config()
    led_path = ledger_path or cfg.get("ledger_path", "data/ledger.jsonl")
    brief_id = brief.get("brief_id", "brief_unknown")
    global_seed = load_global_seed()
    seed = get_ad_seed(global_seed, brief_id, 0)
    tokens_actual = tokens_used or (len(prompt) + len(response)) // 4

    log_event(
        led_path,
        {
            "event_type": "BriefExpanded",
            "ad_id": None,
            "brief_id": brief_id,
            "cycle_number": 0,
            "action": "brief-expansion",
            "tokens_consumed": tokens_actual,
            "model_used": "gemini-2.0-flash",
            "seed": str(seed),
            "inputs": {"brief": brief, "persona": resolved_persona},
            "outputs": {
                "emotional_angles": result.emotional_angles,
                "value_propositions": result.value_propositions,
                "key_differentiators": result.key_differentiators,
                "persona": resolved_persona,
                "hooks_used": [h.get("hook_id") for h in hooks],
            },
        },
    )

    return result
