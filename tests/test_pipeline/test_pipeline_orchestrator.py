"""PH-03 pipeline orchestrator tests.

Cover:
- ``PipelineOrchestrator.run`` with ``NullProgressSink`` produces a
  :class:`RunSummary` end-to-end in dry-run mode (no API calls).
- Progress sinks receive the expected event sequence
  (``batch_start`` → ``batch_complete`` → ``pipeline_complete``) with
  the SSE-compatible payload shape the frontend depends on.
- ``StdoutProgressSink`` logs events; ``NullProgressSink`` is a no-op.
- Backwards-compat: the legacy ``pipeline_runner.run_pipeline`` function
  still returns a :class:`RunSummary` (it now delegates to the
  orchestrator).
- ``_build_batch_processor_config`` produces the dict shape
  ``batch_processor.process_batch`` expects.
"""

from __future__ import annotations

import logging
from typing import Any
from unittest.mock import patch

import pytest

from app.workers.progress import (
    BATCH_COMPLETE,
    BATCH_START,
    PIPELINE_COMPLETE,
)
from iterate.pipeline_orchestrator import (
    PipelineOrchestrator,
    _build_batch_processor_config,
)
from iterate.pipeline_runner import PipelineConfig, RunSummary, run_pipeline
from iterate.progress_sinks import (
    NullProgressSink,
    ProgressSink,
    RedisProgressSink,
    StdoutProgressSink,
)


class _RecordingSink:
    """Test double that captures every emit call in order."""

    def __init__(self) -> None:
        self.events: list[tuple[str, dict[str, Any]]] = []

    def emit(self, event_type: str, payload: dict[str, Any]) -> None:
        self.events.append((event_type, dict(payload)))


# --- ProgressSink basics ---------------------------------------------------


def test_null_progress_sink_is_silent() -> None:
    sink = NullProgressSink()
    sink.emit("anything", {"foo": "bar"})  # must not raise


def test_stdout_progress_sink_logs(caplog: pytest.LogCaptureFixture) -> None:
    sink = StdoutProgressSink()
    with caplog.at_level(logging.INFO, logger="pipeline.progress"):
        sink.emit("batch_start", {"batch": 1})
    assert any("batch_start" in r.message for r in caplog.records)


def test_redis_progress_sink_calls_publish_progress() -> None:
    """RedisProgressSink prefixes ``type`` and delegates to publish_progress."""
    with patch("app.workers.progress.publish_progress") as mock_pub:
        sink = RedisProgressSink("session_abc")
        sink.emit("batch_complete", {"batch": 2, "ads_generated": 5})

    mock_pub.assert_called_once()
    args = mock_pub.call_args
    assert args.args[0] == "session_abc"
    payload = args.args[1]
    assert payload["type"] == "batch_complete"
    assert payload["batch"] == 2
    assert payload["ads_generated"] == 5


# --- _build_batch_processor_config -----------------------------------------


def test_build_batch_processor_config_passthrough() -> None:
    config = PipelineConfig(
        num_batches=2, batch_size=3, max_cycles=2,
        text_threshold=6.5,
        ledger_path="/tmp/l.jsonl",
        global_seed="s1",
        persona="athlete_recruit",
        key_message="hello",
        image_enabled=False,
        creative_brief="stat_focused",
        copy_on_image=True,
        aspect_ratios=["4:5", "1:1"],
    )
    d = _build_batch_processor_config(config)
    assert d["ledger_path"] == "/tmp/l.jsonl"
    assert d["text_threshold"] == 6.5
    assert d["max_cycles"] == 2
    assert d["global_seed"] == "s1"
    assert d["persona"] == "athlete_recruit"
    assert d["key_message"] == "hello"
    assert d["image_enabled"] is False
    assert d["creative_brief"] == "stat_focused"
    assert d["copy_on_image"] is True
    assert d["aspect_ratios"] == ["4:5", "1:1"]
    assert d["improvable_range"] == [5.5, 7.0]


# --- end-to-end orchestrator behaviour -------------------------------------


def test_orchestrator_dry_run_returns_run_summary(tmp_path) -> None:
    """In dry_run mode, the orchestrator finishes without API calls."""
    config = PipelineConfig(
        num_batches=1,
        batch_size=2,
        max_cycles=1,
        ledger_path=str(tmp_path / "l.jsonl"),
        dry_run=True,
        global_seed="ph03-test",
    )
    summary = PipelineOrchestrator().run(config)
    assert isinstance(summary, RunSummary)
    assert summary.total_briefs == 2
    assert summary.batches_completed == 1


def test_orchestrator_emits_progress_event_sequence(tmp_path) -> None:
    """For a 2-batch run, sink receives 2× batch_start, 2× batch_complete, 1× pipeline_complete."""
    sink = _RecordingSink()
    config = PipelineConfig(
        num_batches=2,
        batch_size=2,
        max_cycles=1,
        ledger_path=str(tmp_path / "l.jsonl"),
        dry_run=True,
        global_seed="ph03-events",
    )
    PipelineOrchestrator(progress_sink=sink).run(config)

    types = [t for t, _ in sink.events]
    assert types.count(BATCH_START) == 2
    assert types.count(BATCH_COMPLETE) == 2
    assert types.count(PIPELINE_COMPLETE) == 1
    # batch_start always precedes the matching batch_complete
    starts = [i for i, t in enumerate(types) if t == BATCH_START]
    completes = [i for i, t in enumerate(types) if t == BATCH_COMPLETE]
    for s, c in zip(starts, completes):
        assert s < c
    # pipeline_complete is last
    assert types[-1] == PIPELINE_COMPLETE


def test_orchestrator_payload_has_sse_compatible_keys(tmp_path) -> None:
    """Frontend depends on these payload fields — assert they are all present."""
    sink = _RecordingSink()
    config = PipelineConfig(
        num_batches=1,
        batch_size=1,
        max_cycles=1,
        ledger_path=str(tmp_path / "l.jsonl"),
        dry_run=True,
        global_seed="ph03-payload",
    )
    PipelineOrchestrator(progress_sink=sink).run(config)

    required_keys = {
        "cycle", "batch", "ads_generated", "ads_evaluated",
        "ads_published", "current_score_avg", "cost_so_far",
    }
    for _event_type, payload in sink.events:
        assert required_keys.issubset(payload.keys()), (
            f"missing keys: {required_keys - payload.keys()}"
        )


def test_orchestrator_pipeline_complete_carries_final_totals(tmp_path) -> None:
    sink = _RecordingSink()
    config = PipelineConfig(
        num_batches=2,
        batch_size=2,
        max_cycles=1,
        ledger_path=str(tmp_path / "l.jsonl"),
        dry_run=True,
        global_seed="ph03-totals",
    )
    summary = PipelineOrchestrator(progress_sink=sink).run(config)

    pipeline_complete = next(
        (p for t, p in sink.events if t == PIPELINE_COMPLETE), None
    )
    assert pipeline_complete is not None
    assert pipeline_complete["ads_generated"] == summary.total_generated
    assert pipeline_complete["ads_published"] == summary.total_published


# --- backwards compatibility for legacy callers ----------------------------


def test_pipeline_runner_run_pipeline_still_returns_summary(tmp_path) -> None:
    """``iterate.pipeline_runner.run_pipeline`` is a thin shim — CLI relies on it."""
    config = PipelineConfig(
        num_batches=1, batch_size=2, max_cycles=1,
        ledger_path=str(tmp_path / "l.jsonl"),
        dry_run=True, global_seed="ph03-shim",
    )
    summary = run_pipeline(config)
    assert isinstance(summary, RunSummary)
    assert summary.total_briefs == 2


# --- protocol conformance --------------------------------------------------


def test_sinks_satisfy_progress_sink_protocol() -> None:
    """Static-style sanity check: the three real adapters are ProgressSinks."""
    null: ProgressSink = NullProgressSink()
    stdout: ProgressSink = StdoutProgressSink()
    redis: ProgressSink = RedisProgressSink("session_x")
    # If any didn't satisfy the protocol, mypy/pyright would flag it;
    # at runtime we only confirm emit() exists and is callable.
    for s in (null, stdout, redis):
        assert callable(getattr(s, "emit", None))
