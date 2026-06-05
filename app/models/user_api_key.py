# Ad-Ops-Autopilot — Per-user API keys (BYO providers)
from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class UserApiKey(Base):
    """A user's API key for one provider (gemini | fal | kling).

    The ``ciphertext`` column holds the Fernet-encrypted plaintext key. The
    ``last_four`` column stores the last 4 characters of the plaintext for
    UI display only. Plaintext is decrypted only at the moment of pipeline
    use and is never returned by the API.
    """

    __tablename__ = "user_api_keys"

    user_id: Mapped[str] = mapped_column(String(256), primary_key=True, index=True)
    provider: Mapped[str] = mapped_column(String(32), primary_key=True)
    ciphertext: Mapped[str] = mapped_column(String(2048))
    last_four: Mapped[str] = mapped_column(String(4))
    validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
