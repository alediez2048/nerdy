"""Single-variable A/B image variant generation (P3-03, R2-Q6).

Holds copy constant and generates 3 image variants per ad, each changing
exactly ONE visual element (composition, color_palette, or subject_framing).
Tracks winning visual patterns per audience segment.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass

from iterate.ledger import log_event, read_events_filtered

logger = logging.getLogger(__name__)

IMAGE_VARIANT_ELEMENTS = ("composition", "color_palette", "subject_framing")

_ELEMENT_OPTIONS: dict[str, list[str]] = {
    "composition": ["centered", "rule-of-thirds", "diagonal", "wide"],
    "color_palette": ["warm", "cool", "muted", "vibrant"],
    "subject_framing": ["close-up", "medium", "wide", "environmental"],
}

_VARIANT_ID_MAP: dict[str, str] = {
    "composition": "composition_variant",
    "color_palette": "color_variant",
    "subject_framing": "framing_variant",
}


@dataclass
class ImageABVariant:
    """A single image variant with one visual element changed."""

    ad_id: str
    variant_id: str
    varied_element: str | None
    original_value: str
    variant_value: str
    visual_spec: dict
    image_path: str | None = None


@dataclass
class ImageVariantComparison:
    """Result of comparing image variants against control."""

    ad_id: str
    control_attributes: dict
    control_coherence: float
    variant_results: dict[str, dict]
    winner: str
    winning_element: str | None
    coherence_lift: float


def get_visual_alternatives(element: str, current_value: str) -> str:
    """Return a different value for the specified visual element.

    Args:
        element: One of composition, color_palette, subject_framing.
        current_value: The current value to avoid.

    Returns:
        A different value from the element's option set.
    """
    options = _ELEMENT_OPTIONS.get(element, [])
    for option in options:
        if option != current_value:
            return option
    return current_value


def generate_image_variants(
    ad_id: str,
    visual_spec: dict,
    copy: dict,
) -> list[ImageABVariant]:
    """Generate 3 single-variable image variants from a control spec.

    Each variant changes exactly one visual element while preserving
    all other spec elements.

    Args:
        ad_id: The ad identifier.
        visual_spec: The control visual spec dict.
        copy: The ad copy dict (held constant).

    Returns:
        List of 3 ImageABVariant objects.
    """
    variants: list[ImageABVariant] = []

    for element in IMAGE_VARIANT_ELEMENTS:
        current_value = visual_spec.get(element, "")
        alt_value = get_visual_alternatives(element, current_value)
        variant_id = _VARIANT_ID_MAP[element]

        # Build variant spec — same as control but with one element swapped
        variant_spec = dict(visual_spec)
        variant_spec[element] = alt_value

        variants.append(ImageABVariant(
            ad_id=ad_id,
            variant_id=variant_id,
            varied_element=element,
            original_value=current_value,
            variant_value=alt_value,
            visual_spec=variant_spec,
        ))

        logger.info("Generated %s for %s: %s → %s",
                     variant_id, ad_id, current_value, alt_value)

    return variants


def _composite_score(pass_pct: float, coherence_avg: float) -> float:
    """Compute composite score: attribute_pass_pct * 0.4 + coherence_avg * 0.6."""
    return pass_pct * 0.4 + coherence_avg * 0.6


def compare_image_variants(
    control: ImageABVariant,
    variants: list[ImageABVariant],
    attribute_results: dict[str, dict],
    coherence_results: dict[str, dict],
) -> ImageVariantComparison:
    """Compare image variant scores against control using composite scoring.

    Composite = attribute_pass_pct * 0.4 + coherence_avg * 0.6

    Args:
        control: The control ImageABVariant.
        variants: List of variant ImageABVariants.
        attribute_results: Dict mapping variant_id → {"pass_pct": float}.
        coherence_results: Dict mapping variant_id → {"avg_score": float}.

    Returns:
        ImageVariantComparison with winner, winning element, and coherence lift.
    """
    ctrl_pass = attribute_results["control"]["pass_pct"]
    ctrl_coh = coherence_results["control"]["avg_score"]
    ctrl_composite = _composite_score(ctrl_pass, ctrl_coh)

    best_id = "control"
    best_composite = ctrl_composite
    best_element: str | None = None
    best_coherence = ctrl_coh

    variant_result_map: dict[str, dict] = {}
    for v in variants:
        v_pass = attribute_results.get(v.variant_id, {}).get("pass_pct", 0.0)
        v_coh = coherence_results.get(v.variant_id, {}).get("avg_score", 0.0)
        v_composite = _composite_score(v_pass, v_coh)
        variant_result_map[v.variant_id] = {
            "pass_pct": v_pass,
            "coherence": v_coh,
            "composite": v_composite,
        }
        if v_composite > best_composite:
            best_composite = v_composite
            best_id = v.variant_id
            best_element = v.varied_element
            best_coherence = v_coh

    coherence_lift = best_coherence - ctrl_coh

    return ImageVariantComparison(
        ad_id=control.ad_id,
        control_attributes=attribute_results["control"],
        control_coherence=ctrl_coh,
        variant_results=variant_result_map,
        winner=best_id,
        winning_element=best_element,
        coherence_lift=coherence_lift,
    )


def track_image_variant_win(
    comparison: ImageVariantComparison,
    audience: str,
    ledger_path: str,
) -> None:
    """Log an ImageVariantWin event to the ledger.

    Args:
        comparison: The image variant comparison result.
        audience: The audience segment.
        ledger_path: Path to the JSONL ledger.
    """
    log_event(ledger_path, {
        "event_type": "ImageVariantWin",
        "ad_id": comparison.ad_id,
        "brief_id": "",
        "cycle_number": 0,
        "action": "image-variant-win",
        "inputs": {
            "control_coherence": comparison.control_coherence,
        },
        "outputs": {
            "winner": comparison.winner,
            "winning_element": comparison.winning_element,
            "audience": audience,
            "coherence_lift": comparison.coherence_lift,
        },
        "scores": {},
        "tokens_consumed": 0,
        "model_used": "",
        "seed": "",
    })


def get_visual_patterns(ledger_path: str) -> dict[str, dict[str, float]]:
    """Compute win rates per audience per visual element from ledger.

    Args:
        ledger_path: Path to the JSONL ledger.

    Returns:
        Dict of {audience: {element: win_rate}}.
    """
    events = read_events_filtered(ledger_path, event_type="ImageVariantWin")

    if not events:
        return {}

    audience_wins: dict[str, list[str]] = defaultdict(list)
    for event in events:
        outputs = event.get("outputs", {})
        audience = outputs.get("audience", "unknown")
        element = outputs.get("winning_element")
        if element:
            audience_wins[audience].append(element)

    patterns: dict[str, dict[str, float]] = {}
    for audience, elements in audience_wins.items():
        total = len(elements)
        counts: dict[str, int] = defaultdict(int)
        for e in elements:
            counts[e] += 1
        patterns[audience] = {el: c / total for el, c in counts.items()}

    return patterns
