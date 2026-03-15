# PA-03 Primer: Google SSO Authentication

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** PA-02 (database schema) must be complete — User model required. See `docs/DEVLOG.md`.

---

## What Is This Ticket?

PA-03 implements **Google OAuth 2.0 authentication** with `@nerdy.com` domain restriction and JWT tokens. This replaces the mock auth in `app/api/deps.py` and enables per-user session isolation across the entire application.

### Why It Matters

- **The Tool Is the Product** (Pillar 9): Internal tools need real auth — Nerdy employees sign in with their Google accounts
- Domain restriction (`@nerdy.com` only) is a hard security boundary (R5-Q5)
- Per-user isolation ensures users only see their own sessions
- Every subsequent PA ticket uses `get_current_user()` — getting auth right here means all routes are protected

---

## What Was Already Done

- PA-01: FastAPI scaffold with CORS, health check
- PA-02: User model with `google_id`, `email`, `name`, `picture_url`, `last_login_at`
- `app/api/deps.py`: Mock auth — `get_current_user()` reads `X-User-Id` header or returns `"test-user"`
- `app/config.py`: Pydantic Settings (needs `GOOGLE_CLIENT_ID`, `SECRET_KEY` added)

---

## What This Ticket Must Accomplish

### Goal

Implement Google SSO login flow, JWT token issuance, and replace the mock `get_current_user()` with real token validation. Only `@nerdy.com` emails allowed.

### Deliverables Checklist

#### A. Configuration (`app/config.py`)

- [ ] Add `GOOGLE_CLIENT_ID: str` — from Google Cloud Console
- [ ] Add `SECRET_KEY: str` — for JWT signing (HS256)
- [ ] Add `JWT_EXPIRY_HOURS: int = 24` — token lifetime
- [ ] Update `.env.example` with `GOOGLE_CLIENT_ID` and `SECRET_KEY` placeholders

#### B. Auth Routes (`app/api/routes/auth.py`)

- [ ] `POST /auth/google` — receives Google OAuth `id_token` from frontend
  - Verifies token with Google (`google.oauth2.id_token.verify_oauth2_token` or `google.auth.transport.requests`)
  - Extracts `email`, `name`, `picture`, `sub` (Google ID)
  - Rejects if email domain is not `@nerdy.com` (403)
  - Creates or updates User in database (upsert on `google_id`)
  - Updates `last_login_at`
  - Issues JWT containing `user_id`, `email`, `name`
  - Returns `{"access_token": "<jwt>", "token_type": "bearer", "user": {...}}`
- [ ] `GET /auth/me` — returns current user profile from JWT
- [ ] Register router in `app/api/main.py`

#### C. Auth Dependency (`app/api/deps.py`)

- [ ] Replace mock `get_current_user()` with real JWT validation:
  - Extract `Authorization: Bearer <token>` header
  - Decode and validate JWT (check expiry, signature)
  - Lookup user in database by `user_id` from token
  - Return user dict with `user_id`, `email`, `name`
  - Raise 401 if token missing, expired, or invalid
- [ ] Keep a `DEV_MODE` escape hatch: if `GOOGLE_CLIENT_ID` is empty, fall back to mock auth (for local dev without Google credentials)

#### D. Dependencies

- [ ] Add `google-auth>=2.0.0` to `app/requirements.txt` (already in main requirements)
- [ ] Add `python-jose[cryptography]>=3.3.0` to `app/requirements.txt` for JWT

#### E. Tests (`tests/test_app/test_auth.py`)

- [ ] TDD first
- [ ] Test `@nerdy.com` email accepted
- [ ] Test non-`@nerdy.com` email rejected with 403
- [ ] Test valid JWT returns user from `/auth/me`
- [ ] Test expired JWT returns 401
- [ ] Test missing Authorization header returns 401
- [ ] Test user created on first login (upsert)
- [ ] Test user updated on subsequent login (`last_login_at` changes)
- [ ] Test DEV_MODE fallback works when `GOOGLE_CLIENT_ID` is empty
- [ ] Minimum: 8+ tests

#### F. Documentation

- [ ] Add PA-03 entry in `docs/DEVLOG.md`

---

## Important Context

### Architectural Decisions

| Decision | Reference | Summary |
|----------|-----------|---------|
| Google SSO only | R5-Q5 | Single sign-on via Google. No username/password. |
| @nerdy.com restriction | R5-Q5 | Hard domain check. Reject all other domains. |
| JWT tokens | R5-Q5 | Stateless auth. No server-side session store. |
| Per-user isolation | R5-Q5 | Users see only their own sessions. Filter at query level. |

### Auth Flow

```
Frontend                    Backend                     Google
   │                           │                           │
   │  1. Google Sign-In        │                           │
   │  ─────────────────────>   │                           │
   │                           │  2. Verify id_token       │
   │                           │  ─────────────────────>   │
   │                           │  <─────────────────────   │
   │                           │  3. Check @nerdy.com      │
   │                           │  4. Upsert User           │
   │                           │  5. Issue JWT              │
   │  <─────────────────────   │                           │
   │  6. Store JWT in client   │                           │
   │                           │                           │
   │  7. API call + Bearer     │                           │
   │  ─────────────────────>   │                           │
   │                           │  8. Validate JWT           │
   │  <─────────────────────   │  9. Return data            │
```

### Files to Modify/Create

| File | Action |
|------|--------|
| `app/api/routes/auth.py` | Create — Google SSO + JWT endpoints |
| `app/api/deps.py` | Modify — replace mock with real JWT validation |
| `app/config.py` | Modify — add GOOGLE_CLIENT_ID, SECRET_KEY, JWT_EXPIRY_HOURS |
| `app/api/main.py` | Modify — register auth router |
| `app/requirements.txt` | Modify — add python-jose |
| `.env.example` | Modify — add GOOGLE_CLIENT_ID, SECRET_KEY |
| `tests/test_app/test_auth.py` | Create — auth tests |

### Files You Should READ for Context

| File | Why |
|------|-----|
| `docs/reference/prd.md` (Section 4.7.8) | Auth architecture spec |
| `app/api/deps.py` | Current mock auth to replace |
| `app/models/user.py` | User model fields (from PA-02) |
| `app/api/routes/sessions.py` | Uses `get_current_user` — must stay compatible |
| `app/api/routes/progress.py` | Uses `get_current_user` — must stay compatible |

---

## Definition of Done

- [ ] `POST /auth/google` accepts Google id_token, returns JWT
- [ ] Non-`@nerdy.com` emails rejected with 403
- [ ] `get_current_user()` validates JWT on all protected routes
- [ ] `GET /auth/me` returns current user profile
- [ ] DEV_MODE fallback for local development without Google credentials
- [ ] User upserted in database on login
- [ ] Tests pass
- [ ] Lint clean
- [ ] DEVLOG updated

---

## Estimated Time: 60–90 minutes

---

## After This Ticket: What Comes Next

**PA-04 (Session CRUD API)** needs to be updated to enforce per-user isolation — filtering sessions by the authenticated user's ID. The real `get_current_user()` from this ticket makes that possible.
