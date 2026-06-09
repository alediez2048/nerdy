# Ad-Ops-Autopilot — Conversation message persistence (PJ-04)
"""Append + load helpers for ``conversation_messages``.

The load helper returns the last ``MAX_MESSAGES_RETURNED`` rows for the
current ``(user_id, touchpoint, session_id)`` so the agent always sees
a bounded amount of history (no unbounded prompt growth).
"""
from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session as SASession

from app.models.conversation_message import ConversationMessage

logger = logging.getLogger(__name__)

# Per PJ-00 §6.4: the loop sees the last 20 messages.
MAX_MESSAGES_RETURNED = 20


def append_message(
    db: SASession,
    *,
    user_id: str,
    touchpoint: str,
    session_id: str | None,
    role: str,
    content: str | None = None,
    tool_calls: dict[str, Any] | None = None,
    tool_results: dict[str, Any] | None = None,
    phase: str | None = None,
) -> ConversationMessage:
    """Append a single turn to the log."""
    row = ConversationMessage(
        user_id=user_id,
        touchpoint=touchpoint,
        session_id=session_id,
        role=role,
        content=content,
        tool_calls=tool_calls,
        tool_results=tool_results,
        phase=phase,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def load_history(
    db: SASession,
    *,
    user_id: str,
    touchpoint: str,
    session_id: str | None,
    limit: int = MAX_MESSAGES_RETURNED,
) -> list[ConversationMessage]:
    """Return the last ``limit`` messages for this ``(user, touchpoint, session)``
    in chronological order (oldest first), so they can be replayed into Gemini.
    """
    q = db.query(ConversationMessage).filter(
        ConversationMessage.user_id == user_id,
        ConversationMessage.touchpoint == touchpoint,
    )
    if session_id is None:
        q = q.filter(ConversationMessage.session_id.is_(None))
    else:
        q = q.filter(ConversationMessage.session_id == session_id)

    # Newest first → take the slice → reverse so we feed Gemini old→new.
    rows = (
        q.order_by(ConversationMessage.created_at.desc(), ConversationMessage.id.desc())
        .limit(limit)
        .all()
    )
    return list(reversed(rows))
