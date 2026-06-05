"""BYO API Keys — list / save / delete a user's provider keys."""
from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session as SASession

from app.api.deps import get_current_user
from app.api.key_crypto import EncryptionNotConfigured, encrypt, last_four
from app.api.key_probes import PROVIDERS, KeyRejected, ProbeUnavailable, probe
from app.db import get_db, init_db
from app.models.user_api_key import UserApiKey

logger = logging.getLogger(__name__)

router = APIRouter()


def _serialize(row: UserApiKey) -> dict:
    return {
        "provider": row.provider,
        "last_four": row.last_four,
        "validated_at": row.validated_at.isoformat() if row.validated_at else None,
    }


@router.get("")
def list_keys(
    db: Annotated[SASession, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user)],
) -> dict:
    init_db()
    rows = (
        db.query(UserApiKey)
        .filter(UserApiKey.user_id == user["user_id"])
        .order_by(UserApiKey.provider)
        .all()
    )
    return {"keys": [_serialize(r) for r in rows]}


@router.put("/{provider}")
def save_key(
    provider: str,
    db: Annotated[SASession, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user)],
    payload: Annotated[dict, Body(...)],
) -> dict:
    init_db()
    if provider not in PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")

    api_key = (payload or {}).get("api_key")
    if not isinstance(api_key, str) or not api_key.strip():
        raise HTTPException(status_code=400, detail="api_key is required")

    api_key = api_key.strip()

    try:
        probe(provider, api_key)
    except KeyRejected as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except ProbeUnavailable as e:
        raise HTTPException(status_code=503, detail=str(e)) from e

    try:
        ciphertext = encrypt(api_key)
    except EncryptionNotConfigured as e:
        logger.error("Cannot save key: %s", e)
        raise HTTPException(status_code=500, detail="Server encryption not configured") from e

    from sqlalchemy import func as sa_func

    row = (
        db.query(UserApiKey)
        .filter(UserApiKey.user_id == user["user_id"], UserApiKey.provider == provider)
        .first()
    )
    if row is None:
        row = UserApiKey(
            user_id=user["user_id"],
            provider=provider,
            ciphertext=ciphertext,
            last_four=last_four(api_key),
        )
        db.add(row)
    else:
        row.ciphertext = ciphertext
        row.last_four = last_four(api_key)
    # Stamp validated_at via SQL func.now() to use the DB clock.
    row.validated_at = sa_func.now()
    db.commit()
    db.refresh(row)
    return _serialize(row)


@router.delete("/{provider}", status_code=204)
def delete_key(
    provider: str,
    db: Annotated[SASession, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user)],
) -> None:
    init_db()
    if provider not in PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")
    row = (
        db.query(UserApiKey)
        .filter(UserApiKey.user_id == user["user_id"], UserApiKey.provider == provider)
        .first()
    )
    if row is not None:
        db.delete(row)
        db.commit()
    return None
