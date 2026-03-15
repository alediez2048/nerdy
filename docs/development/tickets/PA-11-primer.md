# PA-11 Primer: Share Session Link

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** PA-09 (Dashboard Integration) must be complete. PA-03 (Auth) must be complete. See `docs/DEVLOG.md`.

---

## What Is This Ticket?

PA-11 implements **shareable session links** — read-only URLs with time-limited tokens so users can share session results with stakeholders without requiring them to log in (R5-Q5, Section 4.7.8).

### Why It Matters

- Stakeholders (managers, clients) need to review ad output without having `@nerdy.com` accounts
- Time-limited tokens (7-day expiry) prevent stale links from becoming security holes
- Read-only access ensures shared viewers can't modify curation or trigger new runs
- This is a common pattern for internal tools: share a link, get feedback

---

## What Was Already Done

- PA-03: JWT-based auth with `get_current_user()` dependency
- PA-09: Session detail page with 7-tab dashboard
- PA-04: Per-user session isolation

---

## What This Ticket Must Accomplish

### Goal

Add a "Share" button to sessions that generates a read-only, time-limited URL. Anyone with the link can view the session dashboard without logging in.

### Deliverables Checklist

#### A. Share Token Model (`app/models/share_token.py`)

- [ ] `ShareToken` SQLAlchemy model:
  - `id` (integer, primary key)
  - `token` (string, unique, indexed) — random URL-safe token
  - `session_id` (foreign key to sessions)
  - `created_by` (foreign key to users)
  - `expires_at` (DateTime with timezone) — 7 days from creation
  - `created_at` (DateTime with timezone)
  - `is_revoked` (boolean, default false)
- [ ] Add migration

#### B. Share API (`app/api/routes/share.py`)

- [ ] `POST /sessions/{session_id}/share` — generate share token
  - Only session owner can share (per-user isolation)
  - Returns `{ "share_url": "https://host/shared/{token}", "expires_at": "..." }`
  - If an active (non-expired, non-revoked) token already exists, return it instead of creating new
- [ ] `DELETE /sessions/{session_id}/share` — revoke share token
  - Sets `is_revoked = true`
  - Returns 204
- [ ] `GET /shared/{token}` — validate token, return session data
  - Check token exists, not expired, not revoked
  - Return session detail + dashboard data (same as PA-09 endpoints but no auth required)
  - Return 404 if token invalid/expired/revoked
- [ ] Register router in `app/api/main.py`

#### C. Shared Session Middleware

- [ ] Dashboard API endpoints must work in two modes:
  1. **Authenticated:** Normal JWT auth, per-user isolation
  2. **Shared:** Token-based, read-only, no auth required
- [ ] Add optional `share_token` query param to dashboard endpoints
- [ ] When `share_token` is present: validate token, skip JWT auth, return read-only data
- [ ] Shared access: all dashboard tabs visible, but no curation, no delete, no new session

#### D. Frontend — Share Button (`src/components/ShareButton.tsx`)

- [ ] Share button on session detail page (top right)
- [ ] On click: calls `POST /sessions/{session_id}/share`
- [ ] Shows modal with share URL + copy-to-clipboard button
- [ ] Shows expiry date
- [ ] "Revoke" button to invalidate the link

#### E. Frontend — Shared Session View (`src/views/SharedSession.tsx`)

- [ ] Route: `/shared/{token}`
- [ ] Fetches session data via `GET /shared/{token}`
- [ ] Renders same 7-tab dashboard as session detail
- [ ] No navigation to other sessions, no curation, no edit actions
- [ ] "Shared view" banner indicating read-only mode
- [ ] Expired/revoked token → error page with message

#### F. Tests (`tests/test_app/test_share.py`)

- [ ] TDD first
- [ ] Test create share token returns URL and expiry
- [ ] Test duplicate share returns existing token
- [ ] Test shared link returns session data without auth
- [ ] Test expired token returns 404
- [ ] Test revoked token returns 404
- [ ] Test only session owner can create share link
- [ ] Test shared view is read-only (no curation endpoints accessible)
- [ ] Minimum: 7+ tests

#### G. Documentation

- [ ] Add PA-11 entry in `docs/DEVLOG.md`

---

## Important Context

### Auth Spec (PRD Section 4.7.8)

> Share session via read-only time-limited link.

### Share Flow

```
Owner                        Backend                     Viewer
  │                             │                           │
  │  1. Click "Share"           │                           │
  │  ───────────────────>       │                           │
  │                             │  2. Generate token         │
  │  <───────────────────       │     (7-day expiry)        │
  │  3. Copy URL                │                           │
  │                             │                           │
  │  4. Send URL to viewer      │                           │
  │  ─────────────────────────────────────────────────>     │
  │                             │                           │
  │                             │  5. GET /shared/{token}   │
  │                             │  <───────────────────     │
  │                             │  6. Validate + return     │
  │                             │  ───────────────────>     │
  │                             │     session dashboard     │
```

### Architectural Decisions

| Decision | Reference | Summary |
|----------|-----------|---------|
| Time-limited tokens | R5-Q5 | 7-day expiry. No permanent links. |
| Read-only | R5-Q5 | Shared viewers cannot modify anything. |
| No auth required for shared | R5-Q5 | Token is the credential for shared views. |

### Files to Create

| File | Why |
|------|-----|
| `app/models/share_token.py` | ShareToken model |
| `app/api/routes/share.py` | Share API endpoints |
| `app/api/schemas/share.py` | Share Pydantic schemas |
| `src/components/ShareButton.tsx` | Share UI |
| `src/views/SharedSession.tsx` | Shared session view |
| `tests/test_app/test_share.py` | Share tests |

### Files You Should READ for Context

| File | Why |
|------|-----|
| `docs/reference/prd.md` (Section 4.7.8) | Auth + sharing spec |
| `app/api/routes/dashboard.py` | Dashboard endpoints to extend with share_token support |
| `app/api/deps.py` | Auth dependency to bypass for shared access |
| `src/views/SessionDetail.tsx` | Session detail page to add Share button |

---

## Definition of Done

- [ ] Share button generates time-limited URL (7-day expiry)
- [ ] Shared link opens read-only session dashboard without login
- [ ] Expired/revoked tokens return appropriate error
- [ ] Only session owner can create/revoke share links
- [ ] Shared view shows all dashboard tabs but no edit actions
- [ ] Tests pass
- [ ] Lint clean
- [ ] DEVLOG updated

---

## Estimated Time: 60–90 minutes

---

## After This Ticket: What Comes Next

**PA-12 (Docker Compose Production Deployment)** is the final ticket — it wraps everything in a production-ready Docker Compose setup with Nginx, HTTPS, and static React builds.
