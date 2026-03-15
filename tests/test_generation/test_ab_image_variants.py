"""Tests for single-variable A/B image variant generation (P3-03).

Validates image variant generation, single-element isolation, composite
scoring comparison, coherence lift, and visual pattern tracking.
"""

from __future__ import annotations

from pathlib import Path

from generate.ab_image_variants import (
    IMAGE_VARIANT_ELEMENTS,
    ImageABVariant,
    ImageVariantComparison,
    compare_image_variants,
    generate_image_variants,
    get_visual_alternatives,
    get_visual_patterns,
    track_image_variant_win,
)


_CONTROL_SPEC = {
    "scene_description": "Student studying at desk with laptop",
    "composition": "centered",
    "color_palette": "warm",
    "subject_framing": "close-up",
    "aspect_ratio": "1:1",
}

_COPY = {
    "headline": "Is Your Child Ready for the SAT?",
    "primary_text": "Varsity Tutors pairs your student with expert tutors.",
}


# --- Variant Generation ---


def test_generate_image_variants_returns_three() -> None:
    """Generates exactly 3 image variants (one per visual element)."""
    variants = generate_image_variants("ad_001", _CONTROL_SPEC, _COPY)
    assert len(variants) == 3


def test_each_variant_changes_exactly_one_element() -> None:
    """Each variant modifies exactly one of composition, color_palette, subject_framing."""
    variants = generate_image_variants("ad_001", _CONTROL_SPEC, _COPY)
    varied = [v.varied_element for v in variants]
    assert set(varied) == set(IMAGE_VARIANT_ELEMENTS)


def test_variant_value_differs_from_original() -> None:
    """Each variant's changed value is different from the control."""
    variants = generate_image_variants("ad_001", _CONTROL_SPEC, _COPY)
    for v in variants:
        assert v.variant_value != v.original_value, (
            f"{v.varied_element}: variant '{v.variant_value}' same as original '{v.original_value}'"
        )


def test_variant_id_naming() -> None:
    """Variant IDs follow naming: composition_variant, color_variant, framing_variant."""
    variants = generate_image_variants("ad_001", _CONTROL_SPEC, _COPY)
    ids = {v.variant_id for v in variants}
    assert "composition_variant" in ids
    assert "color_variant" in ids
    assert "framing_variant" in ids


def test_control_spec_not_mutated() -> None:
    """Generating variants does not mutate the original visual spec."""
    spec = dict(_CONTROL_SPEC)
    generate_image_variants("ad_001", spec, _COPY)
    assert spec == _CONTROL_SPEC


# --- Visual Alternatives ---


def test_visual_alternatives_differ_from_current() -> None:
    """get_visual_alternatives returns a value different from current."""
    for element in IMAGE_VARIANT_ELEMENTS:
        current = _CONTROL_SPEC[element]
        alt = get_visual_alternatives(element, current)
        assert alt != current, f"{element}: alternative '{alt}' same as current '{current}'"


def test_visual_alternatives_are_known_values() -> None:
    """Alternatives come from the predefined set."""
    alt = get_visual_alternatives("composition", "centered")
    assert alt in ("rule-of-thirds", "diagonal", "wide")


# --- Variant Comparison ---


def test_compare_image_variants_identifies_winner() -> None:
    """compare_image_variants picks variant with highest composite score."""
    control = ImageABVariant(
        ad_id="ad_001", variant_id="control", varied_element=None,
        original_value="", variant_value="", visual_spec=_CONTROL_SPEC,
    )
    variants = [
        ImageABVariant(
            ad_id="ad_001", variant_id="composition_variant",
            varied_element="composition", original_value="centered",
            variant_value="rule-of-thirds", visual_spec={},
        ),
    ]
    attribute_results = {
        "control": {"pass_pct": 0.8},
        "composition_variant": {"pass_pct": 1.0},
    }
    coherence_results = {
        "control": {"avg_score": 7.0},
        "composition_variant": {"avg_score": 8.0},
    }
    comparison = compare_image_variants(control, variants, attribute_results, coherence_results)
    assert isinstance(comparison, ImageVariantComparison)
    assert comparison.winner == "composition_variant"
    assert comparison.winning_element == "composition"


def test_coherence_lift_calculation() -> None:
    """Coherence lift = winner coherence - control coherence."""
    control = ImageABVariant(
        ad_id="ad_001", variant_id="control", varied_element=None,
        original_value="", variant_value="", visual_spec=_CONTROL_SPEC,
    )
    variants = [
        ImageABVariant(
            ad_id="ad_001", variant_id="color_variant",
            varied_element="color_palette", original_value="warm",
            variant_value="cool", visual_spec={},
        ),
    ]
    attribute_results = {
        "control": {"pass_pct": 0.8},
        "color_variant": {"pass_pct": 0.8},
    }
    coherence_results = {
        "control": {"avg_score": 6.0},
        "color_variant": {"avg_score": 7.5},
    }
    comparison = compare_image_variants(control, variants, attribute_results, coherence_results)
    assert abs(comparison.coherence_lift - 1.5) < 0.01


def test_control_wins_when_best() -> None:
    """When control has highest composite, winner is 'control'."""
    control = ImageABVariant(
        ad_id="ad_001", variant_id="control", varied_element=None,
        original_value="", variant_value="", visual_spec=_CONTROL_SPEC,
    )
    variants = [
        ImageABVariant(
            ad_id="ad_001", variant_id="framing_variant",
            varied_element="subject_framing", original_value="close-up",
            variant_value="wide", visual_spec={},
        ),
    ]
    attribute_results = {
        "control": {"pass_pct": 1.0},
        "framing_variant": {"pass_pct": 0.6},
    }
    coherence_results = {
        "control": {"avg_score": 8.0},
        "framing_variant": {"avg_score": 6.0},
    }
    comparison = compare_image_variants(control, variants, attribute_results, coherence_results)
    assert comparison.winner == "control"
    assert comparison.winning_element is None


# --- Visual Pattern Tracking ---


def test_track_image_variant_win_logs_event(tmp_path: Path) -> None:
    """track_image_variant_win writes an ImageVariantWin event to ledger."""
    import json

    ledger_path = str(tmp_path / "ledger.jsonl")
    comparison = ImageVariantComparison(
        ad_id="ad_001",
        control_attributes={"pass_pct": 0.8},
        control_coherence=7.0,
        variant_results={"composition_variant": {"composite": 8.2}},
        winner="composition_variant",
        winning_element="composition",
        coherence_lift=1.0,
    )
    track_image_variant_win(comparison, "parents", ledger_path)

    events = [json.loads(line) for line in Path(ledger_path).read_text().strip().split("\n")]
    win_events = [e for e in events if e["event_type"] == "ImageVariantWin"]
    assert len(win_events) == 1
    assert win_events[0]["outputs"]["winning_element"] == "composition"
    assert win_events[0]["outputs"]["audience"] == "parents"


def test_get_visual_patterns_aggregates(tmp_path: Path) -> None:
    """get_visual_patterns returns win rates per audience per element."""
    from iterate.ledger import log_event

    ledger_path = str(tmp_path / "ledger.jsonl")

    for element, count in [("composition", 3), ("color_palette", 1)]:
        for i in range(count):
            log_event(ledger_path, {
                "event_type": "ImageVariantWin",
                "ad_id": f"ad_{element}_{i}",
                "brief_id": "b001",
                "cycle_number": 1,
                "action": "image-variant-win",
                "inputs": {},
                "outputs": {
                    "winning_element": element,
                    "audience": "students",
                    "coherence_lift": 0.5,
                },
                "scores": {},
                "tokens_consumed": 0,
                "model_used": "",
                "seed": "",
            })

    patterns = get_visual_patterns(ledger_path)
    assert "students" in patterns
    assert abs(patterns["students"]["composition"] - 3 / 4) < 0.01
    assert abs(patterns["students"]["color_palette"] - 1 / 4) < 0.01
