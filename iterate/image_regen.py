"""Image targeted regen loop — diagnostic-guided regeneration (P1-17).

When all 3 image variants fail evaluation, diagnoses the weakest attribute
or coherence dimension, appends fix guidance to the visual spec, and
generates focused regen variants. 5-image budget cap per ad.
"""

from __future__ import annotations

import logging
from collections import Counter
from dataclasses import dataclass
from typing import Any

from evaluate.coherence_checker import CoherenceResult
from evaluate.image_evaluator import ImageAttributeResult
from iterate.ledger import log_event, read_events_filtered

logger = logging.getLogger(__name__)

IMAGE_BUDGET = 5

_ATTRIBUTE_FIX_SUGGESTIONS: dict[str, str] = {
    "age_appropriate": (
        "Ensure all subjects appear student-age (16-18) or parent-age. "
        "No young children or elderly people."
    ),
    "lighting": (
        "Use warm, inviting lighting consistent with educational context. "
        "Avoid dark, harsh, or clinical lighting."
    ),
    "diversity": (
        "Include inclusive, diverse representation of students and families."
    ),
    "brand_consistent": (
        "Match Varsity Tutors visual identity: teal (#00838F), navy (#1A237E), "
        "white (#FFFFFF). No competitor branding visible."
    ),
    "no_artifacts": (
        "Ensure no AI artifacts: no extra fingers, no warped text, no distorted "
        "faces, no impossible geometry."
    ),
    "no_third_party_branding": (
        "No visible third-party logos or brand names anywhere in the image. Use "
        "generic/unbranded clothing, equipment, devices, and signage."
    ),
}

_COHERENCE_FIX_SUGGESTIONS: dict[str, str] = {
    "message_alignment": (
        "Image must directly reinforce the ad's core message. Show the specific "
        "activity or outcome described in the copy."
    ),
    "audience_match": (
        "Image must clearly appeal to the target audience. Use appropriate "
        "demographics and settings for parents or students."
    ),
    "emotional_consistency": (
        "Image emotional tone must match the copy's tone. If copy is encouraging, "
        "image should feel warm and aspirational."
    ),
    "visual_narrative": (
        "Image must tell a story consistent with the ad's value proposition. "
        "Show the transformation or benefit described in the copy."
    ),
}


@dataclass
class RegenDiagnostic:
    """Diagnostic result identifying why image variants failed."""

    failure_type: str  # "attribute" or "coherence"
    weakest_dimension: str
    fix_suggestion: str


@dataclass
class RegenResult:
    """Result of the regen loop decision."""

    ad_id: str
    regen_count: int
    blocked: bool
    diagnostic: RegenDiagnostic


def diagnose_failure(
    attribute_results: list[ImageAttributeResult],
    coherence_results: list[CoherenceResult],
) -> RegenDiagnostic:
    """Diagnose why image variants failed evaluation.

    Priority: attribute failures first, then coherence failures.

    Args:
        attribute_results: Attribute evaluation results for all variants.
        coherence_results: Coherence evaluation results for all variants.

    Returns:
        RegenDiagnostic with failure type, weakest dimension, and fix suggestion.
    """
    # Check for attribute failures — count failed attributes across all variants
    failed_attrs: list[str] = []
    for result in attribute_results:
        for attr, passed in result.attributes.items():
            if not passed:
                failed_attrs.append(attr)

    if failed_attrs:
        # Most commonly failed attribute
        counter = Counter(failed_attrs)
        weakest = counter.most_common(1)[0][0]
        return RegenDiagnostic(
            failure_type="attribute",
            weakest_dimension=weakest,
            fix_suggestion=_ATTRIBUTE_FIX_SUGGESTIONS.get(
                weakest, f"Fix {weakest} attribute issues"
            ),
        )

    # Check for coherence failures — find weakest dimension across variants
    worst_dim = ""
    worst_score = 11.0
    for result in coherence_results:
        for dim, score in result.dimension_scores.items():
            if score < worst_score:
                worst_score = score
                worst_dim = dim

    if not worst_dim:
        worst_dim = "message_alignment"

    return RegenDiagnostic(
        failure_type="coherence",
        weakest_dimension=worst_dim,
        fix_suggestion=_COHERENCE_FIX_SUGGESTIONS.get(
            worst_dim, f"Improve {worst_dim} between copy and image"
        ),
    )


def build_regen_spec(
    original_spec: dict[str, Any],
    diagnostic: RegenDiagnostic,
) -> dict[str, Any]:
    """Build a regen visual spec with diagnostic fix suggestions appended.

    Args:
        original_spec: The original visual spec dict.
        diagnostic: The failure diagnostic.

    Returns:
        New spec dict with regen_guidance field added.
    """
    new_spec = dict(original_spec)
    guidance = (
        f"REGEN FIX ({diagnostic.failure_type} — {diagnostic.weakest_dimension}): "
        f"{diagnostic.fix_suggestion}"
    )
    new_spec["regen_guidance"] = guidance
    return new_spec


def get_image_count(ad_id: str, ledger_path: str) -> int:
    """Count total images generated for an ad from ledger events.

    Args:
        ad_id: The ad identifier.
        ledger_path: Path to the ledger file.

    Returns:
        Number of ImageGenerated events for this ad.
    """
    events = read_events_filtered(ledger_path, event_type="ImageGenerated", ad_id=ad_id)
    return len(events)


def can_generate_more(ad_id: str, ledger_path: str, requested: int) -> bool:
    """Check if more images can be generated within budget.

    Args:
        ad_id: The ad identifier.
        ledger_path: Path to the ledger file.
        requested: Number of additional images requested.

    Returns:
        True if current_count + requested <= IMAGE_BUDGET.
    """
    current = get_image_count(ad_id, ledger_path)
    return current + requested <= IMAGE_BUDGET


def run_image_regen(
    ad_id: str,
    diagnostic: RegenDiagnostic,
    current_image_count: int,
) -> RegenResult:
    """Determine regen action based on diagnostic and budget.

    Args:
        ad_id: The ad identifier.
        diagnostic: The failure diagnostic.
        current_image_count: Images already generated for this ad.

    Returns:
        RegenResult with regen count and blocked status.
    """
    remaining = IMAGE_BUDGET - current_image_count

    if remaining <= 0:
        logger.warning("Image budget exhausted for %s — flagging as blocked", ad_id)
        return RegenResult(
            ad_id=ad_id,
            regen_count=0,
            blocked=True,
            diagnostic=diagnostic,
        )

    # Attribute failure = 2 regen variants, coherence failure = 1
    desired = 2 if diagnostic.failure_type == "attribute" else 1
    regen_count = min(desired, remaining)

    logger.info(
        "Regen %d variants for %s (failure=%s, weakest=%s)",
        regen_count, ad_id, diagnostic.failure_type, diagnostic.weakest_dimension,
    )

    return RegenResult(
        ad_id=ad_id,
        regen_count=regen_count,
        blocked=False,
        diagnostic=diagnostic,
    )


def flag_image_blocked(
    ad_id: str,
    diagnostic: RegenDiagnostic,
    ledger_path: str,
) -> None:
    """Flag an ad as image-blocked for human review.

    Args:
        ad_id: The ad identifier.
        diagnostic: The failure diagnostic with full context.
        ledger_path: Path to the ledger file.
    """
    log_event(
        ledger_path,
        {
            "event_type": "ImageBlocked",
            "ad_id": ad_id,
            "brief_id": "",
            "cycle_number": 0,
            "action": "image-blocked",
            "inputs": {"failure_type": diagnostic.failure_type},
            "outputs": {
                "weakest_dimension": diagnostic.weakest_dimension,
                "fix_suggestion": diagnostic.fix_suggestion,
            },
            "scores": {},
            "tokens_consumed": 0,
            "model_used": "",
            "seed": "",
        },
    )
    logger.warning(
        "Ad %s flagged as image-blocked: %s/%s",
        ad_id, diagnostic.failure_type, diagnostic.weakest_dimension,
    )
