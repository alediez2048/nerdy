"""Tests for append-only decision ledger (P0-02)."""

import json
from pathlib import Path

import pytest

from iterate.ledger import (
    LedgerValidationError,
    get_ad_lifecycle,
    log_event,
    read_events,
    read_events_filtered,
)


def _valid_event(**overrides: object) -> dict:
    """Return a minimal valid event dict."""
    base = {
        "event_type": "AdGenerated",
        "ad_id": "ad_001",
        "brief_id": "brief_001",
        "cycle_number": 0,
        "action": "generation",
        "tokens_consumed": 100,
        "model_used": "gemini-flash",
        "seed": "abc123",
    }
    base.update(overrides)
    return base


# --- Roundtrip ---


def test_write_read_roundtrip(tmp_path: Path) -> None:
    """Write event, read back, compare required + auto-injected fields."""
    ledger_path = str(tmp_path / "ledger.jsonl")
    event = _valid_event()
    log_event(ledger_path, event)

    events = read_events(ledger_path)
    assert len(events) == 1
    read = events[0]

    assert read["event_type"] == "AdGenerated"
    assert read["ad_id"] == "ad_001"
    assert read["brief_id"] == "brief_001"
    assert read["cycle_number"] == 0
    assert read["action"] == "generation"
    assert read["tokens_consumed"] == 100
    assert read["model_used"] == "gemini-flash"
    assert read["seed"] == "abc123"
    assert "timestamp" in read
    assert "checkpoint_id" in read


# --- Append-only ---


def test_append_only_multiple_writes(tmp_path: Path) -> None:
    """Multiple writes preserve all events in order."""
    ledger_path = str(tmp_path / "ledger.jsonl")
    log_event(ledger_path, _valid_event(ad_id="ad_001"))
    log_event(ledger_path, _valid_event(ad_id="ad_002"))
    log_event(ledger_path, _valid_event(ad_id="ad_003"))

    events = read_events(ledger_path)
    assert len(events) == 3
    assert events[0]["ad_id"] == "ad_001"
    assert events[1]["ad_id"] == "ad_002"
    assert events[2]["ad_id"] == "ad_003"


# --- Auto-injected fields ---


def test_auto_injected_timestamp_iso8601(tmp_path: Path) -> None:
    """Timestamp is ISO-8601 UTC."""
    ledger_path = str(tmp_path / "ledger.jsonl")
    log_event(ledger_path, _valid_event())

    events = read_events(ledger_path)
    ts = events[0]["timestamp"]
    assert "T" in ts
    assert ts.endswith("+00:00") or ts.endswith("Z")


def test_auto_injected_checkpoint_id_unique(tmp_path: Path) -> None:
    """Each write gets a unique checkpoint_id (UUID)."""
    ledger_path = str(tmp_path / "ledger.jsonl")
    log_event(ledger_path, _valid_event())
    log_event(ledger_path, _valid_event())

    events = read_events(ledger_path)
    assert len(events[0]["checkpoint_id"]) == 36
    assert len(events[1]["checkpoint_id"]) == 36
    assert events[0]["checkpoint_id"] != events[1]["checkpoint_id"]


# --- Schema validation ---


def test_schema_validation_missing_required_field(tmp_path: Path) -> None:
    """Missing required field raises LedgerValidationError."""
    ledger_path = str(tmp_path / "ledger.jsonl")
    event = _valid_event()
    del event["event_type"]

    with pytest.raises(LedgerValidationError, match="event_type"):
        log_event(ledger_path, event)


def test_schema_validation_missing_multiple_fields(tmp_path: Path) -> None:
    """Missing multiple fields lists all of them in the error."""
    ledger_path = str(tmp_path / "ledger.jsonl")
    event = {"event_type": "AdGenerated"}

    with pytest.raises(LedgerValidationError, match="ad_id"):
        log_event(ledger_path, event)


# --- Filtering ---


def test_read_events_filtered_by_event_type(tmp_path: Path) -> None:
    """Filter by event_type returns only matching events."""
    ledger_path = str(tmp_path / "ledger.jsonl")
    log_event(ledger_path, _valid_event(event_type="AdGenerated", ad_id="a1"))
    log_event(ledger_path, _valid_event(event_type="AdEvaluated", ad_id="a2"))
    log_event(ledger_path, _valid_event(event_type="AdGenerated", ad_id="a3"))

    filtered = read_events_filtered(ledger_path, event_type="AdGenerated")
    assert len(filtered) == 2
    assert all(e["event_type"] == "AdGenerated" for e in filtered)


def test_read_events_filtered_by_ad_id(tmp_path: Path) -> None:
    """Filter by ad_id returns only matching events."""
    ledger_path = str(tmp_path / "ledger.jsonl")
    log_event(ledger_path, _valid_event(ad_id="ad_001"))
    log_event(ledger_path, _valid_event(ad_id="ad_002"))
    log_event(ledger_path, _valid_event(ad_id="ad_001"))

    filtered = read_events_filtered(ledger_path, ad_id="ad_001")
    assert len(filtered) == 2
    assert all(e["ad_id"] == "ad_001" for e in filtered)


def test_read_events_filtered_by_brief_id(tmp_path: Path) -> None:
    """Filter by brief_id returns only matching events."""
    ledger_path = str(tmp_path / "ledger.jsonl")
    log_event(ledger_path, _valid_event(brief_id="b1", ad_id="a1"))
    log_event(ledger_path, _valid_event(brief_id="b2", ad_id="a2"))
    log_event(ledger_path, _valid_event(brief_id="b1", ad_id="a3"))

    filtered = read_events_filtered(ledger_path, brief_id="b1")
    assert len(filtered) == 2
    assert all(e["brief_id"] == "b1" for e in filtered)


# --- Lifecycle ---


def test_get_ad_lifecycle_chronological(tmp_path: Path) -> None:
    """get_ad_lifecycle returns events for one ad in chronological order."""
    ledger_path = str(tmp_path / "ledger.jsonl")
    log_event(ledger_path, _valid_event(ad_id="ad_x", event_type="AdGenerated"))
    log_event(ledger_path, _valid_event(ad_id="ad_y", event_type="AdEvaluated"))
    log_event(ledger_path, _valid_event(ad_id="ad_x", event_type="AdEvaluated"))
    log_event(ledger_path, _valid_event(ad_id="ad_x", event_type="AdPublished"))

    lifecycle = get_ad_lifecycle(ledger_path, "ad_x")
    assert len(lifecycle) == 3
    assert lifecycle[0]["event_type"] == "AdGenerated"
    assert lifecycle[1]["event_type"] == "AdEvaluated"
    assert lifecycle[2]["event_type"] == "AdPublished"


# --- Edge cases ---


def test_missing_file_creates_on_first_write(tmp_path: Path) -> None:
    """First write to non-existent path creates file and parent dirs."""
    ledger_path = str(tmp_path / "nested" / "dir" / "ledger.jsonl")
    assert not Path(ledger_path).exists()

    log_event(ledger_path, _valid_event())
    assert Path(ledger_path).exists()
    assert len(read_events(ledger_path)) == 1


def test_read_events_missing_file_returns_empty(tmp_path: Path) -> None:
    """read_events on non-existent path returns empty list."""
    ledger_path = str(tmp_path / "nonexistent.jsonl")
    assert read_events(ledger_path) == []


def test_jsonl_validity(tmp_path: Path) -> None:
    """Each line in ledger is valid JSON with required fields."""
    ledger_path = str(tmp_path / "ledger.jsonl")
    log_event(ledger_path, _valid_event(ad_id="a1"))
    log_event(ledger_path, _valid_event(ad_id="a2"))

    with open(ledger_path) as f:
        for line in f:
            if line.strip():
                parsed = json.loads(line)
                assert isinstance(parsed, dict)
                assert "event_type" in parsed


def test_ad_id_and_brief_id_can_be_none(tmp_path: Path) -> None:
    """ad_id and brief_id accept None for batch-level events."""
    ledger_path = str(tmp_path / "ledger.jsonl")
    event = _valid_event(ad_id=None, brief_id=None, event_type="BatchCompleted")
    log_event(ledger_path, event)

    events = read_events(ledger_path)
    assert events[0]["ad_id"] is None
    assert events[0]["brief_id"] is None


def test_log_event_does_not_mutate_caller_dict(tmp_path: Path) -> None:
    """log_event should not add timestamp/checkpoint_id to the caller's dict."""
    ledger_path = str(tmp_path / "ledger.jsonl")
    event = _valid_event()
    log_event(ledger_path, event)

    assert "timestamp" not in event
    assert "checkpoint_id" not in event
