# PA-11 Primer: Share Session Link

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** PA-09 (session detail dashboard), PA-03 (Google SSO auth) must be complete. See `docs/DEVLOG.md`.

---

## What Is This Ticket?

PA-11 implements **shareable read-only session links**. Users can generate a time-limited URL for any session that grants read-only access to the session dashboard without requiring authentication. Shared viewers see the full dashboard (all tabs including the curated set) but cannot modify curation, start new sessions, or access other sessions.

### Why It Matters

- **The Reviewer Is a User, Too** (Pillar 8): Stakeholders, managers, and clients need to see results without creating accounts or navigating the full application
- Frictionless sharing accelerates review cycles — one link, no login required
- Time-limited tokens (7-day expiry) balance convenience with security
- Read-only mode prevents accidental modifications by non-owners

---

## What Was Already Done

- PA-03: Google SSO authentication with JWT session tokens and @nerdy.com domain restriction
- PA-09: Session detail page with 5-tab dashboard (+ PA-10 curated set tab)
- PA-04: Session CRUD API with per-user session isolation

---

## What This Ticket Must Accomplish

### Goal

Enable authenticated users to generate a read-only shareable URL for any session they own, with a 7-day time-limited token that grants unauthenticated dashboard access.

### Deliverables Checklist

#### A. Share Token Model (`app/models/share_token.py`)

- [ ] `ShareToken` model:
  - `id` (UUID primary key)
  - `session_id` (FK to sessions)
  - `token` (unique, URL-safe string — use `secrets.token_urlsafe(32)`)
  - `created_by` (FK to users — the session owner)
  - `expires_at` (DateTime — 7 days from creation)
  - `created_at` (DateTime)
  - `revoked` (Boolean, default False)
- [ ] Database migration

#### B. Share API (`app/api/routes/share.py`)

- [ ] `POST /sessions/{sessionId}/share` — generates a share token (auth required, must own session)
  - Returns `{ token, url, expires_at }`
  - URL format: `{base_url}/shared/{token}`
  - If active (non-expired, non-revoked) token already exists, return existing one
- [ ] `DELETE /sessions/{sessionId}/share` — revokes active share token (auth required, must own session)
  - Sets `revoked = True` on active token
- [ ] `GET /shared/{token}` — validates token and returns session dashboard data
  - Returns 404 if token doesn't exist
  - Returns 410 (Gone) if token is expired or revoked
  - Returns session detail + dashboard data (same as `GET /sessions/{sessionId}/dashboard`)
  - No authentication required

#### C. Share Token Middleware (`app/middleware/share_auth.py`)

- [ ] Middleware or dependency that checks for share token in shared routes
- [ ] Shared routes bypass normal JWT authentication
- [ ] Shared context is read-only — any mutation endpoint returns 403 if accessed via share token
- [ ] Share token grants access to exactly one session — no enumeration of other sessions

#### D. Frontend — Share Button (`frontend/src/components/ShareButton.tsx`)

- [ ] "Share" button on session detail page header (visible only to session owner)
- [ ] Click generates share link via `POST /sessions/{sessionId}/share`
- [ ] Copy-to-clipboard with success toast
- [ ] Shows expiry date: "Link expires on {date}"
- [ ] "Revoke Link" button if active share token exists
- [ ] Confirmation dialog before revoking

#### E. Frontend — Shared View (`frontend/src/pages/SharedSession.tsx`)

- [ ] Route: `/shared/{token}`
- [ ] No login required — no auth header sent
- [ ] Renders session detail + dashboard (same layout as PA-09)
- [ ] Read-only indicators:
  - No "New Session" button in nav
  - No session list access
  - Curated Set tab visible but all controls disabled (no select, reorder, edit, export)
  - No "Share" button
  - Banner: "You're viewing a shared session — read-only access"
- [ ] Expired/revoked token: show "This link has expired" page with prompt to request a new one

#### F. Tests (`tests/test_app/test_share.py`)

- [ ] TDD first
- [ ] Test token generation returns valid URL and 7-day expiry
- [ ] Test duplicate generation returns existing active token
- [ ] Test token validation succeeds for valid, non-expired token
- [ ] Test expired token returns 410
- [ ] Test revoked token returns 410
- [ ] Test nonexistent token returns 404
- [ ] Test shared route returns session dashboard data
- [ ] Test shared route blocks mutation endpoints (403)
- [ ] Test only session owner can generate share tokens
- [ ] Test token grants access to exactly one session (no enumeration)
- [ ] Minimum: 10+ tests

#### G. Documentation

- [ ] Add PA-11 entry in `docs/DEVLOG.md`

---

## Branch & Merge Workflow

```bash
git switch main && git pull
git switch -c feature/PA-11-share-session
```

---

## Important Context

### Architectural Decisions

| Decision | Reference | Summary |
|----------|-----------|---------|
| Shareable links | R5-Q5 | Read-only URL with time-limited token; no auth required for viewers; 7-day expiry |
| Per-user isolation | R5-Q5 | Share tokens are scoped to exactly one session; no access to other sessions or user data |
| Confidence-gated autonomy | R2-Q5 | Read-only sharing is the lowest autonomy tier — viewers can observe but not modify |

### Files to Create

| File | Why |
|------|-----|
| `app/models/share_token.py` | ShareToken data model |
| `app/api/routes/share.py` | Share token CRUD + shared access endpoints |
| `app/middleware/share_auth.py` | Share token authentication middleware |
| `frontend/src/components/ShareButton.tsx` | Share link generation UI |
| `frontend/src/pages/SharedSession.tsx` | Read-only shared session view |
| `tests/test_app/test_share.py` | Share feature tests |

### Files to Modify

| File | Action |
|------|--------|
| `frontend/src/App.tsx` | Add `/shared/:token` route |
| `frontend/src/pages/SessionDetail.tsx` | Add Share button to header |
| `app/api/main.py` | Register share router |
| `docs/DEVLOG.md` | Add ticket entry |

### Files You Should NOT Modify

- Authentication middleware (PA-03) — share tokens bypass auth, not replace it
- Session CRUD endpoints — shared access uses its own route, not the authenticated one
- Dashboard components — they render the same in shared and authenticated contexts

### Files You Should READ for Context

| File | Why |
|------|-----|
| PA-03 primer | Authentication system — share tokens must coexist with JWT auth |
| PA-09 primer | Session detail page structure |
| PA-10 primer | Curated Set tab — must be read-only in shared view |
| `interviews.md` (R5-Q5) | Full rationale for sharing and access control |

---

## Suggested Implementation Pattern

```python
# app/api/routes/share.py
@router.post("/sessions/{session_id}/share")
async def create_share_link(session_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    session = db.query(PipelineSession).get(session_id)
    if not session or session.user_id != user.id:
        raise HTTPException(403)

    # Return existing active token if one exists
    existing = db.query(ShareToken).filter(
        ShareToken.session_id == session_id,
        ShareToken.revoked == False,
        ShareToken.expires_at > datetime.utcnow()
    ).first()
    if existing:
        return {"token": existing.token, "url": f"{settings.BASE_URL}/shared/{existing.token}", "expires_at": existing.expires_at}

    token = ShareToken(
        session_id=session_id,
        token=secrets.token_urlsafe(32),
        created_by=user.id,
        expires_at=datetime.utcnow() + timedelta(days=7)
    )
    db.add(token)
    db.commit()
    return {"token": token.token, "url": f"{settings.BASE_URL}/shared/{token.token}", "expires_at": token.expires_at}


@router.get("/shared/{token}")
async def get_shared_session(token: str, db: Session = Depends(get_db)):
    share = db.query(ShareToken).filter(ShareToken.token == token).first()
    if not share:
        raise HTTPException(404)
    if share.revoked or share.expires_at < datetime.utcnow():
        raise HTTPException(410, detail="This share link has expired")

    return await get_session_dashboard(share.session_id, db)
```

---

## Edge Cases to Handle

1. Session owner generates link, then deletes their account — token should be invalidated (cascade or check)
2. Token expires while viewer has the page open — next API call returns 410; frontend shows expiry notice
3. Multiple share links requested — return existing active token, don't create duplicates
4. Revoke then re-share — new token generated with fresh 7-day expiry
5. Shared viewer tries to access other sessions by guessing URLs — token is scoped; returns 403/404
6. Token in URL is case-sensitive — `token_urlsafe` generates URL-safe base64; preserve case in routing

---

## Definition of Done

- [ ] Shared link opens session detail in read-only mode
- [ ] No authentication required for shared viewers
- [ ] Token expires after 7 days
- [ ] Expired/revoked tokens show appropriate error page
- [ ] Read-only mode: no curation controls, no new sessions, no share button
- [ ] Session owner can generate and revoke share links
- [ ] Tests pass (`python -m pytest tests/ -v`)
- [ ] Lint clean (`ruff check . --fix`)
- [ ] DEVLOG updated
- [ ] Feature branch pushed

---

## Estimated Time

| Task | Estimate |
|------|----------|
| ShareToken model + migration | 15 min |
| Share API endpoints | 25 min |
| Share auth middleware | 15 min |
| ShareButton component | 15 min |
| SharedSession page (read-only view) | 25 min |
| Tests | 30 min |
| DEVLOG update | 5–10 min |

---

## After This Ticket: What Comes Next

**PA-12 (Docker Compose production deployment)** packages the entire application — FastAPI, React, PostgreSQL, Celery, Redis — into a production-ready Docker Compose setup with Nginx reverse proxy and auto-HTTPS. This is the final application layer ticket.
