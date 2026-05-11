# PG-08 Primer: End-to-End Multi-Tenancy Verification

**For:** New Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** April 2026
**Previous work:** P0-P5, PA-PD complete. PG-01 through PG-07 must be done first.

---

## What Is This Ticket?

After implementing per-user isolation across the stack, this ticket verifies the entire system works end-to-end with multiple users. It's a structured test plan, not new feature work.

### Why It Matters
- Individual tickets may pass their own tests but miss cross-cutting issues
- Multi-tenancy bugs are subtle — a missing filter in one query can leak data silently
- This is the gate before the feature can be considered shipped

---

## What This Ticket Must Accomplish

### Goal
Verify complete per-user data isolation with two distinct Clerk users.

### Test Plan

#### Setup
- [ ] Two Clerk test accounts (User A and User B) with different emails
- [ ] Clean database state (or known baseline)
- [ ] Both frontend and API running with Clerk auth enabled (DEV_MODE=false)

#### Test Matrix

| # | Action | As User | Expected Result |
|---|--------|---------|-----------------|
| 1 | Create campaign "Alpha" | A | Campaign created, owned by A |
| 2 | List campaigns | A | Shows "Alpha" |
| 3 | List campaigns | B | Empty (no campaigns) |
| 4 | Create campaign "Beta" | B | Campaign created, owned by B |
| 5 | List campaigns | B | Shows "Beta" only |
| 6 | Create session in "Alpha" | A | Session created under Alpha |
| 7 | List sessions | A | Shows session from step 6 |
| 8 | List sessions | B | Empty |
| 9 | Run pipeline on A's session | A | Pipeline runs, produces ads |
| 10 | View A's session detail | B | 404 (not found) |
| 11 | View A's session ledger | B | 404 (not found) |
| 12 | Stream A's session progress | B | 403 (forbidden) |
| 13 | Access A's generated images | B | 404 (not found) |
| 14 | View global dashboard | A | Shows only A's metrics |
| 15 | View global dashboard | B | Shows only B's metrics (or empty) |
| 16 | Create share link for A's session | A | Share token created |
| 17 | Access shared session via token | B | Read-only access works |
| 18 | Access shared session images via token | B | Images accessible |
| 19 | Curate ads in A's session | B | 404 (not owner) |
| 20 | Upload competitive ads | Unauth | 401 (no auth) |

#### Cross-Cutting Checks

- [ ] **Redis isolation:** Verify progress events are only received by session owner
- [ ] **Celery tasks:** Verify worker stores correct user_id in session results
- [ ] **Database FKs:** Verify deleting a user cascades correctly (or blocks if data exists)
- [ ] **Browser DevTools:** Check no cross-user data leaks in network responses
- [ ] **Error messages:** Verify 401/403/404 responses don't leak information (no "session belongs to user_2x...")

#### Performance Check

- [ ] Auth overhead: measure request latency before/after Clerk JWT validation
- [ ] JWKS caching: verify keys are cached (not fetched on every request)

---

## Deliverables

- [ ] Test report documenting pass/fail for each test case
- [ ] Any bugs found filed as follow-up tickets
- [ ] Sign-off that multi-tenancy is working correctly

---

## Key Files

No code changes expected — this is a verification ticket. If bugs are found, they become separate fix tickets.

---

## Notes

- Use browser incognito windows or different browsers to test as two users simultaneously.
- Check the Docker API logs (`docker logs nerdy-api-1`) for any 500 errors during testing.
- If using Clerk development keys, both test accounts must be in the same Clerk development instance.
