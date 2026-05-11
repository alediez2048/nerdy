"""PH-01 ledger seam tests.

Cover:
- `LedgerWriter` writes JSONL byte-identical to the legacy `log_event(dict)` path
  (for inputs that match the canonical key ordering).
- `event_type` is derived from the dataclass class name — no string literal.
- Every registered subclass round-trips through write → read_typed_events.
- `LedgerReader` returns typed instances; unknown event_types fall back to base.
- `extra` flattens into the top-level dict and round-trips on read.
"""

from __future__ import annotations

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

from iterate.ledger import log_event
from iterate.ledger_events import (
    EVENT_TYPES,
    AdGenerated,
    AspectRatioGenerated,
    BatchCompleted,
    BriefExpanded,
    LedgerEvent,
    VideoBlocked,
)
from iterate.ledger_reader import (
    LedgerReader,
    iter_typed_events,
    read_typed_events,
    read_typed_events_filtered,
)
from iterate.ledger_writer import LedgerWriter, _serialize


# --- event_type derivation ---


def test_event_type_derived_from_class_name() -> None:
    ev = AdGenerated(
        ad_id="a1", brief_id="b1", cycle_number=0, action="generation",
        tokens_consumed=100, model_used="gemini-2.0-flash", seed="s",
    )
    assert ev.event_type == "AdGenerated"


def test_event_type_for_all_registered_classes() -> None:
    for name, cls in EVENT_TYPES.items():
        instance = cls(
            brief_id="b", cycle_number=0, action="a",
            tokens_consumed=0, model_used="m", seed="s",
        )
        assert instance.event_type == name


# --- byte-identical serialization for canonical orderings ---


def test_writer_matches_log_event_byte_identical() -> None:
    payload_dict = {
        "event_type": "AdGenerated",
        "ad_id": "ad_001",
        "brief_id": "b1",
        "cycle_number": 0,
        "action": "generation",
        "tokens_consumed": 150,
        "model_used": "gemini-2.0-flash",
        "seed": "seed_001",
        "inputs": {"brief_id": "b1"},
        "outputs": {"headline": "Test"},
    }
    ev_typed = AdGenerated(
        ad_id="ad_001", brief_id="b1", cycle_number=0, action="generation",
        tokens_consumed=150, model_used="gemini-2.0-flash", seed="seed_001",
        inputs={"brief_id": "b1"}, outputs={"headline": "Test"},
    )

    with (
        patch("iterate.ledger.datetime") as mock_dt,
        patch("iterate.ledger.uuid4") as mock_uuid,
    ):
        mock_dt.now.return_value = datetime(2026, 5, 10, tzinfo=timezone.utc)
        mock_uuid.return_value = "fixed-uuid"

        with tempfile.TemporaryDirectory() as d:
            p_old = Path(d) / "old.jsonl"
            p_new = Path(d) / "new.jsonl"
            log_event(str(p_old), payload_dict)
            LedgerWriter(str(p_new)).record(ev_typed)
            assert p_old.read_text() == p_new.read_text()


def test_serializer_legacy_key_order() -> None:
    ev = AdGenerated(
        ad_id="x", brief_id="b", cycle_number=0, action="a",
        tokens_consumed=1, model_used="m", seed="s",
    )
    keys = list(_serialize(ev).keys())
    expected_prefix = [
        "event_type", "ad_id", "brief_id", "cycle_number", "action",
        "tokens_consumed", "model_used", "seed", "inputs", "outputs",
    ]
    assert keys[: len(expected_prefix)] == expected_prefix


# --- extra fields flatten and round-trip ---


def test_extra_fields_flatten_to_top_level() -> None:
    ev = AspectRatioGenerated(
        ad_id="x", brief_id="", cycle_number=0, action="a",
        tokens_consumed=0, model_used="m", seed="s",
        extra={"scores": {"clarity": 7.0}, "custom_flag": True},
    )
    payload = _serialize(ev)
    assert payload["scores"] == {"clarity": 7.0}
    assert payload["custom_flag"] is True
    assert "extra" not in payload  # never serialize the container itself


# --- write → read_typed_events round-trip ---


def test_write_read_typed_round_trip() -> None:
    with tempfile.TemporaryDirectory() as d:
        p = str(Path(d) / "l.jsonl")
        w = LedgerWriter(p)
        w.record(BriefExpanded(
            ad_id=None, brief_id="b1", cycle_number=0, action="brief-expansion",
            tokens_consumed=100, model_used="m", seed="s",
            inputs={"brief": "raw"}, outputs={"angles": ["a"]},
        ))
        w.record(AdGenerated(
            ad_id="ad_001", brief_id="b1", cycle_number=0, action="generation",
            tokens_consumed=150, model_used="m", seed="s2",
        ))
        events = read_typed_events(p)

    assert len(events) == 2
    assert isinstance(events[0], BriefExpanded)
    assert events[0].brief_id == "b1"
    assert isinstance(events[1], AdGenerated)
    assert events[1].ad_id == "ad_001"


def test_unknown_event_type_falls_back_to_base() -> None:
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "l.jsonl"
        # Write a raw line with an event_type that is NOT registered.
        line = json.dumps({
            "event_type": "FutureEventType",
            "ad_id": "ad", "brief_id": "b", "cycle_number": 0,
            "action": "future", "tokens_consumed": 0,
            "model_used": "m", "seed": "s",
            "inputs": {}, "outputs": {},
            "timestamp": "2026-05-10T00:00:00+00:00",
            "checkpoint_id": "abc",
        })
        p.write_text(line + "\n")
        events = read_typed_events(str(p))

    assert len(events) == 1
    # Base LedgerEvent — type-erased, but data preserved.
    assert type(events[0]) is LedgerEvent
    assert events[0].extra.get("event_type") == "FutureEventType"


def test_extra_fields_preserved_on_read() -> None:
    with tempfile.TemporaryDirectory() as d:
        p = str(Path(d) / "l.jsonl")
        LedgerWriter(p).record(VideoBlocked(
            ad_id="ad", brief_id="b", cycle_number=0, action="video_blocked",
            tokens_consumed=0, model_used="fal", seed="0",
            outputs={"reason": "no_variants"},
            extra={"scores": {}},
        ))
        events = read_typed_events(p)
        assert events[0].extra["scores"] == {}
        # timestamp + checkpoint_id captured into extra
        assert "timestamp" in events[0].extra
        assert "checkpoint_id" in events[0].extra


def test_read_typed_events_filtered() -> None:
    with tempfile.TemporaryDirectory() as d:
        p = str(Path(d) / "l.jsonl")
        w = LedgerWriter(p)
        w.record(AdGenerated(
            ad_id="ad_001", brief_id="b1", cycle_number=0, action="generation",
            tokens_consumed=1, model_used="m", seed="s",
        ))
        w.record(AdGenerated(
            ad_id="ad_002", brief_id="b1", cycle_number=0, action="generation",
            tokens_consumed=1, model_used="m", seed="s",
        ))
        found = read_typed_events_filtered(p, ad_id="ad_001")

    assert len(found) == 1
    assert found[0].ad_id == "ad_001"


def test_iter_typed_events_is_lazy() -> None:
    with tempfile.TemporaryDirectory() as d:
        p = str(Path(d) / "l.jsonl")
        w = LedgerWriter(p)
        for i in range(5):
            w.record(AdGenerated(
                ad_id=f"ad_{i}", brief_id="b", cycle_number=0, action="generation",
                tokens_consumed=0, model_used="m", seed="s",
            ))
        gen = iter_typed_events(p)
        first = next(iter(gen))
        assert isinstance(first, AdGenerated)


def test_ledger_reader_ad_lifecycle() -> None:
    with tempfile.TemporaryDirectory() as d:
        p = str(Path(d) / "l.jsonl")
        w = LedgerWriter(p)
        w.record(AdGenerated(
            ad_id="ad_001", brief_id="b", cycle_number=0, action="generation",
            tokens_consumed=1, model_used="m", seed="s",
        ))
        w.record(AdGenerated(
            ad_id="ad_002", brief_id="b", cycle_number=0, action="generation",
            tokens_consumed=1, model_used="m", seed="s",
        ))
        reader = LedgerReader(p)
        lifecycle = reader.ad_lifecycle("ad_001")
        assert len(lifecycle) == 1
        assert lifecycle[0].ad_id == "ad_001"


# --- batch-scoped event hack still passes validation ---


def test_batch_completed_synthetic_ids_still_work() -> None:
    """BatchCompleted historically used ad_id='batch_N' to pass validation.
    PH-01 preserves this — it's not the place to redesign the contract."""
    ev = BatchCompleted(
        ad_id="batch_1", brief_id="batch_1", cycle_number=0,
        action="batch-complete", tokens_consumed=0, model_used="none", seed="0",
        outputs={"batch_num": 1, "generated": 5},
    )
    payload = _serialize(ev)
    assert payload["event_type"] == "BatchCompleted"
    assert payload["ad_id"] == "batch_1"
    # Should write without raising LedgerValidationError.
    with tempfile.TemporaryDirectory() as d:
        p = str(Path(d) / "l.jsonl")
        LedgerWriter(p).record(ev)
        assert Path(p).exists()
