# PA-02 Primer: Database Schema — Users & Sessions

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** PA-01 (FastAPI scaffold) must be complete. See `docs/DEVLOG.md`.

---

## What Is This Ticket?

PA-02 defines the **PostgreSQL database schema** for the application layer: users (Google SSO), sessions (one pipeline run = one session), and curated sets (per-session curation state). This is the data model that every subsequent PA ticket reads from and writes to.

### Why It Matters

- **State Is Sacred** (Pillar 5): Sessions are immutable records of pipeline runs — once created, config never changes
- **The Tool Is the Product** (Pillar 9): Multi-user session management requires proper data isolation (R5-Q5)
- The session model is one of the PRD's five load-bearing components (Section 4.7.2)
- Per-user isolation ensures users see only their own sessions
- Every API endpoint in PA-04 depends on these models being correct

---

## What Was Already Done

- PA-01: FastAPI scaffold with SQLAlchemy base, Alembic, Docker Compose
- PRD Section 4.7.2 defines the session model structure
- PRD Section 4.7 specifies immutable sessions and Google SSO fields

---

## What This Ticket Must Accomplish

### Goal

Create PostgreSQL tables for users, sessions, and curated_sets. Generate Alembic migrations. Schema must match the PRD's Section 4.7.2 session model.

### Deliverables Checklist

#### A. Users Model (`app/models/user.py`)

- [ ] `id` — UUID primary key
- [ ] `email` — unique, indexed (Google SSO email, must be @nerdy.com)
- [ ] `name` — display name from Google profile
- [ ] `picture_url` — Google profile avatar URL
- [ ] `google_id` — unique Google OAuth subject identifier
- [ ] `created_at` — timestamp with timezone
- [ ] `last_login_at` — timestamp with timezone, updated on each login

#### B. Sessions Model (`app/models/session.py`)

- [ ] `id` — UUID primary key
- [ ] `user_id` — foreign key to users, indexed
- [ ] `name` — user-provided or auto-generated session name
- [ ] `status` — enum: `pending`, `running`, `completed`, `failed`, `cancelled`
- [ ] `config` — JSONB column storing the full brief configuration:
  - `audience` (required): target audience segment
  - `campaign_goal` (required): awareness or conversion
  - `ad_count` (required): number of ads to generate
  - `threshold` (optional): quality threshold override
  - `weights` (optional): dimension weight overrides
  - `model_tier` (optional): flash or pro
  - `budget_cap` (optional): max token spend
  - `image_settings` (optional): image generation config
- [ ] `results_summary` — JSONB column storing aggregated results:
  - `total_generated`, `total_published`, `avg_score`, `avg_visual_score`
  - `cost_total`, `cost_per_ad`
  - `cycle_count`, `quality_trend` (array of per-cycle averages)
- [ ] `celery_task_id` — string, nullable (for tracking/cancelling the background job)
- [ ] `ledger_path` — string (path to this session's JSONL ledger file)
- [ ] `created_at` — timestamp with timezone
- [ ] `updated_at` — timestamp with timezone, auto-updated
- [ ] `completed_at` — timestamp with timezone, nullable

#### C. Curated Sets Model (`app/models/curated_set.py`)

- [ ] `id` — UUID primary key
- [ ] `session_id` — foreign key to sessions, unique (one curated set per session)
- [ ] `selections` — JSONB array of selected ad_ids with order
- [ ] `annotations` — JSONB map of ad_id → annotation text
- [ ] `edits` — JSONB map of ad_id → `{original: ..., edited: ..., diff: ...}`
- [ ] `created_at` — timestamp with timezone
- [ ] `updated_at` — timestamp with timezone, auto-updated

#### D. Alembic Migration

- [ ] Generate migration from models: `alembic revision --autogenerate -m "create users sessions curated_sets"`
- [ ] Verify migration runs cleanly: `alembic upgrade head`
- [ ] Verify downgrade works: `alembic downgrade -1`
- [ ] Status enum created as PostgreSQL enum type

#### E. Tests (`tests/test_app/test_models.py`)

- [ ] TDD first
- [ ] Test user creation with all fields
- [ ] Test session creation with config JSONB
- [ ] Test session belongs to user (foreign key)
- [ ] Test curated_set belongs to session (foreign key, unique constraint)
- [ ] Test status enum values accepted
- [ ] Test invalid status rejected
- [ ] Test results_summary JSONB stores and retrieves correctly
- [ ] Minimum: 7+ tests

#### F. Documentation

- [ ] Add PA-02 entry in `docs/DEVLOG.md`

---

## Branch & Merge Workflow

```bash
git switch main && git pull
git switch -c feature/PA-02-db-schema
```

---

## Important Context

### Architectural Decisions

| Decision | Reference | Summary |
|----------|-----------|---------|
| Session = immutable pipeline run | R5-Q1 | One session = one pipeline execution. Config is frozen at creation. Results accumulate. |
| Per-user isolation | R5-Q5 | Users see only their own sessions. Foreign key + query filter enforced. |
| JSONB for config + results | Section 4.7.2 | Flexible schema for brief config and aggregated results without rigid columns. |
| Curation separation | R5-Q6 | Curated set is a separate table — dashboard metrics always read from immutable session data. |

### Files to Create

| File | Why |
|------|-----|
| `app/models/user.py` | User model (Google SSO fields) |
| `app/models/session.py` | Session model (config, status, results) |
| `app/models/curated_set.py` | Curated set model (selections, annotations, edits) |
| `alembic/versions/xxxx_create_users_sessions_curated_sets.py` | Migration |
| `tests/test_app/test_models.py` | Model tests |

### Files You Should READ for Context

| File | Why |
|------|-----|
| `app/models/base.py` | SQLAlchemy base from PA-01 |
| `docs/reference/prd.md` (Section 4.7) | Application layer architecture, session model spec |
| `alembic.ini` | Alembic configuration from PA-01 |

---

## Definition of Done

- [ ] Migrations run cleanly (`alembic upgrade head`)
- [ ] Schema matches Section 4.7.2 session model
- [ ] All three tables created with correct columns and types
- [ ] Foreign keys and constraints enforced
- [ ] JSONB columns store and retrieve correctly
- [ ] Tests pass
- [ ] Lint clean
- [ ] DEVLOG updated
- [ ] Feature branch pushed

---

## Estimated Time: 30–45 minutes

---

## After This Ticket: What Comes Next

**PA-03 (Google SSO authentication)** implements Google OAuth 2.0 login using the users table from this ticket. It depends on the user model and database being ready.
