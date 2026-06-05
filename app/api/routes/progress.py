# Ad-Ops-Autopilot — Progress SSE endpoint (PA-07)
import asyncio
import logging
from typing import Annotated

import redis
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from jose import JWTError, jwt
from sse_starlette.sse import EventSourceResponse
from sqlalchemy.orm import Session

from app.api.clerk_jwks import get_clerk_public_key
from app.api.deps import JWT_ALGORITHM, get_current_user
from app.config import settings
from app.db import get_db, init_db
from app.models.session import Session as SessionModel
from app.workers.progress import get_buffered_events

router = APIRouter()
logger = logging.getLogger(__name__)

HEARTBEAT_INTERVAL = 15


def _auth_from_token_param(token: str | None) -> dict | None:
    """Validate JWT from query param (EventSource can't send headers).

    Tries Clerk RS256 first (current auth path), falls back to legacy
    HS256 with SECRET_KEY (kept for old tokens during transition).
    """
    if not token:
        return None
    # Clerk RS256 path
    try:
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")
        if kid:
            public_key = get_clerk_public_key(kid)
            payload = jwt.decode(
                token,
                public_key,
                algorithms=["RS256"],
                issuer=settings.CLERK_ISSUER or None,
                options={"verify_aud": False},
            )
            return {"user_id": payload.get("sub"), "email": payload.get("email")}
    except (JWTError, RuntimeError, ValueError) as e:
        logger.debug("Clerk token validation failed, trying legacy: %s", e)
    # Legacy HS256 path
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return {"user_id": payload.get("sub"), "email": payload.get("email")}
    except JWTError:
        return None


async def _event_generator(
    session_id: str, request: Request, last_event_id: int = 0
):
    """Stream progress events from Redis pub/sub with heartbeat and replay."""
    r = redis.from_url(settings.REDIS_URL, decode_responses=True)
    pubsub = r.pubsub()
    channel = f"session:{session_id}:progress"
    pubsub.subscribe(channel)

    event_id = last_event_id
    last_heartbeat = asyncio.get_event_loop().time()

    # Replay buffered events on reconnect
    if last_event_id > 0:
        missed = get_buffered_events(session_id, last_event_id)
        for data in missed:
            event_id += 1
            yield {"event": "progress", "data": data, "id": str(event_id)}

    try:
        while True:
            if await request.is_disconnected():
                break

            message = await asyncio.to_thread(pubsub.get_message, timeout=1.0)
            if message and message.get("type") == "message":
                data = message.get("data", "{}")
                event_id += 1
                yield {"event": "progress", "data": data, "id": str(event_id)}
                last_heartbeat = asyncio.get_event_loop().time()
            else:
                now = asyncio.get_event_loop().time()
                if now - last_heartbeat >= HEARTBEAT_INTERVAL:
                    event_id += 1
                    yield {"event": "heartbeat", "data": "", "id": str(event_id)}
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
    authorization: str | None = Header(default=None),
    x_user_id: str | None = Header(default=None),
    token: str | None = Query(default=None),
    last_event_id: int = 0,
):
    """SSE endpoint — streams progress events.

    EventSource cannot send custom headers, so authentication accepts EITHER
    an Authorization Bearer header OR a ?token=<jwt> query param.
    """
    init_db()

    # Resolve user from Authorization header (fetch/XHR) or token param (SSE)
    effective_user: dict | None = None
    if authorization or x_user_id:
        try:
            effective_user = get_current_user(authorization=authorization, x_user_id=x_user_id)
        except HTTPException:
            effective_user = None
    if effective_user is None and token:
        effective_user = _auth_from_token_param(token)

    if effective_user is None and not settings.DEV_MODE:
        raise HTTPException(status_code=401, detail="Authentication required")

    row = db.query(SessionModel).filter(SessionModel.session_id == session_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Session not found")

    if effective_user and row.user_id != effective_user.get("user_id"):
        raise HTTPException(status_code=403, detail="Forbidden")

    # Parse Last-Event-ID from header
    header_last_id = request.headers.get("last-event-id")
    effective_last_id = int(header_last_id) if header_last_id else last_event_id

    return EventSourceResponse(
        _event_generator(session_id, request, effective_last_id)
    )
