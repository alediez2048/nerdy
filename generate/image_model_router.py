"""Image model router — PH-06.

Pure-function routing for the image generation tier. Two things the
router decides:

1. Which model to call (Nano Banana Pro for hero variants, Nano Banana 2
   for siblings; budget override forces NB2 across the board).
2. The predicted USD cost of that call, surfaced *before* the spend so
   future budget gates can decide to skip without round-tripping the API.

The legacy ``generate.image_generator.select_image_model`` now delegates
here so older callers keep working without changes. New callers should
prefer ``choose_model(...)`` directly to get the predicted cost.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

# Per-call image generation rates ($/call). Kept in sync with the values
# in evaluate.cost_reporter.MODEL_COST_RATES — when those change, update
# here too. (A future ticket may unify both into config.yaml.)
_RATE_USD_PER_CALL: dict[str, float] = {
    "nano-banana-pro-preview": 0.13,
    "gemini-2.5-flash-image": 0.035,
}

# Budget below which the router forces NB2 for every variant, even anchors.
_BUDGET_OVERRIDE_THRESHOLD_USD = 2.0


class VariantRole(str, Enum):
    """Why we're generating this image — determines the default model.

    ``ANCHOR`` is the hero variant for an ad — gets the expensive model.
    ``SIBLING`` covers ``tone_shift``, ``composition_shift``, and
    additional aspect-ratio renderings — gets the cheap model.
    """

    ANCHOR = "anchor"
    SIBLING = "sibling"


# Translate the literal ``variant_type`` strings used elsewhere in the
# codebase into the router's enum. ``anchor`` maps 1:1, everything else
# is a sibling.
def _variant_role_from_type(variant_type: str) -> VariantRole:
    return VariantRole.ANCHOR if variant_type == "anchor" else VariantRole.SIBLING


@dataclass(frozen=True)
class ModelChoice:
    """Routing decision for one image generation call.

    Fields:
        model_name: Provider-specific model identifier (e.g.
            ``"nano-banana-pro-preview"`` or ``"gemini-2.5-flash-image"``).
        predicted_cost_usd: USD per call this model bills at. Use this
            for budget gating BEFORE the API call.
        rationale: Human-readable explanation, useful for logs and the
            forthcoming budget gate.
    """

    model_name: str
    predicted_cost_usd: float
    rationale: str


def choose_model(
    role: VariantRole | str,
    *,
    budget_remaining_usd: float | None = None,
    persona: str | None = None,  # noqa: ARG001  -- reserved for future per-persona routing
) -> ModelChoice:
    """Pick a model for one image generation call.

    ``role`` accepts the :class:`VariantRole` enum or one of the legacy
    string ``variant_type`` values (``"anchor"``, ``"tone_shift"``,
    ``"composition_shift"``). Anything other than ``"anchor"`` is
    treated as a sibling.

    ``budget_remaining_usd`` triggers the override path: when below
    :data:`_BUDGET_OVERRIDE_THRESHOLD_USD`, all variants fall back to
    NB2. Pass ``None`` (the default) to disable budget routing.

    ``persona`` is accepted for forward compatibility — the router
    does not branch on it today, but the parameter is reserved so
    per-persona routing can land without a signature change.
    """
    if isinstance(role, str):
        role = _variant_role_from_type(role)

    if (
        budget_remaining_usd is not None
        and budget_remaining_usd < _BUDGET_OVERRIDE_THRESHOLD_USD
    ):
        model = "gemini-2.5-flash-image"
        return ModelChoice(
            model_name=model,
            predicted_cost_usd=_RATE_USD_PER_CALL[model],
            rationale=(
                f"budget override: ${budget_remaining_usd:.2f} below "
                f"${_BUDGET_OVERRIDE_THRESHOLD_USD:.2f} threshold — using NB2"
            ),
        )

    if role is VariantRole.ANCHOR:
        model = "nano-banana-pro-preview"
        return ModelChoice(
            model_name=model,
            predicted_cost_usd=_RATE_USD_PER_CALL[model],
            rationale="anchor variant — using Nano Banana Pro for hero quality",
        )

    model = "gemini-2.5-flash-image"
    return ModelChoice(
        model_name=model,
        predicted_cost_usd=_RATE_USD_PER_CALL[model],
        rationale="sibling variant — using NB2 for cost-efficient diversity",
    )
