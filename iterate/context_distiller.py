"""Distilled context objects — compress iteration history for prompts (P1-09, R2-Q4).

Replaces raw iteration history with a fixed-size context object containing:
1. Best attempt so far (highest weighted average)
2. Weakest dimension + improvement guidance (contrastive rationale)
3. Deduplicated anti-patterns from failed attempts

Prompt size stays constant regardless of cycle depth.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

from iterate.ledger import read_events

logger = logging.getLogger(__name__)

DIMENSIONS = (
    "clarity",
    "value_proposition",
    "cta",
    "brand_voice",
    "emotional_resonance",
)

_MAX_ANTI_PATTERNS = 5
_TOKEN_BUDGET = 300  # approximate token budget for formatted prompt


@dataclass
class DistilledContext:
    """Compact context object for generator prompts."""

    ad_id: str
    cycle: int
    best_attempt: str
    best_scores: dict[str, float]
    weakest_dimension: str
    improvement_guidance: str
    anti_patterns: list[str]
    token_count: int = 0


def distill(ad_id: str, ledger_path: str) -> DistilledContext:
    """Compress full iteration history into a fixed-size context object.

    Reads all AdEvaluated events for ad_id, finds the best attempt,
    extracts the weakest dimension and improvement guidance, and
    compiles deduplicated anti-patterns.

    Args:
        ad_id: The ad identifier.
        ledger_path: Path to the JSONL ledger.

    Returns:
        DistilledContext with fixed-size content regardless of cycle count.
    """
    events = read_events(ledger_path)
    ad_events = [
        e for e in events
        if e.get("ad_id") == ad_id and e.get("event_type") == "AdEvaluated"
    ]

    if not ad_events:
        return DistilledContext(
            ad_id=ad_id,
            cycle=0,
            best_attempt="",
            best_scores={d: 5.0 for d in DIMENSIONS},
            weakest_dimension="clarity",
            improvement_guidance="No prior attempts available.",
            anti_patterns=[],
            token_count=0,
        )

    # Find best attempt (highest aggregate score)
    best_event = max(
        ad_events,
        key=lambda e: e.get("outputs", {}).get("aggregate_score", 0),
    )
    best_outputs = best_event.get("outputs", {})
    best_scores_raw = best_outputs.get("scores", {})
    best_scores = {
        d: best_scores_raw.get(d, {}).get("score", 5.0) for d in DIMENSIONS
    }
    best_attempt = best_outputs.get("ad_text", "")

    # Use most recent evaluation for weakest dimension and guidance
    latest = max(ad_events, key=lambda e: e.get("cycle_number", 0))
    latest_outputs = latest.get("outputs", {})
    latest_scores = latest_outputs.get("scores", {})

    weakest_dim = latest_outputs.get("weakest_dimension") or min(
        DIMENSIONS,
        key=lambda d: latest_scores.get(d, {}).get("score", 5.0),
    )

    # Extract improvement guidance from contrastive rationale
    weak_data = latest_scores.get(weakest_dim, {})
    improvement_guidance = (
        weak_data.get("plus_two_description")
        or weak_data.get("contrastive")
        or f"Improve {weakest_dim}"
    )

    # Compile anti-patterns from low-scoring dimensions across all cycles
    anti_patterns_set: set[str] = set()
    for event in ad_events:
        scores = event.get("outputs", {}).get("scores", {})
        for dim in DIMENSIONS:
            dim_data = scores.get(dim, {})
            score = dim_data.get("score", 5.0)
            if score < 6.0:
                rationale = dim_data.get("rationale", "")
                if rationale and rationale not in anti_patterns_set:
                    anti_patterns_set.add(rationale)

    # Cap and deduplicate anti-patterns
    anti_patterns = sorted(anti_patterns_set)[:_MAX_ANTI_PATTERNS]

    max_cycle = max(e.get("cycle_number", 0) for e in ad_events)

    ctx = DistilledContext(
        ad_id=ad_id,
        cycle=max_cycle,
        best_attempt=best_attempt,
        best_scores=best_scores,
        weakest_dimension=weakest_dim,
        improvement_guidance=improvement_guidance,
        anti_patterns=anti_patterns,
    )

    # Estimate token count
    formatted = format_for_prompt(ctx)
    ctx.token_count = len(formatted) // 4  # rough estimate: 4 chars per token

    logger.info(
        "Distilled %s: cycle=%d, weakest=%s, anti_patterns=%d, tokens≈%d",
        ad_id, max_cycle, weakest_dim, len(anti_patterns), ctx.token_count,
    )

    return ctx


def format_for_prompt(context: DistilledContext) -> str:
    """Render distilled context as a structured prompt section.

    Output is capped at ~300 tokens with clear headers.

    Args:
        context: The DistilledContext to format.

    Returns:
        Formatted string for injection into generator prompt.
    """
    scores_str = ", ".join(
        f"{d}: {context.best_scores.get(d, 5.0):.1f}" for d in DIMENSIONS
    )

    anti_section = ""
    if context.anti_patterns:
        items = "\n".join(f"- {p}" for p in context.anti_patterns)
        anti_section = f"\n## AVOID THESE\n{items}"

    prompt = f"""## BEST SO FAR (cycle {context.cycle})
{context.best_attempt}
Scores: {scores_str}

## IMPROVE THIS: {context.weakest_dimension}
{context.improvement_guidance}{anti_section}"""

    return prompt


def get_context_efficiency(ad_id: str, ledger_path: str) -> dict[str, Any]:
    """Compare raw history size vs distilled context size.

    Args:
        ad_id: The ad identifier.
        ledger_path: Path to the JSONL ledger.

    Returns:
        Dict with raw_tokens, distilled_tokens, compression_ratio, token_savings.
    """
    events = read_events(ledger_path)
    ad_events = [
        e for e in events
        if e.get("ad_id") == ad_id and e.get("event_type") == "AdEvaluated"
    ]

    raw_size = sum(len(json.dumps(e)) for e in ad_events)
    raw_tokens = raw_size // 4

    ctx = distill(ad_id, ledger_path)
    formatted = format_for_prompt(ctx)
    distilled_tokens = len(formatted) // 4

    compression_ratio = raw_tokens / max(distilled_tokens, 1)

    return {
        "raw_tokens": raw_tokens,
        "distilled_tokens": distilled_tokens,
        "compression_ratio": round(compression_ratio, 2),
        "token_savings": raw_tokens - distilled_tokens,
    }
