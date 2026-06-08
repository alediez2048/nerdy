# PJ-01 Primer

**Source plan:** [`PJ-00-phase-plan.md`](PJ-00-phase-plan.md) — §5 (Data model) and §13 (Ticket breakdown).
**For:** New Cursor Agent session
**Date:** 2026-06-08
**Previous work:** PI phase complete (final-submission); BYO API Keys feature shipped 2026-06-05. See `docs/development/DEVLOG.md`.
**Status:** ⏳ Not started

---

# Ticket PJ-01: DB models + migration scaffold

## What Is This Ticket?

The PJ phase introduces three new tables — `brand_profile`, `conversation_messages`, `brand_assets` — that together hold every user's brand context plus the receipts of how it was learned. This ticket lays the schema foundation: SQLAlchemy models matching the DDL in PJ-00 §5, imports wired into `app/db.py` so `Base.metadata.create_all` provisions them at startup, and a smoke test proving the tables come up in a fresh Postgres.

Nothing else in PJ can land before this. PJ-02 needs `brand_assets`, PJ-04 needs `brand_profile` + `conversation_messages`, PJ-09 reads `brand_profile` from the pipeline. The schema is load-bearing for ~10 downstream tickets.

### Why It Matters

- Replaces the single-tenant `data/brand_knowledge.json` design with per-user rows.
- `extras JSONB` gives the LLM a flexible scratchpad for industry-specific facts without future schema migrations.
- Mirrors the `app/models/user_api_key.py` precedent — same `Base.metadata.create_all` pattern, no Alembic.

---

## What Was Already Done

- `app/db.py` already declares the SQLAlchemy `Base` and triggers `Base.metadata.create_all` at startup.
- `app/models/user_api_key.py` is the canonical model precedent — single model file, imported in `app/db.py` to register with metadata.
- Postgres 16 is running locally (`nerdy-db-1` on host port 5433) and is the target for `create_all`.
- PJ-00 §5 fixes the DDL: typed columns, `extras JSONB`, `onboarding_phase` enum-by-convention, `good_enough_at` timestamp.

---

## What This Ticket Must Accomplish

### Goal

Land three SQLAlchemy models matching PJ-00 §5 DDL, wired into `app/db.py`, with a startup smoke test confirming `Base.metadata.create_all` creates them in a clean schema.

### Deliverables Checklist

#### A. Implementation

- [ ] `app/models/brand_profile.py` — `BrandProfile` SQLAlchemy model with all typed columns + `extras JSONB` per PJ-00 §5.1.
- [ ] `app/models/conversation_message.py` — `ConversationMessage` model per §5.2 (append-only log).
- [ ] `app/models/brand_asset.py` — `BrandAsset` model per §5.3 (uploaded file metadata + extracted_facts JSONB).
- [ ] Update `app/db.py` to import all three modules so they register with `Base.metadata`.
- [ ] Add the composite index `ix_conversation_messages_lookup` on `(user_id, touchpoint, session_id, created_at)` per §5.2.
- [ ] Add `ix_brand_assets_user` on `(user_id)` and `ix_brand_profile_industry` on `(industry)`.
- [ ] Configure `onboarding_phase` default to `'identify'`, `extras` default to `{}`.

#### B. Tests (`tests/test_models/test_brand_profile_schema.py`)

- [ ] TDD first.
- [ ] `test_brand_profile_create_minimal` — write a row with only `user_id`; row reads back with defaults.
- [ ] `test_brand_profile_extras_jsonb_roundtrip` — write a nested dict, read it back identically.
- [ ] `test_conversation_message_append` — write three rows for the same `(user_id, touchpoint)`, query ordered by `created_at` returns all three.
- [ ] `test_brand_asset_create` — write with a generated UUID, read back the storage_path and asset_type.
- [ ] `test_metadata_create_all_idempotent` — calling `create_all` twice does not raise.

#### C. Integration Expectations

- [ ] Models import cleanly inside `app/db.py` without circular imports.
- [ ] `nerdy-api-1` container starts and the tables appear in the `nerdy-db-1` Postgres instance.
- [ ] No existing tests regress.

#### D. Documentation

- [ ] DEVLOG entry (top of file): `## 2026-XX-YY — PJ-01: DB models + migration scaffold (✅)` with summary of tables added.
- [ ] No phase plan edits.

---

## Branch & Merge Workflow

```bash
git switch final-submission && git pull
git switch -c feature/PJ-01-db-models
# implement, run tests
git add app/models/ app/db.py tests/test_models/
git commit -m "feat(PJ-01): brand_profile + conversation_messages + brand_assets models"
git push -u origin feature/PJ-01-db-models
```

---

## Important Context

### Files to Create

| File | Why |
|------|-----|
| `app/models/brand_profile.py` | Typed-core + extras model — pipeline reads this |
| `app/models/conversation_message.py` | Append-only chat history per user+touchpoint |
| `app/models/brand_asset.py` | Logo / style guide metadata + vision-pass results |
| `tests/test_models/test_brand_profile_schema.py` | Smoke + roundtrip tests |

### Files to Modify

| File | Action |
|------|--------|
| `app/db.py` | Add imports for the three new model modules so they register with `Base.metadata` |

### Files to NOT Modify

- `app/models/user_api_key.py` — read-only pattern reference.
- `data/brand_knowledge.json` — handled in PJ-09, not here.
- `iterate/`, `generate/`, frontend — none of those see schema changes yet.

### Files to READ for Context

| File | Why |
|------|-----|
| `docs/development/tickets/PJ-00-phase-plan.md` §5 | DDL spec, column types, indexes |
| `app/models/user_api_key.py` | Pattern: single-model file, Base inheritance, default timestamps |
| `app/db.py` | Where new imports go; where `create_all` runs |

---

## Architectural Decisions

| Decision | Reference | Summary |
|----------|-----------|---------|
| Typed core + open extras | PJ-00 §3 decision 2 | ~10 typed columns the pipeline relies on, plus `extras JSONB` for LLM-discovered facts |
| No Alembic | PJ-00 §5.4 | Same `Base.metadata.create_all` pattern as BYO Keys; no migration framework |
| `extras` is JSONB, not text | PJ-00 §5.1 | Lets the LLM stash structured facts; queryable if we ever need it |
| Per-user scoping | PJ-00 §6.4 | Every table keyed on `user_id` from Clerk JWT — no cross-tenant leakage primitives in the schema |

---

## Suggested Implementation Pattern

```python
# app/models/brand_profile.py
from sqlalchemy import Column, Text, ARRAY, TIMESTAMP, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func
from app.db import Base


class BrandProfile(Base):
    __tablename__ = "brand_profile"

    user_id = Column(Text, primary_key=True)
    business_name = Column(Text)
    industry = Column(Text, index=True)
    audience = Column(Text)
    mission = Column(Text)
    value_props = Column(ARRAY(Text))
    tone_descriptors = Column(ARRAY(Text))
    avoid_phrases = Column(ARRAY(Text))
    do_dont_rules = Column(JSONB)
    palette_primary_hex = Column(Text)
    palette_secondary_hex = Column(Text)
    palette_accent_hex = Column(Text)
    logo_asset_id = Column(UUID(as_uuid=True), ForeignKey("brand_assets.id"))

    extras = Column(JSONB, nullable=False, server_default="{}")

    onboarding_phase = Column(Text, nullable=False, server_default="identify")
    good_enough_at = Column(TIMESTAMP(timezone=True))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
```

```python
# app/db.py — add at the bottom of the existing model-imports block
from app.models import brand_profile  # noqa: F401
from app.models import conversation_message  # noqa: F401
from app.models import brand_asset  # noqa: F401
```

`ConversationMessage` follows the same pattern with `BIGSERIAL` (use `BigInteger` + `autoincrement=True`) primary key. `BrandAsset` uses `UUID(as_uuid=True)` with `server_default=text("gen_random_uuid()")`.

---

## Edge Cases to Handle

1. `gen_random_uuid()` requires the `pgcrypto` extension — confirm Postgres 16 image bundles it (it does), otherwise add `CREATE EXTENSION IF NOT EXISTS pgcrypto;` to the startup path.
2. `value_props TEXT[]` — assert array roundtrip works through SQLAlchemy with `postgresql.ARRAY(Text)`.
3. Foreign key `brand_profile.logo_asset_id → brand_assets.id` creates a circular dependency at create_all time if the tables are emitted in the wrong order. SQLAlchemy handles this via `use_alter=True` on the FK if needed.
4. `extras` default `'{}'::jsonb` — use `server_default="{}"` and let SQLAlchemy cast it.
5. Index creation must be idempotent — running `create_all` twice cannot error.

---

## Definition of Done

- [ ] Three new model files exist and import cleanly.
- [ ] `app/db.py` imports them; `nerdy-api-1` starts without errors.
- [ ] All five new tests pass (`pytest tests/test_models/test_brand_profile_schema.py -v`).
- [ ] `ruff check .` clean.
- [ ] Existing test suite has no regressions.
- [ ] DEVLOG entry prepended.
- [ ] Feature branch pushed.

---

## Estimated Time

| Task | Estimate |
|------|----------|
| Read PJ-00 §5 + `user_api_key.py` | 15 min |
| Write three model files | 60 min |
| Wire into `app/db.py` | 10 min |
| Write tests + iterate | 90 min |
| Smoke against docker-compose Postgres | 30 min |
| DEVLOG + commit | 15 min |
| **Total** | **~0.5 day** |

---

## After This Ticket: What Comes Next

- **PJ-02** — Brand assets API + storage (depends on `brand_assets` table)
- **PJ-04** — Agent endpoint scaffold (depends on `brand_profile` + `conversation_messages`)
- All remaining PJ tickets — schema is the foundation
