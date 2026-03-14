"""Tests for full pipeline run orchestration (P1-20)."""

from __future__ import annotations

import json
from pathlib import Path
from iterate.pipeline_runner import (
    PipelineConfig,
    RunSummary,
    generate_briefs,
    run_pipeline,
)


def test_pipeline_config_defaults() -> None:
    """PipelineConfig has sensible defaults."""
    config = PipelineConfig()
    assert config.num_batches == 5
    assert config.batch_size == 10
    assert config.max_cycles == 3
    assert config.text_threshold == 7.0
    assert config.image_attribute_threshold == 0.8
    assert config.coherence_threshold == 6.0


def test_generate_briefs_produces_correct_count() -> None:
    """generate_briefs produces num_batches * batch_size briefs."""
    config = PipelineConfig(num_batches=3, batch_size=5)
    briefs = generate_briefs(config)
    assert len(briefs) == 15
    assert all("brief_id" in b for b in briefs)
    assert all("audience" in b for b in briefs)
    assert all("campaign_goal" in b for b in briefs)


def test_generate_briefs_alternates_audiences() -> None:
    """Briefs alternate between parents and students audiences."""
    config = PipelineConfig(num_batches=2, batch_size=10)
    briefs = generate_briefs(config)
    audiences = {b["audience"] for b in briefs}
    assert "parents" in audiences
    assert "students" in audiences


def test_generate_briefs_mixes_campaign_goals() -> None:
    """Briefs include both awareness and conversion goals."""
    config = PipelineConfig(num_batches=2, batch_size=10)
    briefs = generate_briefs(config)
    goals = {b["campaign_goal"] for b in briefs}
    assert "awareness" in goals
    assert "conversion" in goals


def test_run_pipeline_dry_run_returns_summary(tmp_path: Path) -> None:
    """Dry run completes without API calls and returns valid summary."""
    config = PipelineConfig(
        num_batches=2,
        batch_size=3,
        max_cycles=1,
        ledger_path=str(tmp_path / "ledger.jsonl"),
        output_dir=str(tmp_path / "output"),
        dry_run=True,
    )
    summary = run_pipeline(config)
    assert isinstance(summary, RunSummary)
    assert summary.total_briefs == 6
    assert summary.batches_completed == 2


def test_run_pipeline_dry_run_writes_ledger(tmp_path: Path) -> None:
    """Dry run writes batch checkpoint events to ledger."""
    ledger_path = str(tmp_path / "ledger.jsonl")
    config = PipelineConfig(
        num_batches=2,
        batch_size=3,
        max_cycles=1,
        ledger_path=ledger_path,
        output_dir=str(tmp_path / "output"),
        dry_run=True,
    )
    run_pipeline(config)

    ledger = Path(ledger_path)
    assert ledger.exists()
    events = [json.loads(line) for line in ledger.read_text().strip().split("\n")]
    batch_events = [e for e in events if e["event_type"] == "BatchCompleted"]
    assert len(batch_events) == 2


def test_run_summary_has_cost_fields(tmp_path: Path) -> None:
    """RunSummary includes cost and quality fields."""
    config = PipelineConfig(
        num_batches=1,
        batch_size=2,
        max_cycles=1,
        ledger_path=str(tmp_path / "ledger.jsonl"),
        output_dir=str(tmp_path / "output"),
        dry_run=True,
    )
    summary = run_pipeline(config)
    assert hasattr(summary, "total_briefs")
    assert hasattr(summary, "batches_completed")
    assert hasattr(summary, "total_generated")
    assert hasattr(summary, "total_published")
    assert hasattr(summary, "total_discarded")
