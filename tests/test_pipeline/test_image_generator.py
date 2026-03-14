"""Tests for visual spec extraction and image generation (P1-14)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from generate.visual_spec import (
    VisualSpec,
    build_image_prompt,
    extract_visual_spec,
)
from generate.image_generator import (
    ImageVariant,
    generate_extra_ratios,
    generate_variants,
)

VARIANT_TYPES = ("anchor", "tone_shift", "composition_shift")


def _mock_visual_spec() -> VisualSpec:
    """Build a sample VisualSpec for testing."""
    return VisualSpec(
        ad_id="ad_001",
        brief_id="b001",
        subject="High school student studying at desk with laptop, focused expression",
        setting="Bright home office, natural window lighting, afternoon",
        color_palette=["#00838F", "#1A237E", "#FFFFFF", "#FFC107"],
        composition="Rule of thirds, student centered, shallow depth of field",
        campaign_goal_cue="Action-oriented: student actively working toward improvement",
        text_overlay="",
        aspect_ratio="1:1",
        negative_prompt="No competitor branding, no AI artifacts, no text in image",
    )


# --- Visual Spec Tests ---


def test_visual_spec_has_all_fields() -> None:
    """VisualSpec contains all required fields."""
    spec = _mock_visual_spec()
    assert spec.subject
    assert spec.setting
    assert spec.color_palette
    assert spec.composition
    assert spec.campaign_goal_cue
    assert spec.aspect_ratio == "1:1"
    assert spec.negative_prompt
    assert spec.ad_id == "ad_001"


@patch("generate.visual_spec._call_gemini_for_spec")
def test_extract_visual_spec_returns_spec(mock_call: MagicMock) -> None:
    """extract_visual_spec returns a VisualSpec from an expanded brief."""
    mock_call.return_value = {
        "subject": "Student with tutor, collaborative posture",
        "setting": "Modern library, warm ambient lighting",
        "color_palette": ["#00838F", "#1A237E", "#FFFFFF"],
        "composition": "Two-shot, eye-level, balanced",
        "campaign_goal_cue": "Aspirational: student achieving goals",
        "text_overlay": "",
    }
    brief = {
        "brief_id": "b001",
        "audience": "parents",
        "campaign_goal": "conversion",
        "product": "SAT prep",
    }
    spec = extract_visual_spec(brief, campaign_goal="conversion", audience="parents", ad_id="ad_001")
    assert isinstance(spec, VisualSpec)
    assert spec.subject
    assert spec.ad_id == "ad_001"


# --- build_image_prompt Tests ---


def test_build_image_prompt_anchor() -> None:
    """Anchor prompt is a straight interpretation of the spec."""
    spec = _mock_visual_spec()
    prompt = build_image_prompt(spec, "anchor")
    assert "student" in prompt.lower()
    assert len(prompt) > 50


def test_build_image_prompt_tone_shift() -> None:
    """Tone shift prompt adjusts emotional register."""
    spec = _mock_visual_spec()
    prompt = build_image_prompt(spec, "tone_shift")
    assert "warm" in prompt.lower() or "soft" in prompt.lower() or "tone" in prompt.lower()


def test_build_image_prompt_composition_shift() -> None:
    """Composition shift prompt changes framing."""
    spec = _mock_visual_spec()
    prompt = build_image_prompt(spec, "composition_shift")
    assert "close" in prompt.lower() or "wide" in prompt.lower() or "framing" in prompt.lower()


def test_build_image_prompt_always_includes_negative() -> None:
    """All variant prompts include the negative prompt."""
    spec = _mock_visual_spec()
    for variant_type in VARIANT_TYPES:
        prompt = build_image_prompt(spec, variant_type)
        assert "no competitor" in prompt.lower() or "negative" in prompt.lower()


def test_build_image_prompt_different_for_each_variant() -> None:
    """Each variant type produces a different prompt."""
    spec = _mock_visual_spec()
    prompts = {vt: build_image_prompt(spec, vt) for vt in VARIANT_TYPES}
    assert len(set(prompts.values())) == 3


# --- generate_variants Tests ---


@patch("generate.image_generator._call_image_api")
def test_generate_variants_produces_three(mock_api: MagicMock) -> None:
    """generate_variants produces exactly 3 variants with correct types."""
    mock_api.return_value = "/tmp/test_image.png"
    spec = _mock_visual_spec()

    variants = generate_variants(spec, ad_id="ad_001", seed=42, output_dir="/tmp/images")
    assert len(variants) == 3
    types = {v.variant_type for v in variants}
    assert types == {"anchor", "tone_shift", "composition_shift"}


@patch("generate.image_generator._call_image_api")
def test_variant_seeds_are_deterministic(mock_api: MagicMock) -> None:
    """Variant seeds are derived from base seed deterministically."""
    mock_api.return_value = "/tmp/test_image.png"
    spec = _mock_visual_spec()

    v1 = generate_variants(spec, ad_id="ad_001", seed=42, output_dir="/tmp/images")
    v2 = generate_variants(spec, ad_id="ad_001", seed=42, output_dir="/tmp/images")

    for a, b in zip(v1, v2):
        assert a.seed == b.seed


@patch("generate.image_generator._call_image_api")
def test_default_aspect_ratio_is_1x1(mock_api: MagicMock) -> None:
    """Default aspect ratio for all variants is 1:1."""
    mock_api.return_value = "/tmp/test_image.png"
    spec = _mock_visual_spec()

    variants = generate_variants(spec, ad_id="ad_001", seed=42, output_dir="/tmp/images")
    for v in variants:
        assert v.aspect_ratio == "1:1"


# --- generate_extra_ratios Tests ---


@patch("generate.image_generator._call_image_api")
def test_generate_extra_ratios_produces_two(mock_api: MagicMock) -> None:
    """Extra ratios generates 4:5 and 9:16 variants."""
    mock_api.return_value = "/tmp/test_image.png"
    winner = ImageVariant(
        ad_id="ad_001",
        variant_type="anchor",
        image_path="/tmp/original.png",
        aspect_ratio="1:1",
        visual_spec_hash="abc123",
        prompt_used="test prompt",
        seed=42,
    )

    extras = generate_extra_ratios(winner, ratios=["4:5", "9:16"], output_dir="/tmp/images")
    assert len(extras) == 2
    ratios = {e.aspect_ratio for e in extras}
    assert ratios == {"4:5", "9:16"}
