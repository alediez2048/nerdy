# PG-01 Primer: Clerk JWT Validation in deps.py

**For:** New Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** April 2026
**Previous work:** P0-P5, PA-PD complete. See `docs/DEVLOG.md`.

---

## What Is This Ticket?

Replace the current `get_current_user()` auth dependency to validate **Clerk session JWTs** instead of the legacy Google OAuth / HS256 flow. This is the foundational ticket — every other PG ticket depends on it.

Currently, `app/api/deps.py` checks if `GOOGLE_CLIENT_ID` is set. Since it's empty, every request falls back to mock auth returning `user_id: "test-user"`. Meanwhile, the frontend sends real Clerk JWTs that the backend completely ignores.

### Why It Matters
- Without this, all users share the same data (sessions, campaigns, curated sets)
- The Clerk JWT contains the real user identity (`sub`, `email`, `name`) but it's never decoded
- This is the single point of change that enables per-user isolation across the entire app

---

## What Was Already Done

- Frontend Clerk integration is complete: `main.tsx` registers Clerk token getter, all API calls send `Authorization: Bearer <clerk-jwt>`
- `Session` and `Campaign` models already have `user_id: str(256)` columns with indexes
- All CRUD routes already call `Depends(get_current_user)` and filter by `user["user_id"]`
- The only problem is `get_current_user()` always returns `"test-user"`

---

## What This Ticket Must Accomplish

### Goal
Make `get_current_user()` decode Clerk JWTs and return the real user identity.

### Deliverables Checklist

#### A. Implementation

- [ ] **Install dependencies:** Add `PyJWT[crypto]` (or keep `python-jose[cryptography]`) to `requirements.txt`. Add `httpx` for JWKS fetching if not present.
- [ ] **Add Clerk config to `app/config.py`:**
  - `CLERK_PUBLISHABLE_KEY: str = ""` (from env)
  - `CLERK_JWKS_URL: str = ""` (derived from publishable key domain, or set explicitly)
  - `CLERK_ISSUER: str = ""` (Clerk issuer URL for JWT validation)
  - `DEV_MODE: bool = False` (explicit dev mode flag, replaces GOOGLE_CLIENT_ID check)
- [ ] **Add JWKS key caching module** (`app/api/clerk_jwks.py` or inline in deps):
  - Fetch Clerk's JWKS endpoint (e.g., `https://<clerk-domain>/.well-known/jwks.json`)
  - Cache keys in memory with 1-hour TTL
  - Provide `get_clerk_public_key(kid: str)` function
- [ ] **Rewrite `get_current_user()` in `app/api/deps.py`:**
  ```python
  def get_current_user(
      authorization: str | None = Header(default=None),
      x_user_id: str | None = Header(default=None),
  ) -> dict[str, str]:
      # Explicit DEV_MODE: mock auth
      if settings.DEV_MODE:
          user_id = x_user_id or MOCK_USER_ID
          return {"user_id": user_id, "email": f"{user_id}@dev.local", "name": user_id}

      # Production: require Bearer token
      if not authorization:
          raise HTTPException(status_code=401, detail="Authorization header required")

      scheme, _, token = authorization.partition(" ")
      if scheme.lower() != "bearer" or not token:
          raise HTTPException(status_code=401, detail="Invalid authorization scheme")

      try:
          # Decode Clerk JWT (RS256, validate against JWKS)
          header = jwt.get_unverified_header(token)
          key = get_clerk_public_key(header["kid"])
          payload = jwt.decode(token, key, algorithms=["RS256"], issuer=settings.CLERK_ISSUER)
      except Exception as e:
          raise HTTPException(status_code=401, detail=f"Invalid token: {e}")

      user_id = payload.get("sub")  # Clerk user ID: "user_2x..."
      email = payload.get("email", "")
      name = payload.get("name", "")

      if not user_id:
          raise HTTPException(status_code=401, detail="Invalid token payload")

      return {"user_id": user_id, "email": email, "name": name}
  ```
- [ ] **Upsert User record on auth** (optional, can defer to PG-05):
  - After validating JWT, check if User with `clerk_id == user_id` exists
  - If not, create one with email/name from token claims
- [ ] **Update `.env.example`** with new Clerk-related variables
- [ ] **Update Docker `docker-compose.yml`** to pass Clerk env vars to api and worker services

#### B. Testing

- [ ] Test with real Clerk JWT from browser — verify `user_id` is the Clerk `sub` (not `"test-user"`)
- [ ] Test `DEV_MODE=true` fallback — verify mock auth still works for local dev without Clerk
- [ ] Test expired/invalid JWT returns 401
- [ ] Test missing Authorization header returns 401 (when not in DEV_MODE)
- [ ] Verify existing CRUD endpoints still work (campaigns list, sessions list)

#### C. Verification

- [ ] `curl -H "Authorization: Bearer <clerk-jwt>" http://localhost:8000/api/auth/me` returns real Clerk user info
- [ ] `curl http://localhost:8000/api/campaigns` returns 401 (not mock data) when DEV_MODE is off
- [ ] Frontend campaign list loads with real user's data after login

---

## Key Files

| File | Action |
|------|--------|
| `app/api/deps.py` | Rewrite `get_current_user()` |
| `app/config.py` | Add Clerk settings, DEV_MODE flag |
| `app/api/clerk_jwks.py` | New — JWKS key fetching and caching |
| `requirements.txt` | Add/verify `PyJWT[crypto]`, `httpx` |
| `.env.example` | Add Clerk env vars |
| `docker-compose.yml` | Pass Clerk env vars to containers |

---

## Notes

- Clerk session tokens use **RS256** (asymmetric), not HS256. The JWKS endpoint provides the public keys.
- The Clerk `sub` claim format is `"user_2x..."` — this is a string, which already matches the `user_id: str(256)` column type.
- Clerk tokens may also contain `azp` (authorized party) which can be validated against `CLERK_PUBLISHABLE_KEY` for extra security.
- The frontend already sends `Authorization: Bearer <token>` on every request — no frontend changes needed for this ticket.
