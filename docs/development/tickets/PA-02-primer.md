# PA-02 Primer: Database Schema — Users & Sessions

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** PA-01 (FastAPI scaffold) is complete. See `docs/DEVLOG.md`.

---

## What Is This Ticket?

PA-02 defines the **PostgreSQL database schema** for the application layer: users, sessions, and curated sets. These three tables underpin every PA ticket that follows — authentication, session management, curation, and sharing.

### Why It Matters

- **State Is Sacred** (Pillar 5): Session data and curation state must be durable and well-structured
- The session model (PRD Section 4.7.2) is the application's core entity — one session = one pipeline run, immutable after completion
- PA-03 (Google SSO) requires the User model to exist
- PA-10 (curation) requires the CuratedSet/CuratedAd models to exist
- Proper schema design now prevents costly migrations later

---

## What Was Already Done

- PA-01: FastAPI scaffold with SQLAlchemy engine, `SessionLocal`, `init_db()`, and `Base`
- `app/models/session.py`: Session model exists with `id`, `session_id`, `user_id`, `config` (JSON), `status`, `celery_task_id`, `results_summary` (JSON), `created_at`
- `app/db.py`: `create_engine`, `sessionmaker`, `init_db()` using `Base.metadata.create_all()`
- No Alembic — currently using `create_all()` for speed

---

## What This Ticket Must Accomplish

### Goal

Complete the database schema by adding the User model, extending the Session model to match PRD Section 4.7.2, adding CuratedSet/CuratedAd models, and initializing Alembic for migrations.

### Deliverables Checklist

#### A. User Model (`app/models/user.py`)

- [ ] `User` SQLAlchemy model with:
  - `id` (integer, primary key)
  - `google_id` (string, unique, indexed) — from Google SSO
  - `email` (string, unique, indexed) — must be `@nerdy.com`
  - `name` (string) — display name from Google profile
  - `picture_url` (string, nullable) — Google profile picture
  - `last_login_at` (DateTime with timezone)
  - `created_at` (DateTime with timezone, server_default)
- [ ] Add relationship: User has many Sessions

#### B. Extend Session Model (`app/models/session.py`)

- [ ] Add missing fields from PRD Section 4.7.2:
  - `name` (string, nullable) — user-facing session name (e.g., "SAT Parents Conversion March")
  - `updated_at` (DateTime with timezone, onupdate)
  - `completed_at` (DateTime with timezone, nullable)
  - `ledger_path` (string, nullable) — path to session-scoped ledger
  - `output_path` (string, nullable) — path to session output directory
- [ ] Add foreign key: `user_id` references `users.id` (currently just a string)
- [ ] Ensure `config` JSON matches PRD schema: `product`, `audience`, `campaign_goal`, `ad_count`, `cycle_count`, `quality_threshold`, `dimension_weights`, `model_tier`, `budget_cap_usd`, `image_enabled`, `aspect_ratios`

#### C. CuratedSet and CuratedAd Models (`app/models/curation.py`)

- [ ] `CuratedSet` model:
  - `id` (integer, primary key)
  - `session_id` (foreign key to sessions)
  - `name` (string) — curated set name
  - `created_at`, `updated_at` (DateTime)
- [ ] `CuratedAd` model:
  - `id` (integer, primary key)
  - `curated_set_id` (foreign key to curated_sets)
  - `ad_id` (string) — references ad in the JSONL ledger
  - `position` (integer) — ordering within set
  - `annotation` (text, nullable) — user notes
  - `edited_copy` (JSON, nullable) — light edits with before/after
  - `created_at` (DateTime)

#### D. Alembic Initialization

- [ ] `alembic init app/alembic`
- [ ] Configure `alembic.ini` and `env.py` to use `app.config.settings.DATABASE_URL`
- [ ] Generate initial migration from existing models
- [ ] Verify `alembic upgrade head` creates all tables

#### E. Tests (`tests/test_app/test_models.py`)

- [ ] TDD first
- [ ] Test User model creation with all required fields
- [ ] Test Session model creation with extended fields
- [ ] Test User → Session relationship
- [ ] Test CuratedSet → CuratedAd relationship
- [ ] Test `@nerdy.com` email constraint (if enforced at model level)
- [ ] Minimum: 5+ tests

#### F. Documentation

- [ ] Add PA-02 entry in `docs/DEVLOG.md`

---

## Important Context

### Architectural Decisions

| Decision | Reference | Summary |
|----------|-----------|---------|
| Session = one pipeline run | R5-Q1, Section 4.7.2 | Immutable after completion. Config captures all parameters. |
| Per-user isolation | R5-Q5 | Every session belongs to a user. Users only see their own sessions. |
| Curation is mutable, generation is not | R5-Q6 | CuratedAd stores edits separately. Dashboard always shows original scores. |

### Files to Modify/Create

| File | Action |
|------|--------|
| `app/models/user.py` | Create — User model |
| `app/models/session.py` | Modify — extend with missing fields, add FK to users |
| `app/models/curation.py` | Create — CuratedSet + CuratedAd models |
| `app/db.py` | Modify — import all models so `create_all` picks them up |
| `tests/test_app/test_models.py` | Create — model tests |

### Files You Should READ for Context

| File | Why |
|------|-----|
| `docs/reference/prd.md` (Section 4.7.2) | Session model schema |
| `docs/reference/prd.md` (Section 4.7.7) | Curation layer design |
| `docs/reference/prd.md` (Section 4.7.8) | Auth & user model requirements |
| `app/models/session.py` | Existing Session model to extend |
| `app/db.py` | Current database setup |

---

## Definition of Done

- [ ] User, Session (extended), CuratedSet, CuratedAd models all defined
- [ ] Relationships: User → Sessions, Session → CuratedSets, CuratedSet → CuratedAds
- [ ] Alembic initialized with baseline migration
- [ ] `alembic upgrade head` creates all tables cleanly
- [ ] Tests pass
- [ ] Lint clean
- [ ] DEVLOG updated

---

## Estimated Time: 45–60 minutes

---

## After This Ticket: What Comes Next

**PA-03 (Google SSO Authentication)** uses the User model to create/lookup users on login. It depends on the User table and the email field for `@nerdy.com` domain restriction.
