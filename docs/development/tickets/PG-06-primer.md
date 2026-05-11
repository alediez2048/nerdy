# PG-06 Primer: Data Migration — Reassign test-user Data

**For:** New Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** April 2026
**Previous work:** P0-P5, PA-PD complete. PG-01 and PG-05 must be done first.

---

## What Is This Ticket?

All existing sessions, campaigns, curated sets, and share tokens are owned by `user_id: "test-user"` (the mock auth default). After enabling Clerk JWT validation, the admin user's real Clerk ID will be something like `user_2x...`. Existing data needs to be reassigned so it doesn't become inaccessible.

### Why It Matters
- After PG-01, the admin user authenticates as their real Clerk ID
- All existing data is owned by `"test-user"` — queries filtered by real Clerk ID return empty results
- 14+ sessions and 1+ campaigns with 41 published ads would be lost

---

## What This Ticket Must Accomplish

### Goal
Reassign all `"test-user"` data to the real admin Clerk user ID, and provide a reusable migration script.

### Deliverables Checklist

#### A. Implementation

- [ ] **Create migration script** `scripts/migrate_user_data.py`:
  ```python
  """Reassign all data from one user_id to another."""
  import argparse
  from app.db import SessionLocal
  from app.models.session import Session
  from app.models.campaign import Campaign
  from app.models.share_token import ShareToken

  def migrate(old_user_id: str, new_user_id: str, dry_run: bool = True):
      db = SessionLocal()
      sessions = db.query(Session).filter(Session.user_id == old_user_id).all()
      campaigns = db.query(Campaign).filter(Campaign.user_id == old_user_id).all()
      tokens = db.query(ShareToken).filter(ShareToken.created_by == old_user_id).all()

      print(f"Sessions to migrate: {len(sessions)}")
      print(f"Campaigns to migrate: {len(campaigns)}")
      print(f"Share tokens to migrate: {len(tokens)}")

      if dry_run:
          print("DRY RUN — no changes made")
          return

      for s in sessions:
          s.user_id = new_user_id
      for c in campaigns:
          c.user_id = new_user_id
      for t in tokens:
          t.created_by = new_user_id

      db.commit()
      print(f"Migrated all data from '{old_user_id}' to '{new_user_id}'")
  ```

- [ ] **Document the migration process** in the script's docstring:
  1. Log into the frontend with Clerk
  2. Hit `GET /api/auth/me` to get your Clerk user ID
  3. Run: `python scripts/migrate_user_data.py --from test-user --to user_2x... --execute`
  4. Verify: refresh the frontend, confirm campaigns/sessions appear

- [ ] **Add backup step**: before migration, dump the relevant tables:
  ```bash
  pg_dump -h localhost -p 5433 -U postgres -t sessions -t campaigns -t share_tokens nerdy > pre_migration_backup.sql
  ```

- [ ] **Handle edge cases:**
  - Multiple admin users (each gets their own data — can't auto-assign)
  - Sessions with no user_id (NULL) — assign to admin or leave
  - CuratedSets/CuratedAds don't have user_id — they're scoped via session FK, so they migrate automatically

#### B. Testing

- [ ] Dry run shows correct counts
- [ ] After migration, `GET /api/campaigns` returns previously created campaigns
- [ ] After migration, `GET /api/sessions` returns previously created sessions
- [ ] Rollback works by restoring from backup

---

## Key Files

| File | Action |
|------|--------|
| `scripts/migrate_user_data.py` | New — migration script |

---

## Notes

- This is a one-time migration for the initial deployment. Future users will have proper Clerk IDs from the start.
- The script should be idempotent — running it twice with the same args should be safe (no rows match `old_user_id` on second run).
- Consider adding a `--list` flag to show all distinct user_ids in the database for discovery.
