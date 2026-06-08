# PJ-09 Primer

**Source plan:** [`PJ-00-phase-plan.md`](PJ-00-phase-plan.md) — §11 (Pipeline integration), §3 decision 4 (strict per-user replace), §3 decision 13 (GRILL Q3 — one-shot backfill).
**For:** New Cursor Agent session
**Date:** 2026-06-08
**Previous work:** PJ-01..PJ-06 merged; PJ-07/PJ-08 may or may not be merged (UI doesn't block this). See `docs/development/DEVLOG.md`.
**Status:** ⏳ Not started

---

# Ticket PJ-09: Pipeline rewire (highest-risk ticket)

## What Is This Ticket?

This is the load-bearing ticket of PJ. The existing pipeline reads `data/brand_knowledge.json` — a Varsity-specific facts/personas/competitive file — at every brief-expansion call. This ticket rewires it to read each user's `brand_profile` instead, deletes `data/brand_knowledge.json`, gates `POST /api/sessions` on `good_enough_at IS NOT NULL`, and ships a **one-shot backfill migration** that turns every existing user's most-recent session into a pre-filled `brand_profile` so they don't hit the onboarding wall on their next sign-in.

The backfill is non-negotiable. Per GRILL Q3 (decision 13), production already has real users; we cannot wall them all out behind onboarding. The migration reads each existing user's latest `sessions.config` (which carries `audience`, `campaign_goal`, `persona`, `key_message`) and pre-fills a `brand_profile` row with `good_enough_at = now()`. New signups still go through the full 5-phase chat.

### Why It Matters

- Without the rewire, the onboarding profile is decorative — the pipeline ignores it.
- Without the gate, users can create sessions before completing onboarding (no enforcement).
- Without the backfill, every pre-PJ user gets locked out.
- This is also the highest-risk ticket: a broken rewire breaks every pipeline run.

---

## What Was Already Done

- **PJ-01..PJ-06** — `brand_profile` table populated by agent.
- `generate/brief_expansion.py` — current implementation reads `data/brand_knowledge.json` and `data/config.yaml`.
- `app/workers/tasks/pipeline_task.py` — entry point; calls `_run_image_pipeline` / `_run_video_pipeline`.
- `app/workers/user_keys_loader.py` — pattern for loading per-user resources at task start.
- `iterate/pipeline_runner.py` and `pipeline_orchestrator.py` — accept a `PipelineConfig` that needs to gain a `brand_profile` field.
- `app/api/routes/sessions.py` — `POST /api/sessions` endpoint.

---

## What This Ticket Must Accomplish

### Goal

Pipeline reads `brand_profile` per user, no `brand_knowledge.json` fallback, sessions blocked at creation when profile not good enough, and every existing user is backfilled to a non-onboarding-blocked state.

### Deliverables Checklist

#### A. Implementation — Pipeline rewire

- [ ] `app/workers/brand_profile_loader.py` — `load_brand_profile_for_user(user_id) -> dict` returns a frozen snapshot dict matching the shape `brief_expansion` expects. Pattern from `user_keys_loader.py`.
- [ ] Modify `generate/brief_expansion.py`:
  - Drop `load_brand_kb('data/brand_knowledge.json')` and all references.
  - Accept `brand_profile: dict` as a parameter (no global state).
  - Reads from `brand_profile.value_props`, `audience`, `mission`, `tone_descriptors`, `avoid_phrases`, `do_dont_rules`, and `extras` to build the expanded brief.
- [ ] Modify `iterate/pipeline_runner.py` `PipelineConfig` to add `brand_profile: dict` field. Thread it through to `brief_expansion`.
- [ ] Modify `iterate/pipeline_orchestrator.py` — accept `brand_profile` and pass it through.
- [ ] Modify `app/workers/tasks/pipeline_task.py` — load `brand_profile` for `session_row.user_id` at task start, pass to runner/orchestrator.
- [ ] Handle `generate/competitive.py` per PJ-00 §11.1: tutoring users keep the existing competitive intel; non-tutoring users get an empty competitive landscape (refresh deferred).
- [ ] Delete `data/brand_knowledge.json`.
- [ ] Strip Varsity-specific defaults (`brand`, `key_message`, `persona`) from `data/config.yaml`.

#### B. Implementation — Session gate

- [ ] Modify `POST /api/sessions` in `app/api/routes/sessions.py` to check `brand_profile.good_enough_at IS NOT NULL` for the requesting user. Return `403` with `detail: "brand_profile_not_ready"` if not.
- [ ] Both BYO API key check AND brand profile check must pass — neither subsumes the other.

#### C. Implementation — One-shot backfill (GRILL Q3)

- [ ] `scripts/migrations/PJ_backfill_brand_profile.py` — standalone script (NOT Alembic; matches project convention):
  1. For each distinct `sessions.user_id`:
     - Skip if `brand_profile` row already exists.
     - Load their most-recent `sessions` row by `created_at`.
     - Read `config` JSON; extract `audience`, `campaign_goal`, `persona`, `key_message`.
     - Insert a `brand_profile` row with:
       - `audience`, `mission` from `persona`, `value_props` from synthesizing `key_message`, plus `business_name='(legacy import)'` and `industry='tutoring'` (Varsity default, the only pre-PJ industry).
       - `tone_descriptors=['professional', 'trustworthy']` (sensible defaults).
       - `good_enough_at = now()`.
       - `onboarding_phase = 'complete'`.
       - `extras = {"backfilled": true, "source_session_id": <id>}`.
- [ ] Script is **idempotent** — re-running does not double-insert.
- [ ] Script logs `(backfilled_count, skipped_count)`.
- [ ] Add an `app/api/routes/me.py` endpoint or banner-flag field so the frontend can render "Welcome back — we set up your brand profile from your past sessions" once.
- [ ] Add Makefile target or document command: `python scripts/migrations/PJ_backfill_brand_profile.py`.

#### D. Tests (`tests/test_pipeline/test_brand_profile_integration.py` and `tests/test_migrations/test_PJ_backfill.py`)

- [ ] `test_brief_expansion_uses_brand_profile` — synthetic profile → assert expanded brief includes the user's mission + value props.
- [ ] `test_brief_expansion_no_brand_knowledge_json_import` — `grep` test: no module imports `data/brand_knowledge.json`.
- [ ] `test_pipeline_task_loads_brand_profile` — task with `user_id` → asserts loader called.
- [ ] `test_session_create_403_when_no_profile` — fresh user → 403 on `POST /api/sessions`.
- [ ] `test_session_create_403_when_good_enough_null` — profile exists but `good_enough_at=None` → 403.
- [ ] `test_session_create_200_when_gates_pass` — profile good enough + BYO key → 200.
- [ ] Backfill tests:
  - `test_backfill_skips_existing_profile` — user with profile → not touched.
  - `test_backfill_creates_profile_from_latest_session` — user with sessions, no profile → profile created with `good_enough_at`.
  - `test_backfill_idempotent` — run twice → no duplicate rows, second run logs 0 backfilled.
  - `test_backfill_handles_user_with_no_sessions` — skipped (would have nothing to backfill from).

#### E. Documentation

- [ ] DEVLOG entry: `## 2026-XX-YY — PJ-09: Pipeline rewire + brand_knowledge.json removal + backfill (✅)`.
- [ ] Note: deletion of `data/brand_knowledge.json` and removal of Varsity defaults from `config.yaml`.
- [ ] Document the backfill command + when to run it (post-deploy, pre-cutover).

---

## Branch & Merge Workflow

```bash
git switch final-submission && git pull
git switch -c feature/PJ-09-pipeline-rewire
# implement; run full pytest + a real pipeline smoke
git add generate/ iterate/ app/ scripts/migrations/ tests/ data/config.yaml
git rm data/brand_knowledge.json
git commit -m "feat(PJ-09): pipeline reads brand_profile per user + backfill migration"
git push -u origin feature/PJ-09-pipeline-rewire
```

---

## Important Context

### Files to Create

| File | Why |
|------|-----|
| `app/workers/brand_profile_loader.py` | Per-user profile loader |
| `scripts/migrations/PJ_backfill_brand_profile.py` | One-shot backfill |
| `tests/test_pipeline/test_brand_profile_integration.py` | Integration tests |
| `tests/test_migrations/test_PJ_backfill.py` | Backfill tests |

### Files to Modify

| File | Action |
|------|--------|
| `generate/brief_expansion.py` | Replace `brand_knowledge.json` load with parameter-driven brand_profile read |
| `iterate/pipeline_runner.py` | Add `brand_profile` to `PipelineConfig`, thread through |
| `iterate/pipeline_orchestrator.py` | Accept + pass `brand_profile` |
| `app/workers/tasks/pipeline_task.py` | Load profile at task start, pass to runner |
| `app/api/routes/sessions.py` | Gate `POST /api/sessions` on `good_enough_at` |
| `data/config.yaml` | Strip Varsity-specific defaults |
| `generate/competitive.py` | Industry-gated behavior (tutoring keeps existing, others empty) |

### Files to Delete

| File | Why |
|------|-----|
| `data/brand_knowledge.json` | Replaced by per-user `brand_profile` |

### Files to NOT Modify

- `app/api/agent/*` — frozen from PJ-04..PJ-06.
- `evaluate/` modules — pipeline evaluation unchanged.

### Files to READ for Context

| File | Why |
|------|-----|
| `app/workers/user_keys_loader.py` | Pattern for per-user resource loading at task start |
| `app/api/routes/sessions.py` | Where the gate goes |
| `docs/development/tickets/PJ-00-phase-plan.md` §11 | Full rewire spec |
| `generate/brief_expansion.py` (current) | Understand exactly what `brand_knowledge.json` provided |

---

## Architectural Decisions

| Decision | Reference | Summary |
|----------|-----------|---------|
| Strict per-user replace | PJ-00 §3 decision 4 | No `brand_knowledge.json` fallback; empty profile blocks sessions |
| One-shot backfill | PJ-00 §3 decision 13 (GRILL Q3) | Existing users get pre-filled profiles from their latest session config |
| Both gates check | PJ-00 §11.2 | BYO API keys AND brand profile must both pass at session-create |
| Industry-gated competitive | PJ-00 §11.1 | Tutoring keeps Varsity competitive intel; other industries get empty for now |
| No Alembic | precedent | Plain Python migration script, executed manually post-deploy |

---

## Suggested Implementation Pattern

```python
# app/workers/brand_profile_loader.py
from app.db import SessionLocal
from app.models.brand_profile import BrandProfile

def load_brand_profile_for_user(user_id: str) -> dict:
    with SessionLocal() as db:
        row = db.query(BrandProfile).get(user_id)
        if not row:
            raise RuntimeError(f"no brand_profile for user {user_id}")
        return {
            "business_name": row.business_name,
            "industry": row.industry,
            "audience": row.audience,
            "mission": row.mission,
            "value_props": row.value_props or [],
            "tone_descriptors": row.tone_descriptors or [],
            "avoid_phrases": row.avoid_phrases or [],
            "do_dont_rules": row.do_dont_rules or {"do": [], "dont": []},
            "palette": {
                "primary": row.palette_primary_hex,
                "secondary": row.palette_secondary_hex,
                "accent": row.palette_accent_hex,
            },
            "extras": row.extras or {},
        }
```

```python
# generate/brief_expansion.py (new signature)
def expand_brief(raw_brief: dict, brand_profile: dict, *, audience_profile_path=None) -> dict:
    """
    brand_profile keys: business_name, industry, audience, mission, value_props,
                       tone_descriptors, avoid_phrases, do_dont_rules, palette, extras
    """
    bp = brand_profile
    expanded = {
        **raw_brief,
        "business_name": bp["business_name"],
        "industry": bp["industry"],
        "audience": raw_brief.get("audience") or bp["audience"],
        "mission": bp["mission"],
        "value_props": bp["value_props"],
        "tone_descriptors": bp["tone_descriptors"],
        "brand_context_extras": bp["extras"],
        "avoid_phrases": bp["avoid_phrases"],
        "do_dont_rules": bp["do_dont_rules"],
    }
    return expanded
```

```python
# scripts/migrations/PJ_backfill_brand_profile.py
"""
One-shot migration: backfill brand_profile for every existing user from their latest session.config.
Idempotent — safe to re-run. Sets good_enough_at = now() so existing users skip the onboarding wall.
"""
import sys
from datetime import datetime, timezone
from app.db import SessionLocal
from app.models.brand_profile import BrandProfile
# Import the existing Session model — name may vary
from app.models.session import Session as SessionRow

DEFAULT_INDUSTRY = "tutoring"  # only pre-PJ industry was Varsity
DEFAULT_BUSINESS_NAME = "(legacy import — refine in Settings)"
DEFAULT_TONE = ["professional", "trustworthy"]

def main():
    backfilled = 0
    skipped = 0
    with SessionLocal() as db:
        user_ids = {u for (u,) in db.query(SessionRow.user_id).distinct() if u}
        for uid in user_ids:
            if db.query(BrandProfile).get(uid):
                skipped += 1
                continue
            latest = (db.query(SessionRow)
                        .filter(SessionRow.user_id == uid)
                        .order_by(SessionRow.created_at.desc())
                        .first())
            if not latest or not latest.config:
                skipped += 1
                continue
            cfg = latest.config
            row = BrandProfile(
                user_id=uid,
                business_name=DEFAULT_BUSINESS_NAME,
                industry=DEFAULT_INDUSTRY,
                audience=cfg.get("audience") or "students and parents",
                mission=cfg.get("persona") or "help students achieve their academic goals",
                value_props=[cfg.get("key_message", "personalized tutoring")],
                tone_descriptors=DEFAULT_TONE,
                onboarding_phase="complete",
                good_enough_at=datetime.now(timezone.utc),
                extras={"backfilled": True, "source_session_id": latest.session_id},
            )
            db.add(row); backfilled += 1
        db.commit()
    print(f"backfilled={backfilled} skipped={skipped}")

if __name__ == "__main__":
    main()
```

```python
# app/api/routes/sessions.py — add to POST handler
from app.models.brand_profile import BrandProfile

profile = db.query(BrandProfile).get(user_id)
if not profile or profile.good_enough_at is None:
    raise HTTPException(403, detail="brand_profile_not_ready")
```

---

## Edge Cases to Handle

1. Backfill runs on a brand-new install with zero users — script exits with `backfilled=0 skipped=0`; harmless.
2. User has sessions with malformed `config` JSON — script skips and logs.
3. `generate/competitive.py` reads a now-deleted file — make sure all callsites either gate on `industry == 'tutoring'` or accept an empty competitive context.
4. Pre-PJ session is loaded for inspection (e.g., Ad Library) — must still render. Its `config` still has the resolved brand data, so pipeline-free read paths are unaffected.
5. Test fixtures using `brand_knowledge.json` — purge any test-only references.
6. `config.yaml` still referenced by tests with Varsity defaults — update test fixtures to supply `brand_profile` instead.
7. Worker container needs DB access for `brand_profile_loader` — already has it (BYO keys uses the same pattern); no infra change.
8. Race: user finishes onboarding while a pipeline task is already running — task uses the profile snapshot at task start (already loaded); next run picks up the latest. No mid-task swap.

---

## Definition of Done

- [ ] `data/brand_knowledge.json` is gone from the repo.
- [ ] `grep -r "brand_knowledge"` returns no live imports.
- [ ] Pipeline run on a real `brand_profile` produces output that references the user's actual mission and value props (manual inspection of one ad).
- [ ] Pipeline run for a user with no profile fails fast at task start with a clear error.
- [ ] `POST /api/sessions` returns 403 `brand_profile_not_ready` for a user without `good_enough_at`.
- [ ] Backfill script runs idempotently on a snapshot of the prod DB (locally restored).
- [ ] `ruff check .` clean, `pytest tests/` no PJ regressions.
- [ ] DEVLOG entry prepended with the backfill command documented.
- [ ] Feature branch pushed.

---

## Estimated Time

| Task | Estimate |
|------|----------|
| Read existing `brief_expansion` thoroughly | 45 min |
| `brand_profile_loader.py` + tests | 45 min |
| `brief_expansion.py` rewire + tests | 120 min |
| `pipeline_runner.py` / `pipeline_orchestrator.py` thread-through | 60 min |
| `pipeline_task.py` integration | 45 min |
| Session create gate + tests | 45 min |
| `competitive.py` industry gate | 45 min |
| `data/config.yaml` strip + `data/brand_knowledge.json` delete | 30 min |
| Backfill migration + tests + idempotency proof | 120 min |
| Full pipeline smoke (image + video) | 90 min |
| DEVLOG + commit | 30 min |
| **Total** | **~2 days** |

---

## After This Ticket: What Comes Next

- **PJ-10** — Post-session reflection (integrates against the now-rewired pipeline)
- **PJ-11** — Pre-session prep (writes brief into the gated session-create flow)
- **PJ-13** — Verification gate exercises this end-to-end
