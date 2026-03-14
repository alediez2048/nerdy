"""Checkpoint-resume and retry tests (P0-08).

TDD: Tests for get_pipeline_state, should_skip_ad, retry_with_backoff.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from iterate.checkpoint import (
    get_last_checkpoint,
    get_pipeline_state,
    should_skip_ad,
)
from iterate.ledger import log_event
from iterate.retry import retry_with_backoff


def _valid_event(**overrides: object) -> dict:
    """Minimal valid ledger event."""
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


# --- get_pipeline_state ---


def test_empty_ledger_returns_clean_state(tmp_path: Path) -> None:
    """Empty ledger returns clean initial state."""
    ledger_path = str(tmp_path / "ledger.jsonl")
    state = get_pipeline_state(ledger_path)
    assert len(state.generated_ids) == 0
    assert len(state.evaluated_pairs) == 0
    assert len(state.regenerated_pairs) == 0
    assert len(state.published_ids) == 0
    assert len(state.discarded_ids) == 0
    assert len(state.started_brief_ids) == 0


def test_get_pipeline_state_identifies_completed_ads(tmp_path: Path) -> None:
    """Correctly identifies generated, evaluated, published ads from ledger."""
    ledger_path = str(tmp_path / "ledger.jsonl")
    log_event(ledger_path, _valid_event(ad_id="a1", event_type="AdGenerated", brief_id="b1"))
    log_event(ledger_path, _valid_event(ad_id="a1", event_type="AdEvaluated", brief_id="b1"))
    log_event(ledger_path, _valid_event(ad_id="a1", event_type="AdPublished", brief_id="b1"))
    log_event(ledger_path, _valid_event(ad_id="a2", event_type="AdGenerated", brief_id="b1"))
    log_event(ledger_path, _valid_event(ad_id="a2", event_type="AdEvaluated", brief_id="b1"))

    state = get_pipeline_state(ledger_path)
    assert state.generated_ids == {"a1", "a2"}
    assert state.published_ids == {"a1"}
    assert ("a1", 0) in state.evaluated_pairs
    assert ("a2", 0) in state.evaluated_pairs
    assert state.started_brief_ids == {"b1"}


def test_should_skip_ad_returns_true_for_completed_stages(tmp_path: Path) -> None:
    """should_skip_ad returns True when ad has already completed the stage."""
    ledger_path = str(tmp_path / "ledger.jsonl")
    log_event(ledger_path, _valid_event(ad_id="a1", event_type="AdGenerated"))
    log_event(ledger_path, _valid_event(ad_id="a1", event_type="AdEvaluated"))

    state = get_pipeline_state(ledger_path)
    assert should_skip_ad(state, "a1", "generate") is True
    assert should_skip_ad(state, "a1", "evaluate", cycle_number=0) is True


def test_should_skip_ad_returns_false_for_pending_stages(tmp_path: Path) -> None:
    """should_skip_ad returns False when ad has not completed the stage."""
    ledger_path = str(tmp_path / "ledger.jsonl")
    log_event(ledger_path, _valid_event(ad_id="a1", event_type="AdGenerated"))

    state = get_pipeline_state(ledger_path)
    assert should_skip_ad(state, "a1", "generate") is True  # already generated
    assert should_skip_ad(state, "a1", "evaluate", cycle_number=0) is False  # not yet evaluated
    assert should_skip_ad(state, "a2", "generate") is False  # never seen


def test_resume_produces_no_duplicate_ad_ids(tmp_path: Path) -> None:
    """Simulated resume: start, add events, resume state has no duplicates."""
    ledger_path = str(tmp_path / "ledger.jsonl")
    log_event(ledger_path, _valid_event(ad_id="a1", event_type="AdGenerated"))
    log_event(ledger_path, _valid_event(ad_id="a1", event_type="AdEvaluated"))
    log_event(ledger_path, _valid_event(ad_id="a1", event_type="AdPublished"))

    state = get_pipeline_state(ledger_path)
    # If we "resume" and process, we should skip a1 for all stages
    assert should_skip_ad(state, "a1", "generate") is True
    assert should_skip_ad(state, "a1", "evaluate", cycle_number=0) is True
    assert should_skip_ad(state, "a1", "publish") is True


def test_get_last_checkpoint(tmp_path: Path) -> None:
    """get_last_checkpoint returns most recent checkpoint_id or None."""
    ledger_path = str(tmp_path / "ledger.jsonl")
    assert get_last_checkpoint(ledger_path) is None

    log_event(ledger_path, _valid_event(ad_id="a1"))
    log_event(ledger_path, _valid_event(ad_id="a2"))
    last = get_last_checkpoint(ledger_path)
    assert last is not None
    assert len(last) == 36  # UUID format


# --- retry_with_backoff ---


def test_retry_succeeds_on_first_call() -> None:
    """Retry returns result when func succeeds immediately."""
    fn = MagicMock(return_value=42)
    result = retry_with_backoff(fn)
    assert result == 42
    assert fn.call_count == 1


def test_retry_retries_on_429_then_succeeds() -> None:
    """Retry retries on 429, succeeds on second call."""
    fn = MagicMock(side_effect=[Exception("429 RESOURCE_EXHAUSTED"), 99])
    result = retry_with_backoff(fn, max_retries=3, base_delay=0.01)
    assert result == 99
    assert fn.call_count == 2


def test_retry_raises_after_max_retries() -> None:
    """Retry raises after max_retries exceeded."""
    fn = MagicMock(side_effect=Exception("429 quota exceeded"))
    with pytest.raises(Exception, match="429"):
        retry_with_backoff(fn, max_retries=2, base_delay=0.01)
    assert fn.call_count == 2


def test_retry_passes_through_non_retryable_errors() -> None:
    """Non-429/500/503 errors are raised immediately without retry."""
    fn = MagicMock(side_effect=ValueError("invalid input"))
    with pytest.raises(ValueError, match="invalid input"):
        retry_with_backoff(fn, max_retries=3)
    assert fn.call_count == 1
