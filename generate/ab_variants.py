"""Single-variable A/B copy variant generation (P3-02, R2-Q6).

Generates 1 control + 3 variants per ad, each changing exactly ONE element
(hook_type, emotional_angle, or cta_style). Tracks winning patterns per
audience segment for structural learning.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass

from iterate.ledger import log_event, read_events_filtered

logger = logging.getLogger(__name__)

VARIANT_ELEMENTS = ("hook_type", "emotional_angle", "cta_style")

_ELEMENT_OPTIONS: dict[str, list[str]] = {
    "hook_type": ["question", "statistic", "story", "command"],
    "emotional_angle": ["aspiration", "urgency", "empathy", "confidence"],
    "cta_style": ["direct", "soft", "scarcity", "social-proof"],
}

_VARIANT_ID_MAP: dict[str, str] = {
    "hook_type": "hook_variant",
    "emotional_angle": "emotion_variant",
    "cta_style": "cta_variant",
}


@dataclass
class CopyVariant:
    """A single copy variant with one element changed."""

    ad_id: str
    variant_id: str
    varied_element: str | None
    original_value: str
    variant_value: str
    copy: dict


@dataclass
class VariantComparison:
    """Result of comparing variants against control."""

    ad_id: str
    control_scores: dict
    variant_scores: dict[str, dict]
    winner: str
    winning_element: str | None
    lift: float


def get_element_alternatives(element: str, current_value: str) -> str:
    """Return a different value for the specified element.

    Args:
        element: One of hook_type, emotional_angle, cta_style.
        current_value: The current value to avoid.

    Returns:
        A different value from the element's option set.
    """
    options = _ELEMENT_OPTIONS.get(element, [])
    for option in options:
        if option != current_value:
            return option
    return current_value


def generate_copy_variants(
    ad_id: str,
    expanded_brief: dict,
    control_copy: dict,
) -> list[CopyVariant]:
    """Generate 3 single-variable copy variants from a control.

    Each variant changes exactly one element (hook_type, emotional_angle,
    or cta_style) while preserving everything else.

    Args:
        ad_id: The ad identifier.
        expanded_brief: The expanded brief dict.
        control_copy: The control ad copy dict.

    Returns:
        List of 3 CopyVariant objects.
    """
    variants: list[CopyVariant] = []

    for element in VARIANT_ELEMENTS:
        current_value = control_copy.get(element, "")
        alt_value = get_element_alternatives(element, current_value)
        variant_id = _VARIANT_ID_MAP[element]

        # Build variant copy — same as control but with the element swapped
        variant_copy = dict(control_copy)
        variant_copy[element] = alt_value

        variants.append(CopyVariant(
            ad_id=ad_id,
            variant_id=variant_id,
            varied_element=element,
            original_value=current_value,
            variant_value=alt_value,
            copy=variant_copy,
        ))

        logger.info("Generated %s for %s: %s → %s",
                     variant_id, ad_id, current_value, alt_value)

    return variants


def compare_variants(
    control: CopyVariant,
    variants: list[CopyVariant],
    scores: dict[str, dict],
) -> VariantComparison:
    """Compare variant scores against control to find winner.

    Args:
        control: The control CopyVariant.
        variants: List of variant CopyVariants.
        scores: Dict mapping variant_id → {"aggregate_score": float, ...}.

    Returns:
        VariantComparison with winner, winning element, and lift.
    """
    control_score = scores["control"]["aggregate_score"]
    best_id = "control"
    best_score = control_score
    best_element: str | None = None

    variant_scores: dict[str, dict] = {}
    for v in variants:
        v_scores = scores.get(v.variant_id, {})
        variant_scores[v.variant_id] = v_scores
        v_agg = v_scores.get("aggregate_score", 0.0)
        if v_agg > best_score:
            best_score = v_agg
            best_id = v.variant_id
            best_element = v.varied_element

    lift = best_score - control_score

    return VariantComparison(
        ad_id=control.ad_id,
        control_scores=scores["control"],
        variant_scores=variant_scores,
        winner=best_id,
        winning_element=best_element,
        lift=lift,
    )


def track_variant_win(
    comparison: VariantComparison,
    audience: str,
    ledger_path: str,
) -> None:
    """Log a VariantWin event to the ledger.

    Args:
        comparison: The variant comparison result.
        audience: The audience segment (e.g., "parents", "students").
        ledger_path: Path to the JSONL ledger.
    """
    log_event(ledger_path, {
        "event_type": "VariantWin",
        "ad_id": comparison.ad_id,
        "brief_id": "",
        "cycle_number": 0,
        "action": "variant-win",
        "inputs": {
            "control_score": comparison.control_scores.get("aggregate_score", 0),
        },
        "outputs": {
            "winner": comparison.winner,
            "winning_element": comparison.winning_element,
            "audience": audience,
            "lift": comparison.lift,
        },
        "scores": {},
        "tokens_consumed": 0,
        "model_used": "",
        "seed": "",
    })


def get_segment_patterns(ledger_path: str) -> dict[str, dict[str, float]]:
    """Compute win rates per audience per element from ledger.

    Args:
        ledger_path: Path to the JSONL ledger.

    Returns:
        Dict of {audience: {element: win_rate}}.
    """
    events = read_events_filtered(ledger_path, event_type="VariantWin")

    if not events:
        return {}

    # Group by audience
    audience_wins: dict[str, list[str]] = defaultdict(list)
    for event in events:
        outputs = event.get("outputs", {})
        audience = outputs.get("audience", "unknown")
        element = outputs.get("winning_element")
        if element:
            audience_wins[audience].append(element)

    # Compute win rates
    patterns: dict[str, dict[str, float]] = {}
    for audience, elements in audience_wins.items():
        total = len(elements)
        counts: dict[str, int] = defaultdict(int)
        for e in elements:
            counts[e] += 1
        patterns[audience] = {el: c / total for el, c in counts.items()}

    return patterns
