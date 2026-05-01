# Ad-Ops-Autopilot — Auth dependency (PG-01: Clerk JWT validation)
import logging

from fastapi import Header, HTTPException
from jose import JWTError, jwt

from app.config import settings
from app.api.clerk_jwks import get_clerk_public_key

logger = logging.getLogger(__name__)

MOCK_USER_ID = "test-user"

# Legacy constant — kept for backward compat (used by progress.py token param auth)
JWT_ALGORITHM = "HS256"

# Legacy demo data: rows owned by this user_id are readable by every authenticated user.
# Writes still go to the requester's own user_id — see PG-04/05/06.
LEGACY_OWNER_ID = MOCK_USER_ID

def legacy_owner_filter(user_id_column, current_user_id: str):
    """Return a SQLAlchemy filter matching the current user OR the legacy demo user.

    Use this in place of `<Model>.user_id == current_user_id` on READ queries
    to expose pre-PG demo data to all authenticated users.
    """
    from sqlalchemy import or_
    return or_(user_id_column == current_user_id, user_id_column == LEGACY_OWNER_ID)


def get_current_user(
    authorization: str | None = Header(default=None),
    x_user_id: str | None = Header(default=None),
) -> dict[str, str]:
    """Validate Clerk JWT and return current user. Falls back to mock in DEV_MODE."""
    # DEV_MODE: accept X-User-Id header or use mock user
    if settings.DEV_MODE:
        user_id = x_user_id or MOCK_USER_ID
        return {"user_id": user_id, "email": f"{user_id}@nerdy.com", "name": user_id}

    # Warn if issuer is not configured in production
    if not settings.CLERK_ISSUER:
        logger.warning("CLERK_ISSUER not set — JWT issuer validation is disabled")

    # Production: require Bearer token
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="Invalid authorization scheme")

    # Decode header to get kid for JWKS lookup
    try:
        unverified_header = jwt.get_unverified_header(token)
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token header: {e}") from e

    kid = unverified_header.get("kid")
    if not kid:
        raise HTTPException(status_code=401, detail="Token missing kid header")

    # Fetch the public key for this kid
    try:
        public_key = get_clerk_public_key(kid)
    except (RuntimeError, ValueError) as e:
        logger.error("JWKS key fetch failed: %s", e)
        raise HTTPException(status_code=401, detail=f"Key fetch failed: {e}") from e

    # Verify and decode the JWT
    try:
        payload = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            issuer=settings.CLERK_ISSUER or None,
            # Clerk does not set aud in session tokens by default
            options={"verify_aud": False},
        )
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}") from e

    # Extract claims
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token missing sub claim")

    # Clerk may place email in different claim locations
    email = (
        payload.get("email")
        or payload.get("primary_email_address")
        or _extract_email_from_addresses(payload.get("email_addresses"))
        or f"{user_id}@clerk.user"
    )
    name = payload.get("name") or payload.get("full_name") or user_id

    # Auto-create User record on first auth (PG-05)
    _upsert_user(user_id, email, name)

    return {"user_id": user_id, "email": email, "name": name}


def _upsert_user(clerk_id: str, email: str, name: str) -> None:
    """Create or update User record for this Clerk ID."""
    try:
        from app.db import SessionLocal
        from app.models.user import User

        db = SessionLocal()
        try:
            user = db.query(User).filter(User.clerk_id == clerk_id).first()
            if not user:
                user = User(clerk_id=clerk_id, google_id=clerk_id, email=email, name=name)
                db.add(user)
            else:
                if user.email != email:
                    user.email = email
                if user.name != name:
                    user.name = name
            db.commit()
        finally:
            db.close()
    except Exception as e:
        logger.debug("User upsert failed (non-fatal): %s", e)


def _extract_email_from_addresses(addresses) -> str | None:
    """Extract first email from Clerk email_addresses array, if present."""
    if not addresses or not isinstance(addresses, list):
        return None
    for addr in addresses:
        if isinstance(addr, dict) and addr.get("email_address"):
            return addr["email_address"]
        if isinstance(addr, str):
            return addr
    return None
