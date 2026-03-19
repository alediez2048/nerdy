# Ad-Ops-Autopilot — Progress publisher (PA-07)
import json
import time
from typing import Any

import redis

from app.config import settings

PROGRESS_CHANNEL_PREFIX = "session:"
PROGRESS_CHANNEL_SUFFIX = ":progress"
PROGRESS_SUMMARY_KEY_PREFIX = "session:"
PROGRESS_SUMMARY_KEY_SUFFIX = ":progress_summary"
PROGRESS_BUFFER_KEY_SUFFIX = ":progress_buffer"
PROGRESS_SUMMARY_TTL = 3600
PROGRESS_BUFFER_TTL = 300  # 5 min
PROGRESS_BUFFER_MAX = 50

# Event types
CYCLE_START = "cycle_start"
BATCH_START = "batch_start"
AD_GENERATED = "ad_generated"
AD_EVALUATED = "ad_evaluated"
AD_PUBLISHED = "ad_published"
BATCH_COMPLETE = "batch_complete"
CYCLE_COMPLETE = "cycle_complete"
PIPELINE_COMPLETE = "pipeline_complete"
PIPELINE_ERROR = "pipeline_error"

# Video-specific event types (PC-03)
VIDEO_PIPELINE_START = "video_pipeline_start"
VIDEO_AD_START = "video_ad_start"
VIDEO_GENERATING = "video_generating"
VIDEO_EVALUATING = "video_evaluating"
VIDEO_AD_COMPLETE = "video_ad_complete"
VIDEO_PIPELINE_COMPLETE = "video_pipeline_complete"


def _get_redis() -> redis.Redis:
    return redis.from_url(settings.REDIS_URL, decode_responses=True)


def publish_progress(session_id: str, event: dict[str, Any]) -> None:
    """Publish progress event to Redis pub/sub, cache latest, and buffer for replay."""
    event["timestamp"] = time.time()
    channel = f"{PROGRESS_CHANNEL_PREFIX}{session_id}{PROGRESS_CHANNEL_SUFFIX}"
    summary_key = f"{PROGRESS_SUMMARY_KEY_PREFIX}{session_id}{PROGRESS_SUMMARY_KEY_SUFFIX}"
    buffer_key = f"{PROGRESS_CHANNEL_PREFIX}{session_id}{PROGRESS_BUFFER_KEY_SUFFIX}"
    payload = json.dumps(event)

    r = _get_redis()
    r.publish(channel, payload)
    r.set(summary_key, payload, ex=PROGRESS_SUMMARY_TTL)

    # Buffer last N events for Last-Event-ID replay
    r.rpush(buffer_key, payload)
    r.ltrim(buffer_key, -PROGRESS_BUFFER_MAX, -1)
    r.expire(buffer_key, PROGRESS_BUFFER_TTL)


def get_progress_summary(session_id: str) -> dict[str, Any] | None:
    """Read latest cached progress from Redis for session list polling."""
    key = f"{PROGRESS_SUMMARY_KEY_PREFIX}{session_id}{PROGRESS_SUMMARY_KEY_SUFFIX}"
    r = _get_redis()
    raw = r.get(key)
    if raw is None:
        return None
    return json.loads(raw)


def get_buffered_events(session_id: str, after_id: int = 0) -> list[str]:
    """Get buffered events after a given event ID for replay on reconnect."""
    buffer_key = f"{PROGRESS_CHANNEL_PREFIX}{session_id}{PROGRESS_BUFFER_KEY_SUFFIX}"
    r = _get_redis()
    all_events = r.lrange(buffer_key, 0, -1)
    # Events after the given ID (1-indexed)
    if after_id > 0 and after_id < len(all_events):
        return all_events[after_id:]
    return all_events if after_id == 0 else []
