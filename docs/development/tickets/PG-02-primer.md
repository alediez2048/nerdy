# PG-02 Primer: Patch Unprotected Endpoints

**For:** New Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** April 2026
**Previous work:** P0-P5, PA-PD complete. PG-01 (Clerk JWT validation) must be done first.

---

## What Is This Ticket?

Three endpoints have critical auth/isolation gaps identified in the security audit. This ticket patches all three to require authentication and verify resource ownership.

### Endpoints to Fix

| Endpoint | File | Line | Issue |
|----------|------|------|-------|
| `GET /{session_id}/ledger` | `sessions.py` | 70-83 | No `Depends(get_current_user)`, no user_id filter |
| `GET /{session_id}/progress` | `progress.py` | 52-79 | Auth present but no session ownership check |
| `POST /api/competitive/upload` | `competitive.py` | 154 | No auth at all on file upload |

### Why It Matters
- **Ledger:** Any user (or unauthenticated request) can read any session's raw ledger data by guessing the session_id. This exposes ad copy, evaluation scores, API costs, and internal decision traces.
- **Progress SSE:** An authenticated user can subscribe to another user's real-time progress stream. While read-only, it leaks session status, ad counts, and score data.
- **Competitive upload:** Anyone can upload arbitrary files to the competitive data directory, potentially corrupting the pattern database or filling disk.

---

## What Was Already Done

- `sessions.py` already has a `_get_user_session(db, session_id, user_id)` helper (line 36-42) that validates ownership. The ledger endpoint just doesn't use it.
- `progress.py` already has `Depends(get_current_user)` in the signature but the DB query on line 76 doesn't filter by user_id.
- `competitive.py` has no auth patterns at all — needs `Depends(get_current_user)` added.

---

## What This Ticket Must Accomplish

### Goal
Add auth + ownership verification to all three endpoints.

### Deliverables Checklist

#### A. Implementation

- [ ] **Fix `GET /{session_id}/ledger`** in `app/api/routes/sessions.py`:
  - Add `user: Annotated[dict, Depends(get_current_user)]` to function signature
  - Replace raw session query with `_get_user_session(db, session_id, user["user_id"])`
  - This ensures only the session owner can read the ledger

- [ ] **Fix `GET /{session_id}/progress`** in `app/api/routes/progress.py`:
  - After line 76 session lookup, add ownership check: verify `row.user_id == _user["user_id"]`
  - Handle the EventSource query-param token path: decode the token to get user_id and validate ownership
  - Return 403 if user doesn't own the session

- [ ] **Fix `POST /api/competitive/upload`** in `app/api/routes/competitive.py`:
  - Add `user: Annotated[dict, Depends(get_current_user)]` to function signature
  - Log which user performed the upload for audit trail

#### B. Testing

- [ ] Test ledger endpoint returns 401 without auth, 404 for other user's session
- [ ] Test progress SSE returns 403 for non-owner session
- [ ] Test competitive upload returns 401 without auth, succeeds with auth
- [ ] Verify existing authenticated endpoints still work normally

---

## Key Files

| File | Action |
|------|--------|
| `app/api/routes/sessions.py` | Add auth to ledger endpoint (~line 70) |
| `app/api/routes/progress.py` | Add ownership check (~line 76) |
| `app/api/routes/competitive.py` | Add auth to upload endpoint (~line 154) |
