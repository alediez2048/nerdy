"""Fernet symmetric encryption for user-supplied API keys at rest.

Plaintext keys are encrypted with ``KEYS_ENCRYPTION_KEY`` (a Fernet key in
URL-safe base64). Decryption happens only at the moment of pipeline use;
the API never returns plaintext.
"""
from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken

from app.config import settings


class EncryptionNotConfigured(RuntimeError):
    """KEYS_ENCRYPTION_KEY is unset or malformed."""


def _fernet() -> Fernet:
    key = settings.KEYS_ENCRYPTION_KEY
    if not key:
        raise EncryptionNotConfigured(
            "KEYS_ENCRYPTION_KEY is not set. Generate one with "
            'python -c "from cryptography.fernet import Fernet; '
            'print(Fernet.generate_key().decode())"'
        )
    try:
        return Fernet(key.encode() if isinstance(key, str) else key)
    except (ValueError, TypeError) as e:
        raise EncryptionNotConfigured(f"KEYS_ENCRYPTION_KEY is malformed: {e}") from e


def encrypt(plaintext: str) -> str:
    """Encrypt a plaintext key. Returns URL-safe base64 ciphertext."""
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: str) -> str:
    """Decrypt a stored ciphertext. Raises ValueError if the token is bad."""
    try:
        return _fernet().decrypt(ciphertext.encode()).decode()
    except InvalidToken as e:
        raise ValueError("Stored key could not be decrypted (rotated KEYS_ENCRYPTION_KEY?)") from e


def last_four(plaintext: str) -> str:
    """Return the last 4 characters of the plaintext for UI display."""
    return plaintext[-4:] if len(plaintext) >= 4 else plaintext
