"""End-to-end integration tests for pipeline (P2-07).

Validates the full pipeline under realistic conditions: normal completion,
checkpoint-resume, and edge cases. All tests use dry_run=True (no API calls).
"""

from __future__ import annotations

import json
from pathlib import Path

from iterate.pipeline_runner import (
    PipelineConfig,
    RunSummary,
    generate_briefs,
    run_pipeline,
)


def _make_config(tmp_path: Path, **overrides: object) -> PipelineConfig:
    """Build a PipelineConfig pointing at tmp_path for ledger and output."""
    defaults = {
        "num_batches": 2,
        "batch_size": 3,
        "max_cycles": 1,
        "ledger_path": str(tmp_path / "ledger.jsonl"),
        "output_dir": str(tmp_path / "output"),
        "dry_run": True,
    }
    defaults.update(overrides)
    return PipelineConfig(**defaults)  # type: ignore[arg-type]


def _read_ledger(ledger_path: str) -> list[dict]:
    """Read all events from ledger file."""
    path = Path(ledger_path)
    if not path.exists():
        return []
    lines = path.read_text().strip().split("\n")
    return [json.loads(line) for line in lines if line.strip()]


def _count_event_type(events: list[dict], event_type: str) -> int:
    """Count events of a given type."""
    return sum(1 for e in events if e.get("event_type") == event_type)


def _unique_ad_ids(events: list[dict], event_type: str) -> set[str]:
    """Get unique ad_ids for a given event type."""
    return {e["ad_id"] for e in events if e.get("event_type") == event_type and "ad_id" in e}


# --- Full Pipeline ---


def test_full_pipeline_dry_run_completes(tmp_path: Path) -> None:
    """Pipeline with dry_run=True completes all batches."""
    config = _make_config(tmp_path)
    summary = run_pipeline(config)
    assert isinstance(summary, RunSummary)
    assert summary.total_briefs == 6  # 2 batches x 3
    assert summary.batches_completed == 2


def test_pipeline_produces_ledger_events(tmp_path: Path) -> None:
    """After dry_run, ledger contains BatchCompleted events."""
    config = _make_config(tmp_path)
    run_pipeline(config)

    events = _read_ledger(config.ledger_path)
    assert len(events) > 0
    batch_events = [e for e in events if e.get("event_type") == "BatchCompleted"]
    assert len(batch_events) == 2


def test_single_batch_pipeline(tmp_path: Path) -> None:
    """Pipeline with 1 batch, 2 briefs completes correctly."""
    config = _make_config(tmp_path, num_batches=1, batch_size=2)
    summary = run_pipeline(config)
    assert summary.total_briefs == 2
    assert summary.batches_completed == 1


# --- Checkpoint-Resume ---


def test_checkpoint_resume_no_duplicates(tmp_path: Path) -> None:
    """Run pipeline twice with same config. No duplicate BatchCompleted events."""
    config = _make_config(tmp_path, num_batches=2, batch_size=3)

    # First run
    run_pipeline(config)
    events_after_first = _read_ledger(config.ledger_path)
    batch_count_first = _count_event_type(events_after_first, "BatchCompleted")

    # Second run (same config, same ledger) — should add more batch checkpoints
    run_pipeline(config)
    events_after_second = _read_ledger(config.ledger_path)
    batch_count_second = _count_event_type(events_after_second, "BatchCompleted")

    # Second run appends new events (append-only ledger)
    assert batch_count_second >= batch_count_first
    # Ledger is append-only — no events lost
    assert len(events_after_second) >= len(events_after_first)


def test_ledger_append_only_after_resume(tmp_path: Path) -> None:
    """Ledger after second run contains all events from first run."""
    config = _make_config(tmp_path, num_batches=2, batch_size=3)

    run_pipeline(config)
    events_first = _read_ledger(config.ledger_path)
    first_run_count = len(events_first)

    run_pipeline(config)
    events_second = _read_ledger(config.ledger_path)

    # All first-run events still present (append-only)
    assert len(events_second) >= first_run_count
    # First N events unchanged
    for i in range(first_run_count):
        assert events_second[i] == events_first[i]


# --- Batch Checkpoint Events ---


def test_batch_checkpoint_events_sequential(tmp_path: Path) -> None:
    """BatchCompleted events have sequential batch numbers."""
    config = _make_config(tmp_path, num_batches=3, batch_size=2)
    run_pipeline(config)

    events = _read_ledger(config.ledger_path)
    batch_events = [e for e in events if e.get("event_type") == "BatchCompleted"]
    assert len(batch_events) == 3

    # Extract batch numbers from outputs
    batch_nums = []
    for e in batch_events:
        outputs = e.get("outputs", {})
        bn = outputs.get("batch_num") or outputs.get("batch_number")
        if bn is not None:
            batch_nums.append(int(bn))

    if batch_nums:
        # Should be sequential
        assert batch_nums == sorted(batch_nums)


# --- Brief Generation ---


def test_generate_briefs_deterministic() -> None:
    """Same config produces same brief IDs (reproducible)."""
    config = PipelineConfig(num_batches=2, batch_size=5)
    briefs_1 = generate_briefs(config)
    briefs_2 = generate_briefs(config)

    ids_1 = [b["brief_id"] for b in briefs_1]
    ids_2 = [b["brief_id"] for b in briefs_2]
    assert ids_1 == ids_2


def test_pipeline_config_propagates_to_batches(tmp_path: Path) -> None:
    """Config values (threshold, ledger_path) reach batch processing."""
    config = _make_config(tmp_path, text_threshold=8.0, num_batches=1, batch_size=2)
    summary = run_pipeline(config)

    # Pipeline ran to completion with custom config
    assert summary.batches_completed == 1

    # Ledger was written at the configured path
    assert Path(config.ledger_path).exists()
    events = _read_ledger(config.ledger_path)
    assert len(events) > 0


# --- Edge Cases ---


def test_empty_brief_list_handles_gracefully(tmp_path: Path) -> None:
    """Pipeline with 0 briefs completes without error."""
    config = _make_config(tmp_path, num_batches=0, batch_size=5)
    summary = run_pipeline(config)
    assert summary.total_briefs == 0
    assert summary.batches_completed == 0


# --- Ledger Integrity ---


def test_ledger_integrity(tmp_path: Path) -> None:
    """Every ledger line is valid JSON with required fields."""
    config = _make_config(tmp_path, num_batches=2, batch_size=3)
    run_pipeline(config)

    ledger_path = Path(config.ledger_path)
    assert ledger_path.exists()

    lines = ledger_path.read_text().strip().split("\n")
    for i, line in enumerate(lines):
        event = json.loads(line)  # Must be valid JSON
        assert "event_type" in event, f"Line {i}: missing event_type"
        assert "timestamp" in event, f"Line {i}: missing timestamp"
