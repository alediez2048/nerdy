# PG-04 Primer: Scope Global Dashboard to Authenticated User

**For:** New Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** April 2026
**Previous work:** P0-P5, PA-PD complete. PG-01 must be done first.

---

## What Is This Ticket?

The global dashboard endpoint (`GET /api/dashboard/global`) currently aggregates data from ALL sessions across ALL users with no authentication. In a multi-tenant system, each user should only see dashboard metrics for their own sessions.

### Current Behavior
- `GET /api/dashboard/global` — no auth required, reads all `data/sessions/*/ledger.jsonl` files
- Aggregates KPIs (total ads, costs, quality scores) from every user's sessions
- Returns system-wide metrics exposed to anyone

### Desired Behavior
- Require authentication
- Filter to only the authenticated user's sessions
- Show per-user aggregate metrics (their campaigns, their sessions, their costs)

---

## What This Ticket Must Accomplish

### Goal
Make the global dashboard user-scoped while preserving the same response shape.

### Deliverables Checklist

#### A. Implementation

- [ ] **Add auth to `GET /api/dashboard/global`** in `app/api/routes/dashboard.py`:
  - Add `user: Annotated[dict, Depends(get_current_user)]` parameter
  - Filter sessions query by `SessionModel.user_id == user["user_id"]`

- [ ] **Update the competitive summary endpoint** (`GET /api/competitive/summary`):
  - Add `Depends(get_current_user)` — competitive data is shared but should require auth
  - The competitive patterns themselves are global (Meta Ad Library data), so no user filtering needed on the data — just gate access behind auth

- [ ] **Update frontend `GlobalDashboard.tsx`**:
  - Ensure API call includes auth headers (check if it already does)
  - Update any labels from "Global" to "My Dashboard" or "Dashboard"

#### B. Testing

- [ ] Verify dashboard returns 401 without auth
- [ ] Verify dashboard only shows metrics from the authenticated user's sessions
- [ ] Verify two different users see different dashboard data
- [ ] Verify competitive summary requires auth but shows same data to all users

---

## Key Files

| File | Action |
|------|--------|
| `app/api/routes/dashboard.py` | Add auth + user filtering to global endpoint |
| `app/frontend/src/views/GlobalDashboard.tsx` | Verify auth headers, update labels |

---

## Notes

- The global dashboard currently reads ledger files directly from disk (`data/sessions/*/ledger.jsonl`). After scoping to a user, it should query the DB for the user's sessions and only read those ledger files.
- Consider caching per-user dashboard data in Redis with a short TTL (30s) to avoid re-parsing ledger files on every request.
