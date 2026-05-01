# Ad-Ops-Autopilot — User model (PA-02)
from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class User(Base):
    """User — authenticated via Clerk (or legacy Google SSO)."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    clerk_id: Mapped[str | None] = mapped_column(String(256), unique=True, index=True, nullable=True)
    google_id: Mapped[str] = mapped_column(String(256), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(256), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(256))
    picture_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # TODO(PG-06): After data migration, add FK constraints:
    #   sessions.user_id → users.clerk_id
    #   campaigns.user_id → users.clerk_id
