# Ad-Ops-Autopilot — Progress SSE endpoint (PA-07)
import asyncio
from typing import Annotated

import redis
from fastapi import APIRouter, Depends, HTTPException, Request
from sse_starlette.sse import EventSourceResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.config import settings
from app.db import get_db, init_db
from app.models.session import Session as SessionModel

router = APIRouter()

HEARTBEAT_INTERVAL = 15


async def _event_generator(session_id: str, request: Request):
    """Stream progress events from Redis pub/sub with heartbeat."""
    r = redis.from_url(settings.REDIS_URL, decode_responses=True)
    pubsub = r.pubsub()
    channel = f"session:{session_id}:progress"
    pubsub.subscribe(channel)

    last_heartbeat = asyncio.get_event_loop().time()
    event_id = 0

    try:
        while True:
            if await request.is_disconnected():
                break

            message = await asyncio.to_thread(pubsub.get_message, timeout=1.0)
            if message and message.get("type") == "message":
                data = message.get("data", "{}")
                event_id += 1
                yield {
                    "event": "progress",
                    "data": data,
                    "id": str(event_id),
                }
                last_heartbeat = asyncio.get_event_loop().time()
            else:
                now = asyncio.get_event_loop().time()
                if now - last_heartbeat >= HEARTBEAT_INTERVAL:
                    event_id += 1
                    yield {
                        "event": "heartbeat",
                        "data": "",
                        "id": str(event_id),
                    }
                    last_heartbeat = now

            await asyncio.sleep(0.1)
    finally:
        pubsub.unsubscribe(channel)
        pubsub.close()


@router.get("/{session_id}/progress")
async def stream_progress(
    session_id: str,
    db: Annotated[Session, Depends(get_db)],
    request: Request,
    _user: Annotated[dict, Depends(get_current_user)],
):
    """SSE endpoint — streams progress events, heartbeat every 15s. 404 if session not found."""
    init_db()
    row = db.query(SessionModel).filter(SessionModel.session_id == session_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Session not found")

    return EventSourceResponse(_event_generator(session_id, request))
