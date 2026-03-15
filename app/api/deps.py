# Ad-Ops-Autopilot — Auth dependency (PA-03)
from fastapi import Header, HTTPException
from jose import JWTError, jwt

from app.config import settings

JWT_ALGORITHM = "HS256"

# DEV_MODE: when GOOGLE_CLIENT_ID is empty, accept X-User-Id header or mock user
MOCK_USER_ID = "test-user"


def get_current_user(
    authorization: str | None = Header(default=None),
    x_user_id: str | None = Header(default=None),
) -> dict[str, str]:
    """Validate JWT and return current user. Falls back to mock in DEV_MODE."""
    # DEV_MODE: no Google client configured — use mock auth
    if not settings.GOOGLE_CLIENT_ID:
        user_id = x_user_id or MOCK_USER_ID
        return {"user_id": user_id, "email": f"{user_id}@nerdy.com", "name": user_id}

    # Production: require Bearer token
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="Invalid authorization scheme")

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}") from e

    user_id = payload.get("sub")
    email = payload.get("email")
    name = payload.get("name")

    if not user_id or not email:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    return {"user_id": user_id, "email": email, "name": name}
