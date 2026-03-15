"""Image style presets and audience mapping (P3-04).

Defines visual style presets (photorealistic, illustrated, flat_design,
lifestyle, editorial) and maps them to audience segments based on
experiment results.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from generate.style_experiments import aggregate_style_results

logger = logging.getLogger(__name__)


@dataclass
class StylePreset:
    """A visual style preset with prompt modifier."""

    name: str
    prompt_modifier: str
    target_audiences: list[str]


@dataclass
class StyleAudienceMap:
    """Recommended style per audience based on experiment results."""

    mappings: dict[str, str]
    confidence: dict[str, float]
    sample_sizes: dict[str, int]


STYLE_PRESETS: dict[str, StylePreset] = {
    "photorealistic": StylePreset(
        name="photorealistic",
        prompt_modifier="Photorealistic style, natural lighting, real-world textures, candid feel, high detail",
        target_audiences=["parents", "students"],
    ),
    "illustrated": StylePreset(
        name="illustrated",
        prompt_modifier="Clean vector-style illustration, modern, bold outlines, vibrant colors, digital art",
        target_audiences=["students"],
    ),
    "flat_design": StylePreset(
        name="flat_design",
        prompt_modifier="Flat design, minimal, geometric shapes, solid colors, no gradients, clean layout",
        target_audiences=["students"],
    ),
    "lifestyle": StylePreset(
        name="lifestyle",
        prompt_modifier="Aspirational lifestyle photography, warm tones, natural settings, social-media aesthetic",
        target_audiences=["parents", "students"],
    ),
    "editorial": StylePreset(
        name="editorial",
        prompt_modifier="Magazine-quality editorial, high contrast, dramatic lighting, professional composition",
        target_audiences=["parents"],
    ),
}

_DEFAULT_STYLE = "photorealistic"


def get_styles_for_audience(audience: str) -> list[StylePreset]:
    """Return style presets to test for the given audience.

    Initially returns all styles for experimentation.

    Args:
        audience: The audience segment (e.g., "parents", "students").

    Returns:
        List of StylePreset objects.
    """
    return list(STYLE_PRESETS.values())


def apply_style_to_spec(visual_spec: dict, style: StylePreset) -> dict:
    """Apply a style preset to a visual spec.

    Returns a new dict with style modifiers added, without mutating the original.

    Args:
        visual_spec: The original visual spec dict.
        style: The StylePreset to apply.

    Returns:
        Modified visual spec dict with style_name and style_modifier fields.
    """
    modified = dict(visual_spec)
    modified["style_name"] = style.name
    modified["style_modifier"] = style.prompt_modifier
    return modified


def build_style_audience_map(
    ledger_path: str,
    min_samples: int = 5,
) -> StyleAudienceMap:
    """Build recommended style per audience from experiment results.

    Args:
        ledger_path: Path to the JSONL ledger.
        min_samples: Minimum experiments needed for full confidence.

    Returns:
        StyleAudienceMap with mappings, confidence, and sample sizes.
    """
    aggregated = aggregate_style_results(ledger_path)

    mappings: dict[str, str] = {}
    confidence: dict[str, float] = {}
    sample_sizes: dict[str, int] = {}

    for audience, style_scores in aggregated.items():
        if not style_scores:
            continue

        # Pick highest-scoring style
        best_style = max(style_scores, key=lambda s: style_scores[s])
        mappings[audience] = best_style

        # Count samples from ledger
        from iterate.ledger import read_events_filtered
        events = read_events_filtered(ledger_path, event_type="StyleExperiment")
        n_samples = sum(
            1 for e in events
            if e.get("inputs", {}).get("audience") == audience
        )
        sample_sizes[audience] = n_samples
        confidence[audience] = min(1.0, n_samples / min_samples)

    return StyleAudienceMap(
        mappings=mappings,
        confidence=confidence,
        sample_sizes=sample_sizes,
    )


def get_recommended_style(audience: str, style_map: StyleAudienceMap) -> str:
    """Return recommended style for audience, with fallback.

    Args:
        audience: The audience segment.
        style_map: The StyleAudienceMap from experiment results.

    Returns:
        Style name string. Falls back to "photorealistic" if no data.
    """
    return style_map.mappings.get(audience, _DEFAULT_STYLE)
