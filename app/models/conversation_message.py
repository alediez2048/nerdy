# Ad-Ops-Autopilot — Agent conversation log (PJ-01)
"""Append-only chat history per (user, touchpoint).

Each row is a single turn: user message, assistant message, or tool
result. The agent loop loads the last N rows for the current
(user_id, touchpoint, session_id) on each new turn to give Gemini the
conversation context.
"""
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ConversationMessage(Base):
    """One turn in an agent conversation. Append-only."""

    __tablename__ = "conversation_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(256), nullable=False)
    # 'onboarding' | 'post_session' | 'pre_session_prep' | 'refine'
    touchpoint: Mapped[str] = mapped_column(String(32), nullable=False)
    # Optional FK to sessions.session_id — non-null for post_session +
    # pre_session_prep touchpoints. No CASCADE; if a session is deleted
    # we keep the conversation receipts.
    session_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("sessions.session_id"), nullable=True
    )
    # 'user' | 'assistant' | 'tool'
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str | None] = mapped_column(String(8192), nullable=True)
    tool_calls: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    tool_results: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    # Snapshot of brand_profile.onboarding_phase at the time this turn happened.
    phase: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        Index(
            "ix_conversation_messages_lookup",
            "user_id", "touchpoint", "session_id", "created_at",
        ),
    )
