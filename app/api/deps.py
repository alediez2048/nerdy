# Ad-Ops-Autopilot — API dependencies (PA-03 mock auth)
from fastapi import Header

# Mock user for dev — real auth in PA-03
MOCK_USER_ID = "test-user"


def get_current_user(x_user_id: str | None = Header(default=None)) -> dict[str, str]:
    """Return current user. In dev: use X-User-Id header or fallback to mock."""
    user_id = x_user_id or MOCK_USER_ID
    return {"user_id": user_id}
