"""LLM-powered brief expansion with grounding constraints (P1-01, R3-Q5).

Transforms minimal campaign briefs into rich creative briefs using ONLY
verified facts from the brand knowledge base. Injects competitive landscape
context from the pattern database. Prevents hallucination at the source.
"""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass
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

# Audience normalization: brief may say "parent"/"parents" -> brand KB uses "parent"
_AUDIENCE_TO_KB = {"parent": "parent", "parents": "parent", "student": "student", "students": "student"}
_AUDIENCE_TO_COMPETITIVE = {"parent": "parents", "parents": "parents", "student": "students", "students": "students"}


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
    """Map brief audience to brand KB key (parent|student)."""
    return _AUDIENCE_TO_KB.get(audience.lower(), "parent")


def _get_audience_for_competitive(audience: str) -> str:
    """Map brief audience to competitive context key (parents|students)."""
    return _AUDIENCE_TO_COMPETITIVE.get(audience.lower(), "parents")


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

    # Audience-specific
    audiences = kb.get("audiences", {})
    if audience_kb in audiences:
        facts["audience"] = audiences[audience_kb]

    # Product-specific (sat_prep for SAT prep)
    products = kb.get("products", {})
    if "sat" in product_raw or "sat prep" in product_raw or not product_raw:
        if "sat_prep" in products:
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
) -> str:
    """Construct grounding-constrained expansion prompt."""
    audience = brief.get("audience", "parents")
    campaign_goal = brief.get("campaign_goal", "awareness")
    product = brief.get("product", "SAT prep")
    angle = brief.get("angle", "")
    hook = brief.get("hook", "")

    # Format verified facts for injection
    facts_block_parts: list[str] = []

    brand = brand_facts.get("brand", {})
    if brand:
        facts_block_parts.append(f"Brand: {brand.get('name', 'Varsity Tutors')}")
        facts_block_parts.append(f"Voice: {', '.join(brand.get('voice', []))}")
        facts_block_parts.append(f"Positioning: {brand.get('positioning', '')}")

    aud = brand_facts.get("audience", {})
    if aud:
        pain_points = aud.get("pain_points", [])
        if pain_points:
            pts = [p.get("point", p) if isinstance(p, dict) else str(p) for p in pain_points]
            facts_block_parts.append(f"Audience pain points: {pts}")
        drivers = aud.get("emotional_drivers", [])
        if drivers:
            drv = [d.get("driver", d) if isinstance(d, dict) else str(d) for d in drivers]
            facts_block_parts.append(f"Emotional drivers: {drv}")
        facts_block_parts.append(f"Tone: {aud.get('tone_register', '')}")

    prods = brand_facts.get("products", {})
    for prod_key, prod_val in prods.items():
        if isinstance(prod_val, dict):
            claims = prod_val.get("verified_claims", [])
            for c in claims:
                claim_text = c.get("claim", c) if isinstance(c, dict) else str(c)
                facts_block_parts.append(f"Verified claim: {claim_text}")

    compliance = brand_facts.get("compliance", {})
    never = compliance.get("never_claim", [])
    always = compliance.get("always_include", [])

    facts_block = "\n".join(facts_block_parts) if facts_block_parts else "(No facts loaded)"

    return f"""You are expanding a minimal ad brief into a rich creative brief for Varsity Tutors (Nerdy) SAT test prep ads on Meta (Facebook/Instagram).

CRITICAL: Use ONLY the following verified facts. Do NOT invent statistics, testimonials, pricing, or product claims. If a fact is not in the list below, do not use it. Creative framing (emotional angles, story structures) is allowed — but the factual content must come from the verified facts only.

## Verified Facts (USE ONLY THESE)
{facts_block}

## Compliance Rules
Never claim: {never}
Always include: {always}

## Market Context (for differentiation, not to copy)
{competitive_context}

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

Every item in brand_facts MUST be traceable to the verified facts above. Do not add claims that are not in the verified list."""


def _parse_expansion_response(response: str, original_brief: dict[str, Any]) -> ExpandedBrief:
    """Parse JSON response from Gemini into ExpandedBrief. Handles malformed input gracefully."""
    stripped = response.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", stripped)
    if match:
        stripped = match.group(1).strip()

    try:
        data = json.loads(stripped)
    except json.JSONDecodeError as e:
        logger.warning("Brief expansion: malformed JSON response, returning partial expansion: %s", e)
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
        if isinstance(val, dict):
            return val
        return {}

    audience_profile = _dict(data.get("audience_profile"))
    brand_facts_raw = data.get("brand_facts", [])
    brand_facts: list[dict[str, Any] | str] = []
    for bf in brand_facts_raw if isinstance(brand_facts_raw, list) else []:
        if isinstance(bf, dict):
            brand_facts.append(bf)
        else:
            brand_facts.append(str(bf))

    competitive_summary = data.get("competitive_context_summary", "") or ""
    emotional_angles = _list(data.get("emotional_angles"), [])
    value_propositions = _list(data.get("value_propositions"), [])
    key_differentiators = _list(data.get("key_differentiators"), [])
    constraints = _list(data.get("constraints"), [])

    return ExpandedBrief(
        original_brief=original_brief,
        audience_profile=audience_profile,
        brand_facts=brand_facts,
        competitive_context=competitive_summary,
        emotional_angles=emotional_angles,
        value_propositions=value_propositions,
        key_differentiators=key_differentiators,
        constraints=constraints,
    )


def _call_gemini(prompt: str) -> str:
    """Call Gemini Flash for brief expansion. Returns raw response text."""
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
            temperature=0.3,
            max_output_tokens=2048,
        ),
    )
    return response.text or ""


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
) -> ExpandedBrief:
    """Expand a minimal brief into a rich, grounded creative brief.

    Loads verified facts from brand_knowledge.json, injects competitive
    context from get_landscape_context(), and calls Gemini with grounding
    constraints. Logs expansion event to the decision ledger.

    Args:
        brief: Minimal brief with campaign_goal, audience, product; optional angle, hook, brief_id.
        brand_kb_path: Override path to brand_knowledge.json.
        ledger_path: Override path to ledger (default from config).

    Returns:
        ExpandedBrief with all fields populated from verified facts + LLM framing.
    """
    kb = _load_brand_knowledge(brand_kb_path)
    brand_facts = _gather_brand_facts_for_brief(brief, kb)

    audience = brief.get("audience", "parents")
    campaign_goal = brief.get("campaign_goal", "awareness")
    aud_comp = _get_audience_for_competitive(audience)
    competitive_context = get_landscape_context(audience=aud_comp, campaign_goal=campaign_goal)

    prompt = _build_expansion_prompt(brief, brand_facts, competitive_context)

    def _do_call() -> str:
        return _call_gemini(prompt)

    response = retry_with_backoff(_do_call)
    result = _parse_expansion_response(response, brief)

    # Log to ledger
    cfg = _load_config()
    led_path = ledger_path or cfg.get("ledger_path", "data/ledger.jsonl")
    brief_id = brief.get("brief_id", "brief_unknown")
    global_seed = load_global_seed()
    seed = get_ad_seed(global_seed, brief_id, 0)

    # Estimate tokens (prompt + response ~4 chars per token)
    tokens_estimate = (len(prompt) + len(response)) // 4

    log_event(
        led_path,
        {
            "event_type": "BriefExpanded",
            "ad_id": None,
            "brief_id": brief_id,
            "cycle_number": 0,
            "action": "brief-expansion",
            "tokens_consumed": tokens_estimate,
            "model_used": "gemini-2.0-flash",
            "seed": str(seed),
            "inputs": {"brief": brief},
            "outputs": {
                "emotional_angles": result.emotional_angles,
                "value_propositions": result.value_propositions,
                "key_differentiators": result.key_differentiators,
            },
        },
    )

    return result
