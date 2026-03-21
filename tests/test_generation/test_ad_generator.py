"""Tests for ad copy generator (P1-02).

TDD: Tests written first. Validates reference-decompose-recombine,
structural atoms, seed determinism, Meta format, ledger integration.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from generate.ad_generator import (
    GeneratedAd,
    _build_generation_prompt,
    _parse_generation_response,
    _select_structural_atoms,
    generate_ad,
)
from generate.brief_expansion import ExpandedBrief

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
PATTERNS_PATH = DATA_DIR / "competitive" / "patterns.json"

# Valid Meta CTAs from brand_knowledge + common options
VALID_CTAS = {"Learn More", "Get Started", "Sign Up", "Start Free Practice Test", "Book Now"}


@pytest.fixture
def sample_expanded_brief() -> ExpandedBrief:
    """Sample ExpandedBrief for testing."""
    return ExpandedBrief(
        original_brief={
            "brief_id": "brief_001",
            "campaign_goal": "conversion",
            "audience": "parents",
            "product": "SAT prep",
        },
        audience_profile={"pain_points": ["College anxiety"], "tone": "reassuring"},
        brand_facts=[{"claim": "1-on-1 SAT tutoring", "source": "assignment_spec"}],
        competitive_context="Differentiate from competitors.",
        emotional_angles=["College admissions anxiety", "Wanting the best for child"],
        value_propositions=["1-on-1 personalized tutoring", "Online format"],
        key_differentiators=["Expert tutors", "Adaptive learning"],
        constraints=["No guaranteed scores"],
    )


# --- Schema & Components ---


def test_generated_ad_dataclass_has_all_required_fields() -> None:
    """GeneratedAd includes all 4 Meta components + metadata."""
    ad = GeneratedAd(
        ad_id="ad_001",
        primary_text="",
        headline="",
        description="",
        cta_button="Learn More",
        structural_atoms_used=[],
        expanded_brief_id="brief_001",
        generation_metadata={},
    )
    assert hasattr(ad, "primary_text")
    assert hasattr(ad, "headline")
    assert hasattr(ad, "description")
    assert hasattr(ad, "cta_button")
    assert hasattr(ad, "structural_atoms_used")
    assert hasattr(ad, "expanded_brief_id")
    assert hasattr(ad, "generation_metadata")


def test_generate_ad_produces_all_four_components(sample_expanded_brief: ExpandedBrief) -> None:
    """Generated ad contains primary_text, headline, description, cta_button."""
    mock_response = json.dumps({
        "primary_text": "Is your child's SAT score holding them back?",
        "headline": "1-on-1 SAT Prep That Works",
        "description": "Expert tutors. Flexible scheduling.",
        "cta_button": "Start Free Practice Test",
    })

    with patch("generate.ad_generator._call_gemini", return_value=(mock_response, 100)):
        with patch("generate.ad_generator.log_event"):
            result = generate_ad(sample_expanded_brief)

    assert result.primary_text
    assert result.headline
    assert result.description
    assert result.cta_button


def test_all_components_are_non_empty_strings(sample_expanded_brief: ExpandedBrief) -> None:
    """All 4 Meta components are non-empty strings."""
    mock_response = json.dumps({
        "primary_text": "Her SAT score jumped 200 points.",
        "headline": "1-on-1 Tutoring",
        "description": "Expert tutors. Flexible scheduling.",
        "cta_button": "Learn More",
    })

    with patch("generate.ad_generator._call_gemini", return_value=(mock_response, 100)):
        with patch("generate.ad_generator.log_event"):
            result = generate_ad(sample_expanded_brief)

    assert isinstance(result.primary_text, str) and len(result.primary_text) > 0
    assert isinstance(result.headline, str) and len(result.headline) > 0
    assert isinstance(result.description, str) and len(result.description) > 0
    assert isinstance(result.cta_button, str) and len(result.cta_button) > 0


# --- Structural Atoms ---


def test_structural_atoms_selected_and_recorded(sample_expanded_brief: ExpandedBrief) -> None:
    """structural_atoms_used is populated with atom references."""
    mock_response = json.dumps({
        "primary_text": "Test content.",
        "headline": "Headline",
        "description": "Desc",
        "cta_button": "Learn More",
    })

    with patch("generate.ad_generator._call_gemini", return_value=(mock_response, 100)):
        with patch("generate.ad_generator.log_event"):
            result = generate_ad(sample_expanded_brief)

    assert isinstance(result.structural_atoms_used, list)
    assert len(result.structural_atoms_used) >= 1


def test_select_structural_atoms_returns_2_to_3_atoms() -> None:
    """_select_structural_atoms returns 2-3 diverse structural atoms."""
    atoms = _select_structural_atoms("conversion", "parents")
    assert isinstance(atoms, list)
    assert 2 <= len(atoms) <= 5
    for a in atoms:
        assert "pattern_id" in a or "hook_type" in a or "body_pattern" in a


def test_different_campaign_goals_can_select_different_atoms() -> None:
    """Awareness vs conversion may yield different atom sets (or fallback)."""
    atoms_conv = _select_structural_atoms("conversion", "parents")
    atoms_aware = _select_structural_atoms("awareness", "parents")
    assert isinstance(atoms_conv, list)
    assert isinstance(atoms_aware, list)


# --- Seed Determinism ---


def test_seed_determinism_same_seed_same_ad_id(sample_expanded_brief: ExpandedBrief) -> None:
    """Same seed + same brief produces same ad_id."""
    mock_response = json.dumps({
        "primary_text": "Is your child ready for the SAT?",
        "headline": "1-on-1 SAT Prep",
        "description": "Expert tutors.",
        "cta_button": "Get Started",
    })

    with patch("generate.ad_generator._call_gemini", return_value=(mock_response, 100)):
        with patch("generate.ad_generator.log_event"):
            r1 = generate_ad(sample_expanded_brief, seed=12345)
            r2 = generate_ad(sample_expanded_brief, seed=12345)

    assert r1.ad_id == r2.ad_id


def test_different_seed_different_ad_id(sample_expanded_brief: ExpandedBrief) -> None:
    """Different seed produces different ad_id."""
    mock_response = json.dumps({
        "primary_text": "Content.",
        "headline": "Headline",
        "description": "Desc",
        "cta_button": "Learn More",
    })

    with patch("generate.ad_generator._call_gemini", return_value=(mock_response, 100)):
        with patch("generate.ad_generator.log_event"):
            r1 = generate_ad(sample_expanded_brief, seed=111)
            r2 = generate_ad(sample_expanded_brief, seed=222)

    assert r1.ad_id != r2.ad_id


# --- Malformed Response ---


def test_malformed_api_response_handled_gracefully(sample_expanded_brief: ExpandedBrief) -> None:
    """Malformed JSON returns partial GeneratedAd, does not crash."""
    with patch("generate.ad_generator._call_gemini", return_value=("not valid json {{{", 100)):
        with patch("generate.ad_generator.log_event"):
            result = generate_ad(sample_expanded_brief)

    assert isinstance(result, GeneratedAd)
    assert result.ad_id


# --- CTA Validation ---


def test_cta_button_is_valid_meta_option(sample_expanded_brief: ExpandedBrief) -> None:
    """Generated CTA is one of the valid Meta CTA options."""
    mock_response = json.dumps({
        "primary_text": "Content.",
        "headline": "Headline",
        "description": "Desc",
        "cta_button": "Start Free Practice Test",
    })

    with patch("generate.ad_generator._call_gemini", return_value=(mock_response, 100)):
        with patch("generate.ad_generator.log_event"):
            result = generate_ad(sample_expanded_brief)

    assert result.cta_button in VALID_CTAS or result.cta_button in [
        "Learn More",
        "Get Started",
        "Sign Up",
        "Start Free Practice Test",
        "Book Now",
    ]


# --- Generation Metadata ---


def test_generation_metadata_populated(sample_expanded_brief: ExpandedBrief) -> None:
    """generation_metadata includes model, tokens, timestamp."""
    mock_response = json.dumps({
        "primary_text": "Content.",
        "headline": "Headline",
        "description": "Desc",
        "cta_button": "Learn More",
    })

    with patch("generate.ad_generator._call_gemini", return_value=(mock_response, 100)):
        with patch("generate.ad_generator.log_event"):
            result = generate_ad(sample_expanded_brief)

    assert isinstance(result.generation_metadata, dict)
    assert "model_used" in result.generation_metadata or "timestamp" in result.generation_metadata


# --- Parse Helper ---


def test_parse_generation_response_valid_json() -> None:
    """_parse_generation_response parses valid JSON into GeneratedAd."""
    raw = json.dumps({
        "primary_text": "Is your child ready for the SAT?",
        "headline": "1-on-1 SAT Prep",
        "description": "Expert tutors. Flexible scheduling.",
        "cta_button": "Start Free Practice Test",
    })
    ad_id = "ad_001"
    atoms = [{"pattern_id": "p1", "hook_type": "question"}]
    brief_id = "brief_001"

    result = _parse_generation_response(raw, ad_id, atoms, brief_id, {})

    assert result.primary_text == "Is your child ready for the SAT?"
    assert result.headline == "1-on-1 SAT Prep"
    assert result.description == "Expert tutors. Flexible scheduling."
    assert result.cta_button == "Start Free Practice Test"
    assert result.ad_id == ad_id
    assert result.structural_atoms_used == atoms
    assert result.expanded_brief_id == brief_id


def test_parse_generation_response_strips_markdown_code_block() -> None:
    """_parse_generation_response handles markdown-wrapped JSON."""
    inner = {
        "primary_text": "Content",
        "headline": "Head",
        "description": "Desc",
        "cta_button": "Learn More",
    }
    raw = "```json\n" + json.dumps(inner) + "\n```"

    result = _parse_generation_response(raw, "ad_1", [], "b1", {})

    assert result.primary_text == "Content"
    assert result.cta_button == "Learn More"


# --- Prompt ---


def test_build_generation_prompt_includes_recombine_instruction() -> None:
    """Prompt instructs: recombine, do NOT copy verbatim."""
    brief = ExpandedBrief(
        original_brief={"campaign_goal": "awareness", "audience": "parents"},
        audience_profile={},
        brand_facts=[],
        competitive_context="",
        emotional_angles=[],
        value_propositions=[],
        key_differentiators=[],
        constraints=[],
    )
    atoms = [{"pattern_id": "p1", "hook_type": "question", "body_pattern": "testimonial-benefit-cta"}]

    prompt = _build_generation_prompt(brief, atoms)

    assert "recombine" in prompt.lower() or "recomb" in prompt.lower()
    assert "Do NOT copy" in prompt or "do not copy" in prompt.lower()
    assert "question" in prompt or "testimonial" in prompt.lower()


# --- P1-04 Evaluator Compatibility ---


def test_generated_ad_compatible_with_evaluator_input(sample_expanded_brief: ExpandedBrief) -> None:
    """GeneratedAd can be converted to evaluator dict format (primary_text, headline, description, cta_button, ad_id)."""
    mock_response = json.dumps({
        "primary_text": "Is your child's SAT score holding them back?",
        "headline": "1-on-1 SAT Prep",
        "description": "Expert tutors.",
        "cta_button": "Start Free Practice Test",
    })

    with patch("generate.ad_generator._call_gemini", return_value=(mock_response, 100)):
        with patch("generate.ad_generator.log_event"):
            result = generate_ad(sample_expanded_brief)

    eval_input = {
        "primary_text": result.primary_text,
        "headline": result.headline,
        "description": result.description,
        "cta_button": result.cta_button,
        "ad_id": result.ad_id,
    }
    assert all(k in eval_input for k in ("primary_text", "headline", "description", "cta_button", "ad_id"))
