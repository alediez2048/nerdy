"""Tests for narrated pipeline replay (P4-07).

Validates event parsing, batch grouping, full replay generation,
failure highlighting, and text/markdown output formatting.
"""

from __future__ import annotations

from pathlib import Path

from iterate.ledger import log_event
from output.replay import (
    BatchNarrative,
    PipelineReplay,
    ReplayEvent,
    format_replay_markdown,
    format_replay_text,
    generate_replay,
    group_events_by_batch,
    parse_event,
)


# --- Event Parsing ---


def test_parse_ad_generated() -> None:
    """AdGenerated event produces narrative."""
    event = {
        "event_type": "AdGenerated",
        "ad_id": "ad_001",
        "brief_id": "b001",
        "cycle_number": 1,
        "action": "generation",
        "tokens_consumed": 1200,
        "timestamp": "2026-03-15T10:00:00Z",
    }
    result = parse_event(event)
    assert isinstance(result, ReplayEvent)
    assert "ad_001" in result.narrative
    assert result.is_failure is False


def test_parse_ad_published() -> None:
    """AdPublished event produces narrative with score."""
    event = {
        "event_type": "AdPublished",
        "ad_id": "ad_001",
        "timestamp": "2026-03-15T10:05:00Z",
        "inputs": {"aggregate_score": 7.8},
    }
    result = parse_event(event)
    assert "published" in result.narrative.lower()
    assert result.is_failure is False


def test_parse_ad_discarded_is_failure() -> None:
    """AdDiscarded event is flagged as failure."""
    event = {
        "event_type": "AdDiscarded",
        "ad_id": "ad_002",
        "timestamp": "2026-03-15T10:06:00Z",
        "outputs": {"decision": "discard"},
    }
    result = parse_event(event)
    assert result.is_failure is True


def test_parse_batch_completed() -> None:
    """BatchCompleted event includes stats."""
    event = {
        "event_type": "BatchCompleted",
        "ad_id": "batch_1",
        "timestamp": "2026-03-15T10:10:00Z",
        "outputs": {"generated": 10, "published": 6, "discarded": 2, "regenerated": 2},
    }
    result = parse_event(event)
    assert "batch" in result.narrative.lower() or "Batch" in result.narrative


def test_parse_unknown_event() -> None:
    """Unknown event type gets generic narrative."""
    event = {
        "event_type": "SomethingNew",
        "ad_id": "ad_999",
        "timestamp": "2026-03-15T10:00:00Z",
    }
    result = parse_event(event)
    assert result.narrative != ""


def test_parse_self_healing_event() -> None:
    """SelfHealingTriggered is flagged with [HEALING] prefix concept."""
    event = {
        "event_type": "SelfHealingTriggered",
        "ad_id": "system",
        "timestamp": "2026-03-15T10:00:00Z",
        "outputs": {"action_taken": "mutate brief for VP"},
    }
    result = parse_event(event)
    assert "heal" in result.narrative.lower() or "HEAL" in result.narrative


# --- Batch Grouping ---


def test_group_events_by_batch() -> None:
    """Events are grouped between BatchCompleted markers."""
    events = [
        ReplayEvent(timestamp="t1", event_type="AdGenerated", ad_id="ad_001", narrative="gen", details={}, is_failure=False),
        ReplayEvent(timestamp="t2", event_type="AdPublished", ad_id="ad_001", narrative="pub", details={}, is_failure=False),
        ReplayEvent(timestamp="t3", event_type="BatchCompleted", ad_id="batch_1", narrative="batch done", details={"generated": 1, "published": 1}, is_failure=False),
        ReplayEvent(timestamp="t4", event_type="AdGenerated", ad_id="ad_002", narrative="gen2", details={}, is_failure=False),
        ReplayEvent(timestamp="t5", event_type="BatchCompleted", ad_id="batch_2", narrative="batch done", details={"generated": 1, "published": 0}, is_failure=False),
    ]
    batches = group_events_by_batch(events)
    assert isinstance(batches, list)
    assert len(batches) == 2
    assert isinstance(batches[0], BatchNarrative)


def test_failures_collected_in_batch() -> None:
    """Failure events are collected in batch narrative."""
    events = [
        ReplayEvent(timestamp="t1", event_type="AdGenerated", ad_id="ad_001", narrative="gen", details={}, is_failure=False),
        ReplayEvent(timestamp="t2", event_type="AdDiscarded", ad_id="ad_001", narrative="discarded", details={}, is_failure=True),
        ReplayEvent(timestamp="t3", event_type="BatchCompleted", ad_id="batch_1", narrative="batch", details={}, is_failure=False),
    ]
    batches = group_events_by_batch(events)
    assert len(batches[0].failures) == 1


# --- Full Replay ---


def test_generate_replay_from_ledger(tmp_path: Path) -> None:
    """Full replay generated from ledger file."""
    ledger_path = str(tmp_path / "ledger.jsonl")
    log_event(ledger_path, {
        "event_type": "AdGenerated", "ad_id": "ad_001", "brief_id": "b001",
        "cycle_number": 1, "action": "generation", "tokens_consumed": 1000,
        "model_used": "gemini-flash", "seed": "42",
    })
    log_event(ledger_path, {
        "event_type": "AdPublished", "ad_id": "ad_001", "brief_id": "b001",
        "cycle_number": 1, "action": "publish", "tokens_consumed": 0,
        "model_used": "none", "seed": "0",
        "inputs": {"aggregate_score": 7.5},
    })
    log_event(ledger_path, {
        "event_type": "BatchCompleted", "ad_id": "batch_1", "brief_id": "batch_1",
        "cycle_number": 0, "action": "batch-complete", "tokens_consumed": 0,
        "model_used": "none", "seed": "0",
        "inputs": {"batch_num": 1},
        "outputs": {"generated": 1, "published": 1, "discarded": 0, "regenerated": 0},
    })
    replay = generate_replay(ledger_path)
    assert isinstance(replay, PipelineReplay)
    assert len(replay.batches) >= 1
    assert replay.total_summary != ""


# --- Text Output ---


def test_format_replay_text(tmp_path: Path) -> None:
    """Text formatter produces readable output."""
    ledger_path = str(tmp_path / "ledger.jsonl")
    log_event(ledger_path, {
        "event_type": "AdGenerated", "ad_id": "ad_001", "brief_id": "b001",
        "cycle_number": 1, "action": "generation", "tokens_consumed": 1000,
        "model_used": "gemini-flash", "seed": "42",
    })
    log_event(ledger_path, {
        "event_type": "BatchCompleted", "ad_id": "batch_1", "brief_id": "batch_1",
        "cycle_number": 0, "action": "batch-complete", "tokens_consumed": 0,
        "model_used": "none", "seed": "0",
        "inputs": {"batch_num": 1},
        "outputs": {"generated": 1, "published": 0},
    })
    replay = generate_replay(ledger_path)
    text = format_replay_text(replay)
    assert isinstance(text, str)
    assert "Batch" in text or "batch" in text


def test_format_replay_markdown(tmp_path: Path) -> None:
    """Markdown formatter produces valid markdown."""
    ledger_path = str(tmp_path / "ledger.jsonl")
    log_event(ledger_path, {
        "event_type": "AdGenerated", "ad_id": "ad_001", "brief_id": "b001",
        "cycle_number": 1, "action": "generation", "tokens_consumed": 500,
        "model_used": "gemini-flash", "seed": "42",
    })
    log_event(ledger_path, {
        "event_type": "BatchCompleted", "ad_id": "batch_1", "brief_id": "batch_1",
        "cycle_number": 0, "action": "batch-complete", "tokens_consumed": 0,
        "model_used": "none", "seed": "0",
        "inputs": {"batch_num": 1},
        "outputs": {"generated": 1, "published": 0},
    })
    replay = generate_replay(ledger_path)
    md = format_replay_markdown(replay)
    assert isinstance(md, str)
    assert "#" in md  # Has markdown headers
