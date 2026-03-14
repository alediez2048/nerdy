"""Tests for batch-sequential processor (P1-13)."""

from __future__ import annotations

import json

import pytest

from iterate.batch_processor import (
    BatchResult,
    PipelineResult,
    create_batches,
    process_batch,
    write_batch_checkpoint,
)


def _make_brief(brief_id: str, audience: str = "parents", goal: str = "conversion") -> dict:
    """Build a minimal brief dict."""
    return {
        "brief_id": brief_id,
        "audience": audience,
        "campaign_goal": goal,
        "product": "SAT prep",
        "key_message": "Expert 1-on-1 tutoring",
    }


def _make_config(batch_size: int = 10) -> dict:
    return {
        "batch_size": batch_size,
        "ledger_path": "data/ledger.jsonl",
        "cache_path": "data/cache/eval_cache.jsonl",
        "max_regeneration_cycles": 3,
        "improvable_range": [5.5, 7.0],
        "quality_threshold": 7.0,
        "ratchet_window": 5,
        "ratchet_buffer": 0.5,
        "pareto_variants": 3,
        "global_seed": "test-seed",
    }


# --- Batch Division Tests ---


def test_create_batches_divides_evenly() -> None:
    """25 briefs with batch_size=10 yields [10, 10, 5]."""
    briefs = [_make_brief(f"b{i:03d}") for i in range(25)]
    batches = create_batches(briefs, batch_size=10)
    assert len(batches) == 3
    assert len(batches[0]) == 10
    assert len(batches[1]) == 10
    assert len(batches[2]) == 5


def test_create_batches_single_batch() -> None:
    """Fewer briefs than batch_size yields one batch."""
    briefs = [_make_brief(f"b{i:03d}") for i in range(5)]
    batches = create_batches(briefs, batch_size=10)
    assert len(batches) == 1
    assert len(batches[0]) == 5


def test_create_batches_exact_multiple() -> None:
    """Exact multiple of batch_size yields no partial batch."""
    briefs = [_make_brief(f"b{i:03d}") for i in range(20)]
    batches = create_batches(briefs, batch_size=10)
    assert len(batches) == 2
    assert all(len(b) == 10 for b in batches)


def test_create_batches_empty() -> None:
    """Empty briefs yields empty batches."""
    batches = create_batches([], batch_size=10)
    assert len(batches) == 0


# --- Checkpoint Tests ---


def test_write_batch_checkpoint(tmp_path: pytest.TempPathFactory) -> None:
    """Checkpoint event written to ledger after batch completion."""
    ledger = str(tmp_path / "ledger.jsonl")
    checkpoint_id = write_batch_checkpoint(
        batch_num=1,
        batch_result=BatchResult(
            batch_num=1,
            generated=10,
            published=6,
            discarded=2,
            regenerated=2,
            escalated=0,
        ),
        ledger_path=ledger,
    )

    assert checkpoint_id is not None

    with open(ledger) as f:
        events = [json.loads(line) for line in f]

    assert len(events) == 1
    assert events[0]["event_type"] == "BatchCompleted"
    assert events[0]["outputs"]["batch_num"] == 1
    assert events[0]["outputs"]["published"] == 6


# --- BatchResult Tests ---


def test_batch_result_fields() -> None:
    """BatchResult has all required fields."""
    result = BatchResult(
        batch_num=1,
        generated=10,
        published=7,
        discarded=1,
        regenerated=2,
        escalated=0,
    )
    assert result.batch_num == 1
    assert result.generated == 10
    assert result.published == 7
    assert result.discarded == 1
    assert result.regenerated == 2
    assert result.escalated == 0


# --- PipelineResult Tests ---


def test_pipeline_result_aggregates() -> None:
    """PipelineResult aggregates across batches."""
    batch_results = [
        BatchResult(batch_num=1, generated=10, published=6, discarded=2, regenerated=2, escalated=0),
        BatchResult(batch_num=2, generated=10, published=7, discarded=1, regenerated=2, escalated=0),
        BatchResult(batch_num=3, generated=5, published=3, discarded=1, regenerated=1, escalated=0),
    ]
    result = PipelineResult.from_batches(batch_results)
    assert result.total_generated == 25
    assert result.total_published == 16
    assert result.total_discarded == 4
    assert result.total_regenerated == 5
    assert result.batches_completed == 3


def test_pipeline_result_empty() -> None:
    """PipelineResult with no batches has zero counts."""
    result = PipelineResult.from_batches([])
    assert result.total_generated == 0
    assert result.total_published == 0
    assert result.batches_completed == 0


# --- Process Batch (Mocked) Tests ---


def test_process_batch_returns_batch_result(tmp_path: pytest.TempPathFactory) -> None:
    """process_batch returns a BatchResult with correct batch number."""
    ledger = str(tmp_path / "ledger.jsonl")
    config = _make_config(batch_size=2)
    config["ledger_path"] = ledger

    briefs = [_make_brief("b001"), _make_brief("b002")]

    # process_batch in dry_run mode skips API calls
    result = process_batch(briefs, batch_num=1, config=config, dry_run=True)
    assert isinstance(result, BatchResult)
    assert result.batch_num == 1
    assert result.generated == 2  # dry_run counts briefs as generated
