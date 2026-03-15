"""Tests for single-variable A/B copy variant generation (P3-02).

Validates variant generation, single-element isolation, scoring comparison,
lift calculation, and segment pattern tracking.
"""

from __future__ import annotations

from pathlib import Path

from generate.ab_variants import (
    VARIANT_ELEMENTS,
    CopyVariant,
    VariantComparison,
    compare_variants,
    generate_copy_variants,
    get_element_alternatives,
    get_segment_patterns,
    track_variant_win,
)


_CONTROL_COPY = {
    "headline": "Is Your Child Ready for the SAT?",
    "primary_text": (
        "Varsity Tutors pairs your student with expert 1-on-1 tutors "
        "who adapt to how they learn."
    ),
    "description": "Personalized SAT prep that works.",
    "cta_button": "Start Free Practice Test",
    "hook_type": "question",
    "emotional_angle": "aspiration",
    "cta_style": "direct",
}

_EXPANDED_BRIEF = {
    "brief_id": "b001",
    "audience": "parents",
    "campaign_goal": "conversion",
    "product": "SAT prep tutoring",
}


# --- Variant Generation ---


def test_generate_copy_variants_returns_three() -> None:
    """Generates exactly 3 variants (one per element)."""
    variants = generate_copy_variants("ad_001", _EXPANDED_BRIEF, _CONTROL_COPY)
    assert len(variants) == 3


def test_each_variant_changes_exactly_one_element() -> None:
    """Each variant modifies exactly one of hook_type, emotional_angle, cta_style."""
    variants = generate_copy_variants("ad_001", _EXPANDED_BRIEF, _CONTROL_COPY)
    varied = [v.varied_element for v in variants]
    assert set(varied) == set(VARIANT_ELEMENTS)


def test_variant_value_differs_from_original() -> None:
    """Each variant's changed value is different from the control."""
    variants = generate_copy_variants("ad_001", _EXPANDED_BRIEF, _CONTROL_COPY)
    for v in variants:
        assert v.variant_value != v.original_value, (
            f"{v.varied_element}: variant value '{v.variant_value}' "
            f"same as original '{v.original_value}'"
        )


def test_variant_id_naming() -> None:
    """Variant IDs follow consistent naming: hook_variant, emotion_variant, cta_variant."""
    variants = generate_copy_variants("ad_001", _EXPANDED_BRIEF, _CONTROL_COPY)
    ids = {v.variant_id for v in variants}
    assert "hook_variant" in ids
    assert "emotion_variant" in ids
    assert "cta_variant" in ids


def test_control_copy_preserved_in_variants() -> None:
    """Each variant's copy dict has the expected keys."""
    variants = generate_copy_variants("ad_001", _EXPANDED_BRIEF, _CONTROL_COPY)
    for v in variants:
        assert "headline" in v.copy
        assert "primary_text" in v.copy


# --- Element Alternatives ---


def test_element_alternatives_differ_from_current() -> None:
    """get_element_alternatives returns a value different from current."""
    for element in VARIANT_ELEMENTS:
        current = _CONTROL_COPY[element]
        alt = get_element_alternatives(element, current)
        assert alt != current, f"{element}: alternative '{alt}' same as current '{current}'"


def test_element_alternatives_are_known_values() -> None:
    """Alternatives come from the predefined set."""
    alt = get_element_alternatives("hook_type", "question")
    assert alt in ("statistic", "story", "command")


# --- Variant Comparison ---


def test_compare_variants_identifies_winner() -> None:
    """compare_variants picks the variant with highest weighted average."""
    control = CopyVariant(
        ad_id="ad_001", variant_id="control", varied_element=None,
        original_value="", variant_value="", copy=_CONTROL_COPY,
    )
    variants = [
        CopyVariant(
            ad_id="ad_001", variant_id="hook_variant", varied_element="hook_type",
            original_value="question", variant_value="statistic", copy={},
        ),
    ]
    scores = {
        "control": {"aggregate_score": 7.0},
        "hook_variant": {"aggregate_score": 7.8},
    }
    comparison = compare_variants(control, variants, scores)
    assert isinstance(comparison, VariantComparison)
    assert comparison.winner == "hook_variant"
    assert comparison.winning_element == "hook_type"


def test_compare_variants_control_wins() -> None:
    """When control scores highest, winner is 'control' and winning_element is None."""
    control = CopyVariant(
        ad_id="ad_001", variant_id="control", varied_element=None,
        original_value="", variant_value="", copy=_CONTROL_COPY,
    )
    variants = [
        CopyVariant(
            ad_id="ad_001", variant_id="hook_variant", varied_element="hook_type",
            original_value="question", variant_value="statistic", copy={},
        ),
    ]
    scores = {
        "control": {"aggregate_score": 8.0},
        "hook_variant": {"aggregate_score": 7.2},
    }
    comparison = compare_variants(control, variants, scores)
    assert comparison.winner == "control"
    assert comparison.winning_element is None


def test_lift_calculation() -> None:
    """Lift = winner score - control score."""
    control = CopyVariant(
        ad_id="ad_001", variant_id="control", varied_element=None,
        original_value="", variant_value="", copy=_CONTROL_COPY,
    )
    variants = [
        CopyVariant(
            ad_id="ad_001", variant_id="cta_variant", varied_element="cta_style",
            original_value="direct", variant_value="scarcity", copy={},
        ),
    ]
    scores = {
        "control": {"aggregate_score": 7.0},
        "cta_variant": {"aggregate_score": 7.5},
    }
    comparison = compare_variants(control, variants, scores)
    assert abs(comparison.lift - 0.5) < 0.01


# --- Segment Pattern Tracking ---


def test_track_variant_win_logs_event(tmp_path: Path) -> None:
    """track_variant_win writes a VariantWin event to the ledger."""
    ledger_path = str(tmp_path / "ledger.jsonl")
    comparison = VariantComparison(
        ad_id="ad_001",
        control_scores={"aggregate_score": 7.0},
        variant_scores={"hook_variant": {"aggregate_score": 7.8}},
        winner="hook_variant",
        winning_element="hook_type",
        lift=0.8,
    )
    track_variant_win(comparison, "parents", ledger_path)

    import json
    events = [json.loads(line) for line in Path(ledger_path).read_text().strip().split("\n")]
    win_events = [e for e in events if e["event_type"] == "VariantWin"]
    assert len(win_events) == 1
    assert win_events[0]["outputs"]["winning_element"] == "hook_type"
    assert win_events[0]["outputs"]["audience"] == "parents"


def test_get_segment_patterns_aggregates(tmp_path: Path) -> None:
    """get_segment_patterns returns win rates per audience per element."""
    ledger_path = str(tmp_path / "ledger.jsonl")
    from iterate.ledger import log_event

    # 3 wins for parents: 2 hook, 1 cta
    for element, count in [("hook_type", 2), ("cta_style", 1)]:
        for i in range(count):
            log_event(ledger_path, {
                "event_type": "VariantWin",
                "ad_id": f"ad_{element}_{i}",
                "brief_id": "b001",
                "cycle_number": 1,
                "action": "variant-win",
                "inputs": {},
                "outputs": {
                    "winning_element": element,
                    "audience": "parents",
                    "lift": 0.5,
                },
                "scores": {},
                "tokens_consumed": 0,
                "model_used": "",
                "seed": "",
            })

    patterns = get_segment_patterns(ledger_path)
    assert "parents" in patterns
    parent_patterns = patterns["parents"]
    # 2/3 = 0.667 for hook_type
    assert abs(parent_patterns["hook_type"] - 2 / 3) < 0.01
    assert abs(parent_patterns["cta_style"] - 1 / 3) < 0.01
