"""Nano Banana Pro image generation with multi-variant strategy (P1-14, PRD 4.6.3).

Generates 3 image variants per ad: anchor, tone shift, composition shift.
Default aspect ratio 1:1. Extra ratios (4:5, 9:16) for published winners only.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from generate.visual_spec import VisualSpec, build_image_prompt
from iterate.retry import retry_with_backoff

logger = logging.getLogger(__name__)

VARIANT_TYPES = ("anchor", "tone_shift", "composition_shift")
_VARIANT_SEED_OFFSETS = {"anchor": 0, "tone_shift": 1000, "composition_shift": 2000}


@dataclass
class ImageVariant:
    """A single generated image variant."""

    ad_id: str
    variant_type: str
    image_path: str
    aspect_ratio: str
    visual_spec_hash: str
    prompt_used: str
    seed: int
    tokens_consumed: int = 0


def _call_image_api(
    prompt: str,
    aspect_ratio: str,
    seed: int,
    output_path: str,
) -> str:
    """Call Nano Banana Pro (Gemini image model) API.

    Args:
        prompt: Text prompt for image generation.
        aspect_ratio: Target aspect ratio (1:1, 4:5, 9:16).
        seed: Deterministic seed.
        output_path: Where to save the generated image.

    Returns:
        The output path of the saved image.
    """
    from google import genai
    from google.genai import types

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set in environment")

    def _do_call() -> str:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-2.0-flash-preview-image-generation",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE", "TEXT"],
            ),
        )

        # Save image from response
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        for part in response.candidates[0].content.parts:
            if part.inline_data is not None:
                with open(path, "wb") as f:
                    f.write(part.inline_data.data)
                return str(path)

        raise RuntimeError("No image data in API response")

    return retry_with_backoff(_do_call)


def generate_variants(
    visual_spec: VisualSpec,
    ad_id: str,
    seed: int,
    output_dir: str,
) -> list[ImageVariant]:
    """Generate all 3 image variants for an ad.

    Args:
        visual_spec: The visual spec driving generation.
        ad_id: The ad identifier.
        seed: Base seed for reproducibility.
        output_dir: Directory to save images.

    Returns:
        List of 3 ImageVariant objects.
    """
    variants: list[ImageVariant] = []
    spec_hash = visual_spec.spec_hash()

    for variant_type in VARIANT_TYPES:
        prompt = build_image_prompt(visual_spec, variant_type)
        variant_seed = seed + _VARIANT_SEED_OFFSETS[variant_type]
        filename = f"{ad_id}_{variant_type}_{visual_spec.aspect_ratio.replace(':', 'x')}.png"
        output_path = str(Path(output_dir) / filename)

        try:
            image_path = _call_image_api(
                prompt=prompt,
                aspect_ratio=visual_spec.aspect_ratio,
                seed=variant_seed,
                output_path=output_path,
            )
        except Exception as e:
            logger.error("Image generation failed for %s/%s: %s", ad_id, variant_type, e)
            image_path = output_path  # placeholder path

        variants.append(ImageVariant(
            ad_id=ad_id,
            variant_type=variant_type,
            image_path=image_path,
            aspect_ratio=visual_spec.aspect_ratio,
            visual_spec_hash=spec_hash,
            prompt_used=prompt,
            seed=variant_seed,
        ))

        logger.info("Generated %s variant for %s (seed=%d)", variant_type, ad_id, variant_seed)

    return variants


def generate_extra_ratios(
    image_variant: ImageVariant,
    ratios: list[str],
    output_dir: str,
) -> list[ImageVariant]:
    """Generate extra aspect ratios for a winning variant.

    For published winners only — regenerates at 4:5 and 9:16 using
    the same prompt and seed.

    Args:
        image_variant: The winning variant to regenerate.
        ratios: List of target aspect ratios (e.g., ["4:5", "9:16"]).
        output_dir: Directory to save images.

    Returns:
        List of additional ImageVariant objects.
    """
    extras: list[ImageVariant] = []

    for ratio in ratios:
        filename = f"{image_variant.ad_id}_{image_variant.variant_type}_{ratio.replace(':', 'x')}.png"
        output_path = str(Path(output_dir) / filename)

        try:
            image_path = _call_image_api(
                prompt=image_variant.prompt_used,
                aspect_ratio=ratio,
                seed=image_variant.seed,
                output_path=output_path,
            )
        except Exception as e:
            logger.error("Extra ratio generation failed for %s at %s: %s",
                         image_variant.ad_id, ratio, e)
            image_path = output_path

        extras.append(ImageVariant(
            ad_id=image_variant.ad_id,
            variant_type=image_variant.variant_type,
            image_path=image_path,
            aspect_ratio=ratio,
            visual_spec_hash=image_variant.visual_spec_hash,
            prompt_used=image_variant.prompt_used,
            seed=image_variant.seed,
        ))

        logger.info("Generated %s at %s for %s", image_variant.variant_type, ratio, image_variant.ad_id)

    return extras
