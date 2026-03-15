# Ad-Ops-Autopilot — Auth routes (PA-03)
from datetime import datetime, timedelta, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from jose import jwt
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.config import settings
from app.db import get_db, init_db
from app.models.user import User

router = APIRouter()

JWT_ALGORITHM = "HS256"


def _create_jwt(user: User) -> str:
    """Issue a JWT for the given user."""
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "name": user.name,
        "exp": datetime.now(timezone.utc) + timedelta(hours=settings.JWT_EXPIRY_HOURS),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=JWT_ALGORITHM)


def _verify_google_token(id_token: str) -> dict[str, Any]:
    """Verify Google OAuth id_token and return claims."""
    from google.auth.transport import requests as google_requests
    from google.oauth2 import id_token as google_id_token

    try:
        claims = google_id_token.verify_oauth2_token(
            id_token,
            google_requests.Request(),
            settings.GOOGLE_CLIENT_ID,
        )
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid Google token: {e}") from e

    return claims


@router.post("/google")
def google_login(
    body: dict[str, str],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    """Exchange Google id_token for a JWT. Only @nerdy.com emails allowed."""
    init_db()
    id_token_str = body.get("id_token", "")
    if not id_token_str:
        raise HTTPException(status_code=400, detail="id_token required")

    claims = _verify_google_token(id_token_str)

    email = claims.get("email", "")
    if not email.endswith("@nerdy.com"):
        raise HTTPException(status_code=403, detail="Only @nerdy.com emails are allowed")

    google_id = claims.get("sub", "")
    name = claims.get("name", email.split("@")[0])
    picture = claims.get("picture")

    # Upsert user
    user = db.query(User).filter(User.google_id == google_id).first()
    if user:
        user.name = name
        user.picture_url = picture
        user.last_login_at = datetime.now(timezone.utc)
    else:
        user = User(
            google_id=google_id,
            email=email,
            name=name,
            picture_url=picture,
            last_login_at=datetime.now(timezone.utc),
        )
        db.add(user)

    db.commit()
    db.refresh(user)

    token = _create_jwt(user)
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "picture_url": user.picture_url,
        },
    }


@router.get("/me")
def get_me(
    user: Annotated[dict, Depends(get_current_user)],
) -> dict[str, Any]:
    """Return current user profile from JWT."""
    return user
