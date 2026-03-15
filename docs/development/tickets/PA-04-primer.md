# PA-04 Primer: Session CRUD API

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** PA-03 (Google SSO) must be complete — real auth required. See `docs/DEVLOG.md`.

---

## What Is This Ticket?

PA-04 completes the **Session CRUD API** — creating sessions that trigger pipeline jobs, listing sessions with filtering/pagination, and retrieving session detail. The routes already exist but need per-user isolation, proper input validation, and filtering.

### Why It Matters

- Sessions are the core entity of the application — every user interaction starts with creating or viewing a session
- Per-user isolation (R5-Q5) ensures users only see their own data
- Proper config validation catches bad input before it reaches the Celery pipeline
- The session list is the home screen (Section 4.7.3) — it must support filtering and sorting

---

## What Was Already Done

- `app/api/routes/sessions.py`: Three routes exist:
  - `POST /sessions` — creates session, triggers `run_pipeline_session.delay(session_id)`, returns 201
  - `GET /sessions` — lists ALL sessions (no user filtering), reverse chronological
  - `GET /sessions/{session_id}` — gets session detail by ID
- `app/api/schemas/session.py`: Pydantic schemas exist:
  - `SessionCreate` — accepts `config: dict` (no validation)
  - `SessionSummary` — list item with `progress_summary`
  - `SessionDetail` — full session fields
  - `ProgressSummary` — running session progress from Redis
- `app/workers/tasks/pipeline_task.py`: Simulated pipeline task with progress publishing
- `app/api/deps.py`: `get_current_user()` (mock in PA-01, replaced with real JWT in PA-03)

---

## What This Ticket Must Accomplish

### Goal

Harden the Session CRUD API with per-user isolation, input validation on `SessionCreate`, filtering/pagination on the list endpoint, and a `DELETE` endpoint.

### Deliverables Checklist

#### A. Per-User Isolation

- [ ] `POST /sessions`: Set `user_id` from authenticated user (not from request body)
- [ ] `GET /sessions`: Filter by `user_id` from authenticated user — users NEVER see other users' sessions
- [ ] `GET /sessions/{session_id}`: Return 404 if session belongs to a different user
- [ ] `DELETE /sessions/{session_id}`: Only owner can delete. Return 404 for other users.

#### B. Input Validation (`app/api/schemas/session.py`)

- [ ] Replace `config: dict` with a typed `SessionConfig` schema:
  - `audience` (required, enum: "parents", "students")
  - `campaign_goal` (required, enum: "awareness", "conversion")
  - `ad_count` (required, int, default 50, min 1, max 200)
  - `name` (optional, string) — user-facing session name
  - `cycle_count` (optional, int, default 3, min 1, max 10)
  - `quality_threshold` (optional, float, default 7.0, min 5.0, max 10.0)
  - `dimension_weights` (optional, enum: "awareness_profile", "conversion_profile", "equal")
  - `model_tier` (optional, enum: "standard", "premium")
  - `budget_cap_usd` (optional, float, min 1.0)
  - `image_enabled` (optional, bool, default true)
  - `aspect_ratios` (optional, list of enum: "1:1", "4:5", "9:16")
- [ ] Return 422 with clear messages for invalid input

#### C. Filtering & Pagination on `GET /sessions`

- [ ] Query parameters:
  - `?audience=parents` — filter by audience
  - `?campaign_goal=conversion` — filter by campaign goal
  - `?status=completed` — filter by status (pending, running, completed, failed)
  - `?sort_by=created_at` (default) or `sort_by=score`
  - `?offset=0&limit=20` — pagination
- [ ] Return total count in response for pagination UI
- [ ] Include `config` summary fields (audience, campaign_goal, ad_count) in `SessionSummary`

#### D. Delete Endpoint

- [ ] `DELETE /sessions/{session_id}` — soft delete or hard delete
- [ ] Cancel Celery task if session is still running
- [ ] Return 204 on success

#### E. Session Name Generation

- [ ] Auto-generate a human-readable name if not provided: e.g., "SAT Parents Conversion — Mar 15"
- [ ] Store in `Session.name` field (added in PA-02)

#### F. Tests (`tests/test_app/test_sessions.py`)

- [ ] TDD first
- [ ] Test create session with valid config returns 201
- [ ] Test create session with invalid config returns 422
- [ ] Test list sessions returns only current user's sessions
- [ ] Test list sessions with audience filter
- [ ] Test list sessions with status filter
- [ ] Test list sessions with pagination (offset + limit)
- [ ] Test get session returns 404 for another user's session
- [ ] Test delete session returns 204
- [ ] Test delete returns 404 for another user's session
- [ ] Minimum: 9+ tests

#### G. Documentation

- [ ] Add PA-04 entry in `docs/DEVLOG.md`

---

## Important Context

### Architectural Decisions

| Decision | Reference | Summary |
|----------|-----------|---------|
| Session = one pipeline run | R5-Q1 | Immutable after completion. Config locked on creation. |
| Per-user isolation | R5-Q5 | Filter at query level. Never leak cross-user data. |
| Session list as home screen | R5-Q2, Section 4.7.3 | Reverse-chronological cards with filters and badges |
| Session config from PRD | Section 4.7.2 | Full config schema with required and optional fields |

### Files to Modify/Create

| File | Action |
|------|--------|
| `app/api/routes/sessions.py` | Modify — add user filtering, delete, pagination |
| `app/api/schemas/session.py` | Modify — typed SessionConfig, extend SessionSummary |
| `tests/test_app/test_sessions.py` | Create — CRUD tests |

### Files You Should READ for Context

| File | Why |
|------|-----|
| `docs/reference/prd.md` (Section 4.7.2) | Session config schema |
| `docs/reference/prd.md` (Section 4.7.3) | Session list spec |
| `app/api/routes/sessions.py` | Existing routes to extend |
| `app/api/schemas/session.py` | Existing schemas to extend |
| `app/api/deps.py` | `get_current_user()` — now returns real user from PA-03 |
| `app/workers/tasks/pipeline_task.py` | Pipeline task triggered by create |

---

## Definition of Done

- [ ] Users only see their own sessions (per-user isolation enforced)
- [ ] `SessionCreate` validates config fields with proper types and constraints
- [ ] `GET /sessions` supports filtering by audience, goal, status + pagination
- [ ] `DELETE /sessions/{session_id}` works with ownership check
- [ ] Auto-generated session names
- [ ] Tests pass
- [ ] Lint clean
- [ ] DEVLOG updated

---

## Estimated Time: 60–90 minutes

---

## After This Ticket: What Comes Next

**PA-05 (Brief Configuration Form)** builds the React form that submits to `POST /sessions`. The `SessionConfig` schema from this ticket defines exactly what fields the form must collect.
