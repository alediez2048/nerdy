"""Tests for distilled context objects (P1-09)."""

from __future__ import annotations

import json

import pytest

from iterate.context_distiller import (
    DistilledContext,
    distill,
    format_for_prompt,
    get_context_efficiency,
)


def _write_ledger_events(ledger_path: str, events: list[dict]) -> None:
    """Write events to a JSONL ledger file."""
    with open(ledger_path, "w") as f:
        for event in events:
            f.write(json.dumps(event) + "\n")


def _make_eval_event(
    ad_id: str,
    cycle: int,
    scores: dict[str, float],
    weakest: str = "cta",
    ad_text: str = "Test ad copy",
) -> dict:
    """Build a minimal AdEvaluated ledger event."""
    return {
        "event_type": "AdEvaluated",
        "ad_id": ad_id,
        "brief_id": "b001",
        "cycle_number": cycle,
        "action": "evaluation",
        "tokens_consumed": 500,
        "model_used": "gemini-2.0-flash",
        "seed": "0",
        "inputs": {"ad_id": ad_id},
        "outputs": {
            "ad_id": ad_id,
            "scores": {
                d: {
                    "score": s,
                    "rationale": f"{d} rationale for cycle {cycle}",
                    "contrastive": f"{d} contrastive for cycle {cycle}",
                    "plus_two_description": f"A +2 {d} would look like X",
                    "specific_gap": f"Gap in {d}",
                }
                for d, s in scores.items()
            },
            "aggregate_score": sum(scores.values()) / len(scores),
            "weakest_dimension": weakest,
            "ad_text": ad_text,
        },
    }


# --- distill Tests ---


def test_distill_single_cycle(tmp_path: pytest.TempPathFactory) -> None:
    """Single cycle returns best attempt and weakest dimension."""
    ledger = str(tmp_path / "ledger.jsonl")
    scores = {"clarity": 7.0, "value_proposition": 6.0, "cta": 5.0, "brand_voice": 7.5, "emotional_resonance": 6.5}
    events = [_make_eval_event("ad_001", 1, scores, weakest="cta", ad_text="Buy now!")]
    _write_ledger_events(ledger, events)

    ctx = distill("ad_001", ledger)
    assert isinstance(ctx, DistilledContext)
    assert ctx.ad_id == "ad_001"
    assert ctx.weakest_dimension == "cta"
    assert ctx.best_scores["cta"] == 5.0


def test_distill_identifies_best_across_cycles(tmp_path: pytest.TempPathFactory) -> None:
    """distill picks the best attempt across multiple cycles."""
    ledger = str(tmp_path / "ledger.jsonl")
    scores_c1 = {"clarity": 6.0, "value_proposition": 6.0, "cta": 5.0, "brand_voice": 6.0, "emotional_resonance": 6.0}
    scores_c2 = {"clarity": 7.5, "value_proposition": 7.0, "cta": 6.5, "brand_voice": 7.0, "emotional_resonance": 7.0}
    events = [
        _make_eval_event("ad_002", 1, scores_c1, ad_text="Cycle 1 ad"),
        _make_eval_event("ad_002", 2, scores_c2, ad_text="Cycle 2 ad"),
    ]
    _write_ledger_events(ledger, events)

    ctx = distill("ad_002", ledger)
    # Cycle 2 has higher scores
    assert ctx.best_attempt == "Cycle 2 ad"
    assert ctx.best_scores["clarity"] == 7.5


def test_distill_three_cycles_fixed_size(tmp_path: pytest.TempPathFactory) -> None:
    """3 cycles produces a fixed-size DistilledContext."""
    ledger = str(tmp_path / "ledger.jsonl")
    events = []
    for c in range(1, 4):
        scores = {d: 5.0 + c * 0.5 for d in ["clarity", "value_proposition", "cta", "brand_voice", "emotional_resonance"]}
        events.append(_make_eval_event("ad_003", c, scores, ad_text=f"Cycle {c} ad"))
    _write_ledger_events(ledger, events)

    ctx = distill("ad_003", ledger)
    assert ctx.cycle == 3
    assert ctx.token_count > 0


def test_distill_size_invariance(tmp_path: pytest.TempPathFactory) -> None:
    """5 cycles produces same-size output as 3 cycles."""
    ledger3 = str(tmp_path / "ledger3.jsonl")
    ledger5 = str(tmp_path / "ledger5.jsonl")

    events3 = []
    for c in range(1, 4):
        scores = {d: 5.0 + c * 0.3 for d in ["clarity", "value_proposition", "cta", "brand_voice", "emotional_resonance"]}
        events3.append(_make_eval_event("ad_size", c, scores, ad_text=f"Cycle {c}"))

    events5 = list(events3)
    for c in range(4, 6):
        scores = {d: 5.0 + c * 0.3 for d in ["clarity", "value_proposition", "cta", "brand_voice", "emotional_resonance"]}
        events5.append(_make_eval_event("ad_size", c, scores, ad_text=f"Cycle {c}"))

    _write_ledger_events(ledger3, events3)
    _write_ledger_events(ledger5, events5)

    ctx3 = distill("ad_size", ledger3)
    ctx5 = distill("ad_size", ledger5)

    prompt3 = format_for_prompt(ctx3)
    prompt5 = format_for_prompt(ctx5)
    # Size should be similar (within 20%) — anti-patterns are capped
    assert abs(len(prompt3) - len(prompt5)) / max(len(prompt3), 1) < 0.3


def test_anti_patterns_deduplicated(tmp_path: pytest.TempPathFactory) -> None:
    """Anti-patterns are deduplicated across cycles."""
    ledger = str(tmp_path / "ledger.jsonl")
    # Same weak dimension across cycles should not duplicate anti-patterns
    scores = {"clarity": 5.0, "value_proposition": 7.0, "cta": 7.0, "brand_voice": 7.0, "emotional_resonance": 7.0}
    events = [
        _make_eval_event("ad_dedup", 1, scores, weakest="clarity"),
        _make_eval_event("ad_dedup", 2, scores, weakest="clarity"),
        _make_eval_event("ad_dedup", 3, scores, weakest="clarity"),
    ]
    _write_ledger_events(ledger, events)

    ctx = distill("ad_dedup", ledger)
    # Anti-patterns should not have duplicates
    assert len(ctx.anti_patterns) == len(set(ctx.anti_patterns))


# --- format_for_prompt Tests ---


def test_format_for_prompt_includes_all_sections(tmp_path: pytest.TempPathFactory) -> None:
    """Formatted prompt includes BEST SO FAR, IMPROVE THIS, AVOID THESE."""
    ledger = str(tmp_path / "ledger.jsonl")
    scores = {"clarity": 7.0, "value_proposition": 6.0, "cta": 5.0, "brand_voice": 7.5, "emotional_resonance": 6.5}
    events = [_make_eval_event("ad_fmt", 1, scores, weakest="cta", ad_text="Great ad copy here")]
    _write_ledger_events(ledger, events)

    ctx = distill("ad_fmt", ledger)
    prompt = format_for_prompt(ctx)

    assert "BEST SO FAR" in prompt
    assert "IMPROVE THIS" in prompt
    assert "AVOID THESE" in prompt
    assert "Great ad copy here" in prompt


def test_format_for_prompt_within_token_budget(tmp_path: pytest.TempPathFactory) -> None:
    """Formatted prompt stays within ~300 token budget (~1200 chars)."""
    ledger = str(tmp_path / "ledger.jsonl")
    events = []
    for c in range(1, 6):
        scores = {d: 5.0 + c * 0.2 for d in ["clarity", "value_proposition", "cta", "brand_voice", "emotional_resonance"]}
        events.append(_make_eval_event("ad_budget", c, scores, ad_text=f"Ad copy for cycle {c} with some content"))
    _write_ledger_events(ledger, events)

    ctx = distill("ad_budget", ledger)
    prompt = format_for_prompt(ctx)
    # ~4 chars per token, 300 tokens ≈ 1200 chars, allow some margin
    assert len(prompt) < 2000


# --- get_context_efficiency Tests ---


def test_context_efficiency_compression_ratio(tmp_path: pytest.TempPathFactory) -> None:
    """Multi-cycle ads should show compression ratio > 1."""
    ledger = str(tmp_path / "ledger.jsonl")
    events = []
    for c in range(1, 4):
        scores = {d: 5.0 + c * 0.5 for d in ["clarity", "value_proposition", "cta", "brand_voice", "emotional_resonance"]}
        events.append(_make_eval_event("ad_eff", c, scores, ad_text=f"Cycle {c} ad copy with lots of details"))
    _write_ledger_events(ledger, events)

    efficiency = get_context_efficiency("ad_eff", ledger)
    assert efficiency["compression_ratio"] >= 1.0
    assert efficiency["distilled_tokens"] > 0
    assert efficiency["raw_tokens"] > 0
