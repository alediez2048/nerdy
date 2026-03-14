# PA-03 Primer: Google SSO Authentication

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** PA-01 (FastAPI scaffold), PA-02 (database schema) must be complete. See `docs/DEVLOG.md`.

---

## What Is This Ticket?

PA-03 implements **Google OAuth 2.0 authentication** with `@nerdy.com` domain restriction. Users sign in with their corporate Google account, receive a JWT session token, and can only access their own sessions.

### Why It Matters

- **The Tool Is the Product** (Pillar 9): An internal tool requires authentication — no anonymous access
- `@nerdy.com` domain lock ensures only Nerdy employees can access the system (R5-Q5)
- Per-user session isolation is a hard requirement — users must never see each other's data
- JWT tokens enable stateless API authentication without server-side session storage
- Every subsequent API endpoint depends on `get_current_user()` being available

---

## What Was Already Done

- PA-01: FastAPI scaffold with config (`GOOGLE_CLIENT_ID`, `SECRET_KEY` in `.env`)
- PA-02: Users table with `email`, `google_id`, `name`, `picture_url`, `last_login_at`
- Docker Compose running API + DB

---

## What This Ticket Must Accomplish

### Goal

Implement Google OAuth 2.0 login flow, domain-restricted to `@nerdy.com`, with JWT session tokens and a `get_current_user` dependency for per-user isolation.

### Deliverables Checklist

#### A. Auth Routes (`app/api/routes/auth.py`)

- [ ] `POST /auth/google` — accepts Google OAuth ID token from frontend
  - Verifies token with Google's public keys
  - Extracts email, name, picture, Google subject ID
  - Rejects non-`@nerdy.com` emails with 403 Forbidden
  - Creates user record on first login (upsert by `google_id`)
  - Updates `last_login_at` on every login
  - Returns JWT access token
- [ ] `GET /auth/me` — returns current user profile from JWT
- [ ] `POST /auth/logout` — client-side only (JWT is stateless), returns 200

#### B. JWT Token Management (`app/api/auth.py`)

- [ ] `create_access_token(user_id: str, email: str) -> str`
  - Signs JWT with `SECRET_KEY` from config
  - Includes `sub` (user_id), `email`, `exp` (expiration, default 24h)
- [ ] `get_current_user(token: str) -> User`
  - FastAPI dependency (uses `Depends` with `OAuth2PasswordBearer` or custom header scheme)
  - Decodes and validates JWT
  - Returns User model instance from database
  - Raises 401 Unauthorized on invalid/expired token
- [ ] Token expiration configurable via environment variable

#### C. Domain Restriction

- [ ] Validate email domain is exactly `@nerdy.com` (case-insensitive)
- [ ] Return clear error message: "Only @nerdy.com accounts can access this application"
- [ ] Log rejected login attempts (email + timestamp, NOT the token)

#### D. Per-User Isolation Pattern

- [ ] Document the pattern: every query that returns sessions must filter by `user_id = current_user.id`
- [ ] Create helper: `get_user_sessions_query(user: User) -> Query` that pre-filters
- [ ] This pattern will be enforced in PA-04 endpoints

#### E. Tests (`tests/test_app/test_auth.py`)

- [ ] TDD first
- [ ] Test valid @nerdy.com Google token → returns JWT + creates user
- [ ] Test non-@nerdy.com email → 403 Forbidden
- [ ] Test valid JWT → `get_current_user` returns correct user
- [ ] Test expired JWT → 401 Unauthorized
- [ ] Test invalid JWT → 401 Unauthorized
- [ ] Test repeat login updates `last_login_at` (upsert, not duplicate)
- [ ] Test `GET /auth/me` returns user profile
- [ ] Minimum: 7+ tests

#### F. Documentation

- [ ] Add PA-03 entry in `docs/DEVLOG.md`

---

## Branch & Merge Workflow

```bash
git switch main && git pull
git switch -c feature/PA-03-google-sso
```

---

## Important Context

### Architectural Decisions

| Decision | Reference | Summary |
|----------|-----------|---------|
| Google SSO only | R5-Q5 | No email/password auth. Google OAuth 2.0 with corporate domain restriction. |
| @nerdy.com lock | R5-Q5 | Domain-level access control. Only corporate accounts allowed. |
| JWT tokens | R5-Q5 | Stateless authentication. No server-side session store needed. |
| Per-user isolation | R5-Q5 | Every database query filters by authenticated user. No cross-user data leakage. |

### Files to Create

| File | Why |
|------|-----|
| `app/api/routes/auth.py` | Auth endpoints (Google login, me, logout) |
| `app/api/auth.py` | JWT creation, validation, get_current_user dependency |
| `tests/test_app/test_auth.py` | Auth tests |

### Files You Should READ for Context

| File | Why |
|------|-----|
| `app/models/user.py` | User model fields (PA-02) |
| `app/config.py` | Environment config with GOOGLE_CLIENT_ID, SECRET_KEY |
| `app/api/main.py` | FastAPI app to register auth routes |

---

## Definition of Done

- [ ] Only @nerdy.com emails can sign in
- [ ] Non-@nerdy.com emails receive 403 with clear message
- [ ] JWT token issued on successful login
- [ ] `get_current_user` dependency works for protected routes
- [ ] Users see only their own sessions (isolation pattern documented)
- [ ] First login creates user; repeat login updates `last_login_at`
- [ ] Tests pass
- [ ] Lint clean
- [ ] DEVLOG updated
- [ ] Feature branch pushed

---

## Estimated Time: 45–60 minutes

---

## After This Ticket: What Comes Next

**PA-04 (Session CRUD API)** builds the REST endpoints for creating, listing, and viewing sessions. It depends on `get_current_user` from this ticket for every protected endpoint.
