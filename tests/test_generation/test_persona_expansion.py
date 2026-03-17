# PB-04: Persona-aware brief expansion tests
"""Tests for persona injection, hook loading, offer context, and messaging rules."""

import json
from unittest.mock import patch

from generate.brief_expansion import (
    ExpandedBrief,
    _build_expansion_prompt,
    _gather_brand_facts_for_brief,
    _get_messaging_rules,
    _get_offer_context,
    _get_persona_profile,
    _load_brand_knowledge,
    _resolve_persona,
    expand_brief,
)


def _mock_gemini_response() -> str:
    """Return a valid JSON response mimicking Gemini output."""
    return json.dumps({
        "audience_profile": {"pain_points": ["test anxiety"], "emotional_drivers": ["fear"], "tone": "reassuring"},
        "brand_facts": [{"claim": "1-on-1 SAT tutoring", "source": "supplementary"}],
        "competitive_context_summary": "Differentiate via 1:1 format and digital SAT training",
        "emotional_angles": ["scholarship fear", "recruiting urgency"],
        "value_propositions": ["10X vs self-study", "100pts/month"],
        "key_differentiators": ["digital SAT interface", "tutor matching"],
        "constraints": ["no fake urgency", "use your child not your student"],
    })


# --- Persona resolution ---


def test_resolve_persona_explicit():
    assert _resolve_persona("athlete_recruit", "parents") == "athlete_recruit"


def test_resolve_persona_auto_defaults_to_suburban():
    assert _resolve_persona("auto", "parents") == "suburban_optimizer"
    assert _resolve_persona(None, "parents") == "suburban_optimizer"


def test_resolve_persona_student_returns_none():
    assert _resolve_persona(None, "students") is None


# --- Persona profile loading ---


def test_persona_profile_loaded():
    kb = _load_brand_knowledge()
    profile = _get_persona_profile(kb, "athlete_recruit")
    assert profile is not None
    assert "psychology" in profile
    assert "trigger" in profile
    assert "key_needs" in profile
    assert "recruiting" in profile["trigger"].lower() or "scholarship" in profile["trigger"].lower()


# --- Offer context ---


def test_offer_context_present():
    kb = _load_brand_knowledge()
    offer = _get_offer_context(kb)
    assert offer is not None
    assert "model" in offer
    assert "membership" in offer["model"].lower()


# --- Messaging rules ---


def test_messaging_rules_loaded():
    kb = _load_brand_knowledge()
    rules = _get_messaging_rules(kb)
    assert rules is not None
    assert "dos" in rules
    assert "donts" in rules
    dos_text = " ".join(d["rule"] for d in rules["dos"])
    assert "your child" in dos_text.lower()


# --- Prompt building ---


def test_prompt_includes_persona_context():
    kb = _load_brand_knowledge()
    brief = {"audience": "parents", "campaign_goal": "conversion"}
    brand_facts = _gather_brand_facts_for_brief(brief, kb)
    persona_profile = _get_persona_profile(kb, "athlete_recruit")
    hooks = [{"hook_text": "The coach wants him.", "hook_id": "h1"}]
    offer = _get_offer_context(kb)
    messaging = _get_messaging_rules(kb)

    prompt = _build_expansion_prompt(
        brief, brand_facts, "competitive context here",
        persona_profile=persona_profile, hooks=hooks,
        offer=offer, messaging=messaging,
    )

    assert "athlete" in prompt.lower() or "recruit" in prompt.lower()
    assert "The coach wants him." in prompt
    assert "membership" in prompt.lower()
    assert "your child" in prompt.lower()


def test_prompt_without_persona_has_no_persona_section():
    kb = _load_brand_knowledge()
    brief = {"audience": "parents", "campaign_goal": "awareness"}
    brand_facts = _gather_brand_facts_for_brief(brief, kb)

    prompt = _build_expansion_prompt(brief, brand_facts, "context")

    assert "Target Persona" not in prompt


# --- Full expand_brief with mocked Gemini ---


def test_expand_brief_with_persona_sets_fields():
    brief = {"audience": "parents", "campaign_goal": "conversion", "brief_id": "test_001"}

    with (
        patch("generate.brief_expansion._call_gemini", return_value=_mock_gemini_response()),
        patch("generate.brief_expansion.log_event"),
    ):
        result = expand_brief(brief, persona="athlete_recruit")

    assert isinstance(result, ExpandedBrief)
    assert result.persona == "athlete_recruit"
    assert len(result.suggested_hooks) >= 1
    assert result.offer_context is not None
    assert result.messaging_rules is not None


def test_expand_brief_awareness_has_no_offer():
    brief = {"audience": "parents", "campaign_goal": "awareness", "brief_id": "test_002"}

    with (
        patch("generate.brief_expansion._call_gemini", return_value=_mock_gemini_response()),
        patch("generate.brief_expansion.log_event"),
    ):
        result = expand_brief(brief, persona="suburban_optimizer")

    assert result.persona == "suburban_optimizer"
    assert result.offer_context is None


def test_expand_brief_auto_persona():
    brief = {"audience": "parents", "campaign_goal": "conversion", "brief_id": "test_003"}

    with (
        patch("generate.brief_expansion._call_gemini", return_value=_mock_gemini_response()),
        patch("generate.brief_expansion.log_event"),
    ):
        result = expand_brief(brief, persona=None)

    assert result.persona == "suburban_optimizer"  # default for parents


def test_expand_brief_messaging_rules_in_result():
    brief = {"audience": "parents", "campaign_goal": "awareness", "brief_id": "test_004"}

    with (
        patch("generate.brief_expansion._call_gemini", return_value=_mock_gemini_response()),
        patch("generate.brief_expansion.log_event"),
    ):
        result = expand_brief(brief, persona="burned_returner")

    assert result.messaging_rules is not None
    assert "dos" in result.messaging_rules
    assert "donts" in result.messaging_rules
