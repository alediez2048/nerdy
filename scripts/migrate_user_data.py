"""PG-06: Reassign all data from one user_id to another.

Usage:
    # Dry run (default) — shows what would change
    python scripts/migrate_user_data.py --from test-user --to user_2x...

    # Execute the migration
    python scripts/migrate_user_data.py --from test-user --to user_2x... --execute

    # List all distinct user_ids in the database
    python scripts/migrate_user_data.py --list

Steps:
    1. Log into the frontend with Clerk
    2. Hit GET /api/auth/me to find your Clerk user ID (the "user_id" field)
    3. Run this script with --from test-user --to <your-clerk-id> --execute
    4. Refresh the frontend — your campaigns and sessions should appear
"""

import argparse
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db import SessionLocal, init_db
from app.models.campaign import Campaign
from app.models.session import Session
from app.models.share_token import ShareToken


def list_user_ids():
    """Show all distinct user_ids across sessions and campaigns."""
    init_db()
    db = SessionLocal()
    try:
        session_users = {r[0] for r in db.query(Session.user_id).distinct().all() if r[0]}
        campaign_users = {r[0] for r in db.query(Campaign.user_id).distinct().all() if r[0]}
        all_users = session_users | campaign_users

        print(f"\nDistinct user_ids found ({len(all_users)}):\n")
        for uid in sorted(all_users):
            s_count = db.query(Session).filter(Session.user_id == uid).count()
            c_count = db.query(Campaign).filter(Campaign.user_id == uid).count()
            print(f"  {uid:40s}  sessions={s_count}  campaigns={c_count}")
        print()
    finally:
        db.close()


def migrate(old_user_id: str, new_user_id: str, dry_run: bool = True):
    """Reassign all data from old_user_id to new_user_id."""
    init_db()
    db = SessionLocal()
    try:
        sessions = db.query(Session).filter(Session.user_id == old_user_id).all()
        campaigns = db.query(Campaign).filter(Campaign.user_id == old_user_id).all()
        tokens = db.query(ShareToken).filter(ShareToken.created_by == old_user_id).all()

        print(f"\nMigration: '{old_user_id}' → '{new_user_id}'")
        print(f"  Sessions to migrate:    {len(sessions)}")
        print(f"  Campaigns to migrate:   {len(campaigns)}")
        print(f"  Share tokens to migrate: {len(tokens)}")

        if not sessions and not campaigns and not tokens:
            print(f"\n  No data found for user_id '{old_user_id}'. Nothing to do.")
            return

        if dry_run:
            print("\n  DRY RUN — no changes made. Use --execute to apply.\n")
            return

        for s in sessions:
            s.user_id = new_user_id
        for c in campaigns:
            c.user_id = new_user_id
        for t in tokens:
            t.created_by = new_user_id

        db.commit()
        total = len(sessions) + len(campaigns) + len(tokens)
        print(f"\n  ✓ Migrated {total} records from '{old_user_id}' to '{new_user_id}'.\n")
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="Reassign user data between user_ids")
    parser.add_argument("--list", action="store_true", help="List all distinct user_ids")
    parser.add_argument("--from", dest="from_user", help="Source user_id to migrate from")
    parser.add_argument("--to", dest="to_user", help="Target user_id to migrate to")
    parser.add_argument("--execute", action="store_true", help="Actually apply changes (default is dry run)")

    args = parser.parse_args()

    if args.list:
        list_user_ids()
        return

    if not args.from_user or not args.to_user:
        parser.error("--from and --to are required (or use --list)")

    if args.from_user == args.to_user:
        parser.error("--from and --to must be different")

    migrate(args.from_user, args.to_user, dry_run=not args.execute)


if __name__ == "__main__":
    main()
