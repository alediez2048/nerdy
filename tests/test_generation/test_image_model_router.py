"""PH-06 image model router tests.

Pure-function tests — no API calls, no mocks. Cover:
- Anchor variants get Nano Banana Pro (the expensive hero model).
- Sibling variants (tone_shift, composition_shift, anything else) get
  Nano Banana 2 (the cheap model).
- Budget below $2 forces NB2 even for anchors.
- Legacy ``variant_type`` strings work alongside the :class:`VariantRole` enum.
- ``predicted_cost_usd`` matches the per-model rate in cost_reporter.
- The legacy ``select_image_model`` shim still works and returns the
  same model identifier strings as before.
"""

from __future__ import annotations

import pytest

from generate.image_model_router import (
    ModelChoice,
    VariantRole,
    choose_model,
)


# --- default routing -------------------------------------------------------


def test_anchor_gets_nano_banana_pro() -> None:
    choice = choose_model(VariantRole.ANCHOR)
    assert choice.model_name == "nano-banana-pro-preview"
    assert choice.predicted_cost_usd == pytest.approx(0.13)
    assert "anchor" in choice.rationale.lower()


def test_sibling_gets_nano_banana_2() -> None:
    choice = choose_model(VariantRole.SIBLING)
    assert choice.model_name == "gemini-2.5-flash-image"
    assert choice.predicted_cost_usd == pytest.approx(0.035)
    assert "sibling" in choice.rationale.lower()


# --- legacy variant_type strings -------------------------------------------


def test_string_anchor_routes_to_pro() -> None:
    assert choose_model("anchor").model_name == "nano-banana-pro-preview"


def test_string_tone_shift_is_sibling() -> None:
    assert choose_model("tone_shift").model_name == "gemini-2.5-flash-image"


def test_string_composition_shift_is_sibling() -> None:
    assert choose_model("composition_shift").model_name == "gemini-2.5-flash-image"


def test_unknown_string_falls_back_to_sibling() -> None:
    """Anything that isn't ``'anchor'`` is treated as a sibling — defensive default."""
    assert choose_model("future_variant_type").model_name == "gemini-2.5-flash-image"


# --- budget override --------------------------------------------------------


def test_budget_below_2_forces_nb2_for_anchor() -> None:
    choice = choose_model(VariantRole.ANCHOR, budget_remaining_usd=1.50)
    assert choice.model_name == "gemini-2.5-flash-image"
    assert "budget override" in choice.rationale.lower()
    assert "1.50" in choice.rationale


def test_budget_below_2_forces_nb2_for_sibling() -> None:
    choice = choose_model(VariantRole.SIBLING, budget_remaining_usd=0.50)
    assert choice.model_name == "gemini-2.5-flash-image"


def test_budget_at_or_above_2_uses_default_routing() -> None:
    """Threshold is strict (``<``), so $2.00 exactly still uses Pro for anchor."""
    choice = choose_model(VariantRole.ANCHOR, budget_remaining_usd=2.00)
    assert choice.model_name == "nano-banana-pro-preview"


def test_no_budget_uses_default_routing() -> None:
    """``budget_remaining_usd=None`` should NOT trigger the override."""
    choice = choose_model(VariantRole.ANCHOR, budget_remaining_usd=None)
    assert choice.model_name == "nano-banana-pro-preview"


# --- predicted_cost_usd is always populated --------------------------------


def test_predicted_cost_present_on_every_choice() -> None:
    for role in (VariantRole.ANCHOR, VariantRole.SIBLING):
        for budget in (None, 0.5, 5.0):
            choice = choose_model(role, budget_remaining_usd=budget)
            assert isinstance(choice, ModelChoice)
            assert choice.predicted_cost_usd > 0


# --- legacy select_image_model shim ----------------------------------------


def test_legacy_select_image_model_anchor_returns_pro() -> None:
    from generate.image_generator import select_image_model

    assert select_image_model("anchor") == "nano-banana-pro-preview"


def test_legacy_select_image_model_sibling_returns_nb2() -> None:
    from generate.image_generator import select_image_model

    assert select_image_model("tone_shift") == "gemini-2.5-flash-image"


def test_legacy_select_image_model_budget_override() -> None:
    from generate.image_generator import select_image_model

    assert select_image_model("anchor", budget_remaining=1.0) == "gemini-2.5-flash-image"


# --- persona parameter is accepted but currently inert ---------------------


def test_persona_does_not_affect_routing_today() -> None:
    """Reserved for future per-persona routing — currently has no effect."""
    no_persona = choose_model(VariantRole.ANCHOR)
    with_persona = choose_model(VariantRole.ANCHOR, persona="athlete_recruit")
    assert no_persona.model_name == with_persona.model_name
