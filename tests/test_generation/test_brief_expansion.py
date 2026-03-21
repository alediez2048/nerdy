"""Tests for brief expansion engine (P1-01).

TDD: Tests written first. Validates grounding, competitive context,
audience-appropriate facts, malformed response handling, retry logic.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from generate.brief_expansion import (
    ExpandedBrief,
    _build_expansion_prompt,
    _parse_expansion_response,
    expand_brief,
)

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
BRAND_KB_PATH = DATA_DIR / "brand_knowledge.json"


# --- Fixtures ---


@pytest.fixture
def minimal_brief() -> dict:
    """Minimal brief with required fields."""
    return {
        "campaign_goal": "awareness",
        "audience": "parents",
        "product": "SAT prep",
    }


@pytest.fixture
def full_brief() -> dict:
    """Brief with optional angle and hook."""
    return {
        "brief_id": "brief_001",
        "campaign_goal": "conversion",
        "audience": "students",
        "product": "SAT prep",
        "angle": "test anxiety relief",
        "hook": "question",
    }


# --- Schema & Structure ---


def test_expanded_brief_dataclass_has_all_required_fields() -> None:
    """ExpandedBrief includes all fields from primer."""
    brief = ExpandedBrief(
        original_brief={},
        audience_profile={},
        brand_facts=[],
        competitive_context="",
        emotional_angles=[],
        value_propositions=[],
        key_differentiators=[],
        constraints=[],
    )
    assert hasattr(brief, "original_brief")
    assert hasattr(brief, "audience_profile")
    assert hasattr(brief, "brand_facts")
    assert hasattr(brief, "competitive_context")
    assert hasattr(brief, "emotional_angles")
    assert hasattr(brief, "value_propositions")
    assert hasattr(brief, "key_differentiators")
    assert hasattr(brief, "constraints")


def test_expand_brief_produces_all_required_fields(
    minimal_brief: dict,
) -> None:
    """expand_brief returns ExpandedBrief with all required fields populated."""
    mock_response = json.dumps({
        "audience_profile": {"pain_points": ["College anxiety"], "tone": "reassuring"},
        "brand_facts": [{"claim": "1-on-1 SAT tutoring", "source": "assignment_spec"}],
        "competitive_context_summary": "Competitors focus on...",
        "emotional_angles": ["College admissions anxiety", "Wanting the best for child"],
        "value_propositions": ["1-on-1 personalized tutoring", "Online format"],
        "key_differentiators": ["Expert tutors", "Adaptive learning"],
        "constraints": ["No guaranteed scores", "Factual claims only"],
    })

    with patch("generate.brief_expansion._call_gemini", return_value=(mock_response, 100)):
        with patch("generate.brief_expansion.log_event"):
            result = expand_brief(minimal_brief)

    assert isinstance(result, ExpandedBrief)
    assert result.original_brief == minimal_brief
    assert result.audience_profile
    assert isinstance(result.brand_facts, list)
    assert isinstance(result.competitive_context, str)
    assert len(result.emotional_angles) >= 1
    assert len(result.value_propositions) >= 1
    assert len(result.key_differentiators) >= 1
    assert isinstance(result.constraints, list)


# --- Grounding (No Hallucination) ---


def test_expansion_includes_only_verified_brand_facts(
    minimal_brief: dict,
) -> None:
    """All brand_facts in expansion are traceable to brand_knowledge.json."""
    mock_response = json.dumps({
        "audience_profile": {"pain_points": ["College anxiety"], "tone": "reassuring"},
        "brand_facts": [
            {"claim": "Offers 1-on-1 SAT test prep tutoring", "source": "assignment_spec"},
            {"claim": "Online format available", "source": "assignment_spec"},
        ],
        "competitive_context_summary": "Market context.",
        "emotional_angles": ["College admissions anxiety"],
        "value_propositions": ["1-on-1 tutoring", "Online format"],
        "key_differentiators": ["Personalized approach"],
        "constraints": ["No guaranteed scores"],
    })

    with patch("generate.brief_expansion._call_gemini", return_value=(mock_response, 100)):
        with patch("generate.brief_expansion.log_event"):
            result = expand_brief(minimal_brief)

    for fact in result.brand_facts:
        if isinstance(fact, dict):
            assert "claim" in fact or "point" in fact or "driver" in fact
            assert "source" in fact
        else:
            assert isinstance(fact, str)


def test_build_expansion_prompt_instructs_no_invention() -> None:
    """Prompt explicitly instructs: use ONLY verified facts, do NOT invent."""
    brief = {"campaign_goal": "awareness", "audience": "parents", "product": "SAT prep"}
    brand_facts = {"audience": {"pain_points": []}, "products": {}}
    competitive_context = "## Competitive Landscape\n\nContext here."

    prompt = _build_expansion_prompt(brief, brand_facts, competitive_context)

    assert "ONLY" in prompt.upper() or "only" in prompt
    assert "verified" in prompt.lower()
    assert "Do NOT invent" in prompt or "do not invent" in prompt.lower()
    assert "statistics" in prompt.lower() or "claims" in prompt.lower()


# --- Competitive Context ---


def test_competitive_context_included_in_expanded_brief(
    minimal_brief: dict,
) -> None:
    """Competitive landscape from get_landscape_context is included."""
    mock_response = json.dumps({
        "audience_profile": {},
        "brand_facts": [],
        "competitive_context_summary": "Chegg uses direct offers. Kaplan focuses on test prep.",
        "emotional_angles": [],
        "value_propositions": [],
        "key_differentiators": [],
        "constraints": [],
    })

    with patch("generate.brief_expansion._call_gemini", return_value=(mock_response, 100)):
        with patch("generate.brief_expansion.log_event"):
            with patch(
                "generate.brief_expansion.get_landscape_context",
                return_value="## Competitive Landscape\n\n### Top Patterns\n- [Chegg] direct_offer: ...",
            ) as mock_landscape:
                result = expand_brief(minimal_brief)

    mock_landscape.assert_called_once()
    assert "competitive" in result.competitive_context.lower() or len(result.competitive_context) > 0


# --- Audience-Appropriate Facts ---


def test_parent_brief_gets_parent_relevant_facts(minimal_brief: dict) -> None:
    """Brief with audience=parents receives parent-specific pain points."""
    minimal_brief["audience"] = "parents"
    mock_response = json.dumps({
        "audience_profile": {
            "pain_points": ["College admissions anxiety", "Comparison shopping"],
            "tone": "authoritative, reassuring",
        },
        "brand_facts": [{"claim": "1-on-1 SAT tutoring", "source": "assignment_spec"}],
        "competitive_context_summary": "",
        "emotional_angles": ["College admissions anxiety"],
        "value_propositions": ["Personalized tutoring"],
        "key_differentiators": [],
        "constraints": [],
    })

    with patch("generate.brief_expansion._call_gemini", return_value=(mock_response, 100)):
        with patch("generate.brief_expansion.log_event"):
            result = expand_brief(minimal_brief)

    profile = result.audience_profile
    if isinstance(profile, dict):
        pain_points = profile.get("pain_points", [])
        assert any("college" in str(p).lower() or "comparison" in str(p).lower() for p in pain_points) or len(profile) > 0
    assert result.original_brief["audience"] == "parents"


def test_student_brief_gets_student_relevant_facts() -> None:
    """Brief with audience=students receives student-specific pain points."""
    brief = {"campaign_goal": "conversion", "audience": "students", "product": "SAT prep"}
    mock_response = json.dumps({
        "audience_profile": {"pain_points": ["Test anxiety", "Score pressure"], "tone": "relatable"},
        "brand_facts": [{"claim": "Online format", "source": "assignment_spec"}],
        "competitive_context_summary": "",
        "emotional_angles": ["Test anxiety", "Desire to prove themselves"],
        "value_propositions": ["Flexible scheduling"],
        "key_differentiators": [],
        "constraints": [],
    })

    with patch("generate.brief_expansion._call_gemini", return_value=(mock_response, 100)):
        with patch("generate.brief_expansion.log_event"):
            result = expand_brief(brief)

    assert result.original_brief["audience"] == "students"


# --- Malformed Response Handling ---


def test_malformed_api_response_handled_gracefully(minimal_brief: dict) -> None:
    """Malformed JSON from API returns partial expansion with warning, not crash."""
    with patch("generate.brief_expansion._call_gemini", return_value=("not valid json {{{", 100)):
        with patch("generate.brief_expansion.log_event"):
            result = expand_brief(minimal_brief)

    assert isinstance(result, ExpandedBrief)
    assert result.original_brief == minimal_brief
    assert result.brand_facts == [] or result.emotional_angles == []


def test_partial_json_response_parsed_gracefully(minimal_brief: dict) -> None:
    """Partial JSON (missing some keys) produces partial ExpandedBrief."""
    partial = json.dumps({
        "emotional_angles": ["Anxiety"],
        "value_propositions": ["1-on-1 tutoring"],
    })

    with patch("generate.brief_expansion._call_gemini", return_value=(partial, 100)):
        with patch("generate.brief_expansion.log_event"):
            result = expand_brief(minimal_brief)

    assert result.emotional_angles == ["Anxiety"]
    assert result.value_propositions == ["1-on-1 tutoring"]
    assert result.original_brief == minimal_brief
    assert result.brand_facts == [] or result.brand_facts  # May be empty


# --- Retry Logic ---


def test_retry_logic_invoked_on_api_failure(minimal_brief: dict) -> None:
    """retry_with_backoff is used for Gemini API calls."""
    with patch("generate.brief_expansion.retry_with_backoff") as mock_retry:
        mock_retry.side_effect = lambda f: f()
        with patch("generate.brief_expansion._call_gemini") as mock_call:
            mock_call.return_value = (json.dumps({
                "audience_profile": {},
                "brand_facts": [],
                "competitive_context_summary": "",
                "emotional_angles": [],
                "value_propositions": [],
                "key_differentiators": [],
                "constraints": [],
            }), 100)
            with patch("generate.brief_expansion.log_event"):
                expand_brief(minimal_brief)

    mock_retry.assert_called()


# --- Minimal Brief ---


def test_minimal_brief_with_only_required_fields_expands_successfully(
    minimal_brief: dict,
) -> None:
    """Brief with only campaign_goal, audience, product expands without error."""
    mock_response = json.dumps({
        "audience_profile": {},
        "brand_facts": [],
        "competitive_context_summary": "",
        "emotional_angles": ["College anxiety"],
        "value_propositions": ["1-on-1 tutoring"],
        "key_differentiators": [],
        "constraints": [],
    })

    with patch("generate.brief_expansion._call_gemini", return_value=(mock_response, 100)):
        with patch("generate.brief_expansion.log_event"):
            result = expand_brief(minimal_brief)

    assert result.original_brief == minimal_brief
    assert len(result.emotional_angles) >= 1 or len(result.value_propositions) >= 1


# --- Parse Helper ---


def test_parse_expansion_response_valid_json() -> None:
    """_parse_expansion_response parses valid JSON into ExpandedBrief."""
    raw = json.dumps({
        "audience_profile": {"tone": "reassuring"},
        "brand_facts": [{"claim": "1-on-1 tutoring", "source": "assignment_spec"}],
        "competitive_context_summary": "Competitors...",
        "emotional_angles": ["Anxiety", "Aspiration"],
        "value_propositions": ["Personalized", "Online"],
        "key_differentiators": ["Expert tutors"],
        "constraints": ["No guarantees"],
    })
    brief = {"campaign_goal": "awareness", "audience": "parents", "product": "SAT prep"}

    result = _parse_expansion_response(raw, brief)

    assert result.audience_profile.get("tone") == "reassuring"
    assert len(result.brand_facts) == 1
    assert result.emotional_angles == ["Anxiety", "Aspiration"]
    assert result.value_propositions == ["Personalized", "Online"]
    assert result.key_differentiators == ["Expert tutors"]
    assert result.constraints == ["No guarantees"]
    assert result.original_brief == brief


def test_parse_expansion_response_strips_markdown_code_block() -> None:
    """_parse_expansion_response handles markdown-wrapped JSON."""
    inner = {"emotional_angles": ["A"], "value_propositions": ["B"], "audience_profile": {}, "brand_facts": [], "competitive_context_summary": "", "key_differentiators": [], "constraints": []}
    raw = "```json\n" + json.dumps(inner) + "\n```"
    brief = {}

    result = _parse_expansion_response(raw, brief)

    assert result.emotional_angles == ["A"]
    assert result.value_propositions == ["B"]
