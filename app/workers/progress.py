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
PROGRESS_SUMMARY_TTL = 3600

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


def _get_redis() -> redis.Redis:
    return redis.from_url(settings.REDIS_URL, decode_responses=True)


def publish_progress(session_id: str, event: dict[str, Any]) -> None:
    """Publish progress event to Redis pub/sub and cache latest for polling."""
    event["timestamp"] = time.time()
    channel = f"{PROGRESS_CHANNEL_PREFIX}{session_id}{PROGRESS_CHANNEL_SUFFIX}"
    key = f"{PROGRESS_SUMMARY_KEY_PREFIX}{session_id}{PROGRESS_SUMMARY_KEY_SUFFIX}"
    payload = json.dumps(event)
    r = _get_redis()
    r.publish(channel, payload)
    r.set(key, payload, ex=PROGRESS_SUMMARY_TTL)


def get_progress_summary(session_id: str) -> dict[str, Any] | None:
    """Read latest cached progress from Redis for session list polling."""
    key = f"{PROGRESS_SUMMARY_KEY_PREFIX}{session_id}{PROGRESS_SUMMARY_KEY_SUFFIX}"
    r = _get_redis()
    raw = r.get(key)
    if raw is None:
        return None
    return json.loads(raw)
