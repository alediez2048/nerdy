# PA-07: Progress reporting tests
"""Tests for progress publishing, event buffering, and SSE endpoint."""

import json
from unittest.mock import MagicMock, patch


# --- publish_progress tests (unit, mock Redis) ---


def test_publish_progress_sends_to_channel():
    """publish_progress publishes to Redis pub/sub and caches summary."""
    mock_redis = MagicMock()

    with patch("app.workers.progress._get_redis", return_value=mock_redis):
        from app.workers.progress import publish_progress

        publish_progress("sess_test", {
            "type": "ad_generated",
            "cycle": 1,
            "batch": 1,
            "ads_generated": 5,
        })

    # pub/sub publish called
    mock_redis.publish.assert_called_once()
    channel = mock_redis.publish.call_args[0][0]
    assert "sess_test" in channel
    assert "progress" in channel

    # Summary cached
    mock_redis.set.assert_called_once()
    key = mock_redis.set.call_args[0][0]
    assert "sess_test" in key

    # Buffer appended
    mock_redis.rpush.assert_called_once()
    mock_redis.ltrim.assert_called_once()
    mock_redis.expire.assert_called_once()


def test_publish_progress_adds_timestamp():
    """publish_progress adds a timestamp field."""
    mock_redis = MagicMock()

    with patch("app.workers.progress._get_redis", return_value=mock_redis):
        from app.workers.progress import publish_progress

        publish_progress("sess_ts", {"type": "cycle_start", "cycle": 1})

    payload = mock_redis.publish.call_args[0][1]
    event = json.loads(payload)
    assert "timestamp" in event
    assert event["type"] == "cycle_start"


def test_get_progress_summary_returns_cached():
    """get_progress_summary reads from Redis cache."""
    mock_redis = MagicMock()
    cached = json.dumps({"type": "ad_evaluated", "ads_generated": 10})
    mock_redis.get.return_value = cached

    with patch("app.workers.progress._get_redis", return_value=mock_redis):
        from app.workers.progress import get_progress_summary

        result = get_progress_summary("sess_cached")

    assert result is not None
    assert result["ads_generated"] == 10


def test_get_progress_summary_returns_none_when_empty():
    """get_progress_summary returns None when no cache exists."""
    mock_redis = MagicMock()
    mock_redis.get.return_value = None

    with patch("app.workers.progress._get_redis", return_value=mock_redis):
        from app.workers.progress import get_progress_summary

        result = get_progress_summary("sess_empty")

    assert result is None


def test_get_buffered_events_returns_after_id():
    """get_buffered_events returns events after the given ID."""
    mock_redis = MagicMock()
    mock_redis.lrange.return_value = [
        json.dumps({"type": "ad_generated", "id": 1}),
        json.dumps({"type": "ad_evaluated", "id": 2}),
        json.dumps({"type": "ad_published", "id": 3}),
    ]

    with patch("app.workers.progress._get_redis", return_value=mock_redis):
        from app.workers.progress import get_buffered_events

        # After event 1, should get events 2 and 3
        result = get_buffered_events("sess_buf", after_id=1)
        assert len(result) == 2

        # After event 0, should get all
        result_all = get_buffered_events("sess_buf", after_id=0)
        assert len(result_all) == 3


# --- Pipeline task tests ---


def test_pipeline_task_updates_status():
    """Pipeline task sets status to running then completed."""
    from app.workers.tasks.pipeline_task import run_pipeline_session

    mock_db_session = MagicMock()
    mock_row = MagicMock()
    mock_row.session_id = "sess_task"
    mock_row.status = "pending"
    mock_db_session.query.return_value.filter.return_value.first.return_value = mock_row

    with (
        patch("app.workers.tasks.pipeline_task.SessionLocal", return_value=mock_db_session),
        patch("app.workers.tasks.pipeline_task.init_db"),
        patch("app.workers.tasks.pipeline_task.publish_progress"),
    ):
        result = run_pipeline_session("sess_task")

    assert result["status"] == "completed"
    assert result["ads_published"] > 0


# --- Event type constants ---


def test_event_types_defined():
    """All expected event types are defined."""
    from app.workers.progress import (
        CYCLE_START,
        BATCH_START,
        AD_GENERATED,
        AD_EVALUATED,
        AD_PUBLISHED,
        BATCH_COMPLETE,
        CYCLE_COMPLETE,
        PIPELINE_COMPLETE,
        PIPELINE_ERROR,
    )

    types = [
        CYCLE_START, BATCH_START, AD_GENERATED, AD_EVALUATED,
        AD_PUBLISHED, BATCH_COMPLETE, CYCLE_COMPLETE,
        PIPELINE_COMPLETE, PIPELINE_ERROR,
    ]
    assert len(types) == 9
    assert all(isinstance(t, str) for t in types)
