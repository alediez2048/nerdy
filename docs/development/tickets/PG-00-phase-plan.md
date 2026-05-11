# PG Phase Plan: Per-User Isolation (Clerk Auth Refactor)

**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** April 2026
**Previous work:** P0-P5, PA, PB, PC, PD phases complete. See `docs/DEVLOG.md`.
**Branch:** `final-submission`

---

## Problem Statement

The application uses Clerk for frontend authentication but the backend ignores Clerk JWTs entirely. In dev mode (`GOOGLE_CLIENT_ID` empty), every request resolves to the same mock user `"test-user"`, meaning all users share the same campaigns, sessions, and data. The system has the right data model (user_id columns exist on sessions and campaigns) but the auth layer doesn't use real user identity.

Additionally, several endpoints have no auth at all (ledger, progress SSE, competitive upload), and static file serving for images/videos has no access control.

---

## Audit Findings

Four parallel audits identified these gaps:

### Critical (must fix)
1. **`deps.py` ignores Clerk JWTs** — always falls back to `"test-user"` in dev mode
2. **`GET /{session_id}/ledger`** — no auth, no user_id filter (anyone can read any ledger)
3. **`GET /{session_id}/progress`** — auth present but no session ownership check
4. **`POST /api/competitive/upload`** — no auth on file upload endpoint

### High (should fix)
5. **Static file serving** — `/api/images` and `/api/videos` served without per-user authorization
6. **Global dashboard** — `GET /api/dashboard/global` aggregates all users' data with no auth
7. **No FK constraints** — `user_id` columns on sessions/campaigns have no foreign key to users table
8. **Data migration** — existing data owned by `"test-user"` needs reassignment to real Clerk user IDs

### Medium (improve)
9. **Frontend missing user context** — no programmatic access to current user ID
10. **Campaign types missing user_id** — frontend types don't include user_id field
11. **Token expiry handling** — no frontend handling of expired Clerk sessions

---

## Tickets (8)

| Ticket | Title | Priority | Dependencies |
|--------|-------|----------|--------------|
| PG-01 | Clerk JWT validation in `deps.py` | Critical | None |
| PG-02 | Patch unprotected endpoints (ledger, progress, competitive) | Critical | PG-01 |
| PG-03 | Secure static file serving for images/videos | High | PG-01 |
| PG-04 | Scope global dashboard to authenticated user | High | PG-01 |
| PG-05 | Add FK constraints and User model updates | High | PG-01 |
| PG-06 | Data migration — reassign test-user data to real Clerk IDs | High | PG-01, PG-05 |
| PG-07 | Frontend user context and token expiry handling | Medium | PG-01 |
| PG-08 | End-to-end multi-tenancy verification | Medium | PG-01–PG-07 |

---

## Architecture Decisions

1. **Clerk JWT validation via JWKS** — decode Clerk session tokens using Clerk's public JWKS endpoint (RS256), not the current HS256 symmetric key. Use `PyJWT` + `cryptography` with JWKS caching.
2. **User ID = Clerk `sub` claim** — Clerk JWTs contain `sub: "user_2x..."` which becomes the canonical `user_id` stored in sessions/campaigns.
3. **Upsert User on first request** — when a Clerk JWT is validated, upsert a User record with the Clerk ID, email, and name from the token claims. No separate login endpoint needed.
4. **Dev mode preserved** — keep `X-User-Id` fallback but only when an explicit `DEV_MODE=true` env var is set, not based on `GOOGLE_CLIENT_ID` being empty.
5. **Static files served through auth middleware** — replace `StaticFiles` mount with route handlers that verify session ownership before serving images/videos.

---

## Risk Assessment

| Risk | Mitigation |
|------|-----------|
| Existing data becomes inaccessible after migration | PG-06 includes reassignment script + rollback plan |
| Clerk JWKS endpoint unavailable | Cache JWKS keys locally with TTL; fallback to last-known-good |
| Breaking change for current users | PG-01 maintains dev mode fallback behind explicit flag |
| Static file auth adds latency | Serve via authenticated route only for non-shared content; shared links bypass |
