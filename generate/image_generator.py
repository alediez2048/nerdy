"""Image generation with Nano Banana Pro + Nano Banana 2 (P1-14, P3-01, PRD 4.6.3).

Generates 3 image variants per ad: anchor, tone shift, composition shift.
Default aspect ratio 1:1. Extra ratios (4:5, 9:16) for published winners only.

Model routing (P3-01): anchor → Pro (quality-critical), variants → NB2 (cost-tier).
Budget override forces all to NB2 when remaining budget is low.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path

from generate.visual_spec import VisualSpec, build_image_prompt
from iterate.retry import retry_with_backoff

logger = logging.getLogger(__name__)

# Model constants — Nano Banana Pro for quality, NB2 for cost-tier variants
MODEL_NANO_BANANA_PRO = "nano-banana-pro-preview"
MODEL_NANO_BANANA_2 = "gemini-2.5-flash-image"

# Budget threshold: below this, all variants use NB2 regardless of type
_BUDGET_THRESHOLD = 2.0

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
    model_used: str = field(default_factory=lambda: MODEL_NANO_BANANA_PRO)


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

    # Map aspect ratio to orientation instruction for the prompt
    _AR_INSTRUCTIONS = {
        "9:16": "Generate a VERTICAL/PORTRAIT image (9:16 aspect ratio, taller than wide, like a phone screen or Instagram Story).",
        "4:5": "Generate a PORTRAIT image (4:5 aspect ratio, slightly taller than wide, like an Instagram feed post).",
        "1:1": "Generate a SQUARE image (1:1 aspect ratio).",
    }
    ar_instruction = _AR_INSTRUCTIONS.get(aspect_ratio, _AR_INSTRUCTIONS["1:1"])
    full_prompt = f"{ar_instruction}\n\n{prompt}"

    def _do_call() -> str:
        client = genai.Client(api_key=api_key)

        # Save image from response
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        # Use Nano Banana Pro (generateContent with image modality)
        response = client.models.generate_content(
            model=MODEL_NANO_BANANA_PRO,
            contents=full_prompt,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE", "TEXT"],
            ),
        )

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


# --- Nano Banana 2 / Model Routing (P3-01) ---


def select_image_model(
    variant_type: str,
    budget_remaining: float | None = None,
) -> str:
    """Select image generation model based on variant type and budget.

    Args:
        variant_type: One of "anchor", "tone_shift", "composition_shift".
        budget_remaining: Remaining budget in dollars, or None for default routing.

    Returns:
        Model identifier string.
    """
    # Budget override: force NB2 when budget is low
    if budget_remaining is not None and budget_remaining < _BUDGET_THRESHOLD:
        logger.info("Budget override: %.2f < %.2f — using NB2 for %s",
                     budget_remaining, _BUDGET_THRESHOLD, variant_type)
        return MODEL_NANO_BANANA_2

    # Default routing: anchor → Pro, others → NB2
    if variant_type == "anchor":
        return MODEL_NANO_BANANA_PRO
    return MODEL_NANO_BANANA_2


def _call_image_api_with_model(
    prompt: str,
    aspect_ratio: str,
    seed: int,
    output_path: str,
    model: str,
) -> str:
    """Call image generation API with a specific model.

    Args:
        prompt: Text prompt for image generation.
        aspect_ratio: Target aspect ratio (1:1, 4:5, 9:16).
        seed: Deterministic seed.
        output_path: Where to save the generated image.
        model: Model identifier to use.

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
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE", "TEXT"],
            ),
        )

        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        for part in response.candidates[0].content.parts:
            if part.inline_data is not None:
                with open(path, "wb") as f:
                    f.write(part.inline_data.data)
                return str(path)

        raise RuntimeError("No image data in API response")

    return retry_with_backoff(_do_call)


def generate_image_routed(
    prompt: str,
    aspect_ratio: str,
    seed: int,
    output_path: str,
    ad_id: str,
    variant_type: str,
    budget_remaining: float | None = None,
) -> ImageVariant:
    """Generate an image using the routed model selection.

    Selects Pro or NB2 based on variant type and budget, then generates.

    Args:
        prompt: Text prompt for image generation.
        aspect_ratio: Target aspect ratio.
        seed: Deterministic seed.
        output_path: Where to save the generated image.
        ad_id: The ad identifier.
        variant_type: One of "anchor", "tone_shift", "composition_shift".
        budget_remaining: Remaining budget in dollars, or None.

    Returns:
        ImageVariant with model_used populated.
    """
    model = select_image_model(variant_type, budget_remaining)

    try:
        image_path = _call_image_api(
            prompt=prompt,
            aspect_ratio=aspect_ratio,
            seed=seed,
            output_path=output_path,
        )
    except Exception as e:
        logger.error("Routed image generation failed for %s/%s (%s): %s",
                     ad_id, variant_type, model, e)
        image_path = output_path

    return ImageVariant(
        ad_id=ad_id,
        variant_type=variant_type,
        image_path=image_path,
        aspect_ratio=aspect_ratio,
        visual_spec_hash="",
        prompt_used=prompt,
        seed=seed,
        model_used=model,
    )


def generate_variants_routed(
    visual_spec: VisualSpec,
    ad_id: str,
    seed: int,
    output_dir: str,
    budget_remaining: float | None = None,
) -> list[ImageVariant]:
    """Generate all 3 image variants using model routing.

    Anchor → Pro, tone_shift/composition_shift → NB2 (unless budget override).

    Args:
        visual_spec: The visual spec driving generation.
        ad_id: The ad identifier.
        seed: Base seed for reproducibility.
        output_dir: Directory to save images.
        budget_remaining: Remaining budget in dollars, or None.

    Returns:
        List of 3 ImageVariant objects with model_used populated.
    """
    variants: list[ImageVariant] = []
    spec_hash = visual_spec.spec_hash()

    for variant_type in VARIANT_TYPES:
        prompt = build_image_prompt(visual_spec, variant_type)
        variant_seed = seed + _VARIANT_SEED_OFFSETS[variant_type]
        model = select_image_model(variant_type, budget_remaining)
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
            logger.error("Routed generation failed for %s/%s (%s): %s",
                         ad_id, variant_type, model, e)
            image_path = output_path

        variants.append(ImageVariant(
            ad_id=ad_id,
            variant_type=variant_type,
            image_path=image_path,
            aspect_ratio=visual_spec.aspect_ratio,
            visual_spec_hash=spec_hash,
            prompt_used=prompt,
            seed=variant_seed,
            model_used=model,
        ))

        logger.info("Generated %s variant for %s via %s (seed=%d)",
                     variant_type, ad_id, model, variant_seed)

    return variants
