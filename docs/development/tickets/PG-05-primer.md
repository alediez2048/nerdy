# PG-05 Primer: User Model Updates and FK Constraints

**For:** New Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** April 2026
**Previous work:** P0-P5, PA-PD complete. PG-01 must be done first.

---

## What Is This Ticket?

The `User` model was designed for Google OAuth and lacks a `clerk_id` field. The `user_id` columns on `sessions`, `campaigns`, and `share_tokens` are loose strings with no foreign key constraints. This ticket adds Clerk identity to the User model and enforces referential integrity.

### Current State
- `users` table: `id` (int PK), `google_id`, `email`, `name`, `picture_url`
- `sessions.user_id`: `str(256)`, indexed, **no FK**
- `campaigns.user_id`: `str(256)`, indexed, **no FK**
- `share_tokens.created_by`: `str(256)`, **no FK**
- Comment in `session.py` line 19: "String user_id for dev (mock auth). PA-03 adds FK to users.id."

### Why It Matters
- Without FK constraints, orphaned records can exist (sessions belonging to deleted users)
- The User model has no way to store Clerk identity
- `user_id` columns store different formats depending on auth path (int from Google OAuth, string from mock, Clerk ID from Clerk)

---

## What This Ticket Must Accomplish

### Goal
Update the User model for Clerk, add FK constraints, and standardize user_id format.

### Deliverables Checklist

#### A. Implementation

- [ ] **Update `app/models/user.py`:**
  - Add `clerk_id: str(256)` column — UNIQUE, INDEXED, NULLABLE (for migration period)
  - Keep `google_id` for backward compatibility (existing users)
  - The canonical user_id used across the app becomes the Clerk `sub` value

- [ ] **Create Alembic migration** (or update `_repair_schema` pattern):
  - Add `clerk_id` column to `users` table
  - Add FK constraint: `sessions.user_id → users.clerk_id`
  - Add FK constraint: `campaigns.user_id → users.clerk_id`
  - Add FK constraint: `share_tokens.created_by → users.clerk_id`
  - These FKs should be added with `ON DELETE CASCADE` or `SET NULL` depending on desired behavior

- [ ] **Auto-create User on first auth** in `deps.py` or a middleware:
  - When Clerk JWT is validated and no User exists with that `clerk_id`, create one
  - Extract `email`, `name`, and optionally `image_url` from Clerk JWT claims
  - This replaces the need for a separate `/auth/google` login flow

- [ ] **Update `app/api/routes/auth.py`:**
  - `GET /me` should look up User by `clerk_id` and return full profile
  - `POST /google` can be deprecated or kept as legacy

#### B. Testing

- [ ] Verify new user is auto-created on first Clerk JWT validation
- [ ] Verify FK constraints prevent orphaned sessions/campaigns
- [ ] Verify `GET /auth/me` returns correct user profile from Clerk identity

---

## Key Files

| File | Action |
|------|--------|
| `app/models/user.py` | Add `clerk_id` column |
| `app/db.py` | Add migration/repair for new column + FKs |
| `app/api/deps.py` | Auto-create User on first auth |
| `app/api/routes/auth.py` | Update `/me`, deprecate `/google` |

---

## Notes

- FK constraints should be added carefully — existing data may reference user_ids that don't exist in the users table. PG-06 (data migration) handles this.
- Consider adding the FK constraints as DEFERRED or adding them after PG-06 migration completes.
- Clerk JWTs may not always contain `email` in the `sub` claim — the email is typically in a separate claim. Check Clerk's JWT structure for your app.
