# PC-04 Primer: Campaign Model + Migration + CRUD API

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** PA-02 (Session model), PA-04 (Session CRUD API), PC-00–PC-03 (video pipeline). See `docs/DEVLOG.md`.

---

## What Is This Ticket?

PC-04 introduces the **Campaign** entity — a named container that groups related sessions. Today every session is a standalone item in a flat list. With campaigns, users can organize sessions by marketing initiative (e.g. "Spring SAT Push", "Back-to-School Awareness") and spin up multiple sessions within a single campaign context.

This ticket creates the database model, Alembic migration, and full REST API for campaigns. It does NOT touch the frontend — that's PC-06/07.

### Why It Matters

- Users running dozens of sessions need organizational hierarchy — a flat list doesn't scale
- Campaigns provide default config (audience, goal, persona) so users don't re-enter the same settings for every session
- Roll-up stats across a campaign's sessions become possible (PC-11)
- Clean separation: campaigns are organizational containers, not pipeline executors

---

## What Was Already Done

- PA-02: `app/models/session.py` — Session SQLAlchemy model with `config` JSON column
- PA-02: `app/models/base.py` — `Base` declarative base class
- PA-04: `app/api/routes/sessions.py` — Session CRUD endpoints (POST/GET/PATCH/DELETE)
- PA-04: `app/api/schemas/session.py` — `SessionConfig`, `SessionCreate`, `SessionSummary`, etc.
- PA-03: `app/api/deps.py` — `get_current_user` auth dependency
- `app/db.py` — engine, session factory, `init_db()` auto-create

---

## What This Ticket Must Accomplish

### Goal

Create the `campaigns` database table, Campaign SQLAlchemy model, Pydantic schemas, and full CRUD API (`POST/GET/PATCH/DELETE`) with per-user isolation.

### Deliverables Checklist

#### A. Model (`app/models/campaign.py` — create)

- [ ] `Campaign` SQLAlchemy model on `Base`
- [ ] Columns:
  - `id`: int PK, autoincrement
  - `campaign_id`: String(64), unique, indexed — format `camp_<hex(8)>`
  - `name`: String(256), required
  - `user_id`: String(256), indexed (same pattern as Session)
  - `description`: Text, nullable
  - `audience`: String(32), nullable — default audience for sessions
  - `campaign_goal`: String(32), nullable — default goal
  - `default_config`: JSON, default `{}` — template config for new sessions
  - `status`: String(32), default `"active"` — `active` or `archived`
  - `created_at`: DateTime(timezone=True), server_default `func.now()`
  - `updated_at`: DateTime(timezone=True), onupdate `func.now()`, nullable
- [ ] Relationship: `sessions = relationship("Session", back_populates="campaign")`

#### B. Schemas (`app/api/schemas/campaign.py` — create)

- [ ] `CampaignCreate`: name (required), description (optional), audience (optional), campaign_goal (optional), default_config (optional dict)
- [ ] `CampaignUpdate`: name (optional), description (optional), status (optional — only `active`/`archived`)
- [ ] `CampaignSummary`: id, campaign_id, name, description, audience, campaign_goal, status, created_at, session_count (int)
- [ ] `CampaignDetail`: all summary fields + default_config + updated_at
- [ ] `CampaignListResponse`: campaigns list + total + offset + limit (pagination)

#### C. API Routes (`app/api/routes/campaigns.py` — create)

- [ ] `POST /campaigns` — create campaign, auto-generate `campaign_id`
- [ ] `GET /campaigns` — list user's campaigns (paginated, filterable by status)
- [ ] `GET /campaigns/{campaign_id}` — campaign detail with session_count
- [ ] `PATCH /campaigns/{campaign_id}` — update name, description, or status
- [ ] `DELETE /campaigns/{campaign_id}` — soft delete (set status to `archived`)
- [ ] All endpoints enforce per-user isolation via `get_current_user`
- [ ] `_campaign_id()` helper: `f"camp_{secrets.token_hex(8)}"`

#### D. Wire into App (`app/api/main.py` — modify)

- [ ] Import and include campaign router: `app.include_router(campaign_router, prefix="/api/campaigns", tags=["campaigns"])`
- [ ] Import campaign model in `app/db.py` so `init_db()` creates the table

#### E. Tests (`tests/test_app/test_campaigns.py` — create)

- [ ] TDD first: write tests before implementation
- [ ] Test create campaign returns 201 with campaign_id
- [ ] Test create campaign with all optional fields
- [ ] Test list campaigns returns only user's campaigns
- [ ] Test list campaigns pagination (offset/limit)
- [ ] Test list campaigns filter by status
- [ ] Test get campaign detail includes session_count = 0
- [ ] Test update campaign name
- [ ] Test update campaign status to archived
- [ ] Test delete campaign sets status to archived (soft delete)
- [ ] Test get non-existent campaign returns 404
- [ ] Test campaign isolation: user A cannot see user B's campaigns
- [ ] Minimum: 12+ tests

#### F. Documentation

- [ ] Add ticket entry in `docs/DEVLOG.md`
- [ ] Update decision log: "Why Campaigns are organizational containers, not pipeline executors"

---

## Branch & Merge Workflow

Work on `develop` branch per project convention.

---

## Important Context

### Files to Create

| File | Why |
|------|-----|
| `app/models/campaign.py` | Campaign SQLAlchemy model |
| `app/api/schemas/campaign.py` | Pydantic schemas for campaign API |
| `app/api/routes/campaigns.py` | Campaign CRUD endpoints |
| `tests/test_app/test_campaigns.py` | Campaign API tests |

### Files to Modify

| File | Action |
|------|--------|
| `app/db.py` | Import campaign model for auto-create |
| `app/api/main.py` | Mount campaign router |
| `docs/DEVLOG.md` | Add ticket entry |

### Files You Should NOT Modify

- `app/models/session.py` — session gets `campaign_id` in PC-05, not here
- `app/api/routes/sessions.py` — session endpoints unchanged in this ticket
- Any `generate/`, `evaluate/`, `iterate/` pipeline code

### Files You Should READ for Context

| File | Why |
|------|-----|
| `app/models/session.py` | Model pattern to follow |
| `app/api/routes/sessions.py` | Route pattern to follow |
| `app/api/schemas/session.py` | Schema pattern to follow |
| `app/api/deps.py` | Auth dependency |
| `app/db.py` | Model registration |

---

## Architectural Decisions

| Decision | Rationale |
|----------|-----------|
| Campaigns are containers, not executors | Campaigns don't run pipelines. Sessions within them do. Keeps complexity isolated. |
| Soft delete via `archived` status | No data loss. Archived campaigns and their sessions remain queryable. |
| `default_config` is a JSON template | Flexible — any SessionConfig field can be a default. Frontend merges at session creation. |
| Same user_id pattern as Session | No FK to users table yet (matches Session pattern). Easy to add later. |

---

## Suggested Implementation Pattern

```python
# app/models/campaign.py
class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    campaign_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(256))
    user_id: Mapped[str] = mapped_column(String(256), index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    audience: Mapped[str | None] = mapped_column(String(32), nullable=True)
    campaign_goal: Mapped[str | None] = mapped_column(String(32), nullable=True)
    default_config: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(32), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    sessions = relationship("Session", back_populates="campaign")
```

```python
# session_count in list endpoint
session_count = db.query(Session).filter(Session.campaign_id == row.campaign_id).count()
```

---

## Edge Cases to Handle

1. Campaign name empty or whitespace-only — reject with 400
2. Campaign with no sessions — session_count = 0, valid state
3. Archived campaign — still visible in list when filtered by `status=archived`, hidden from default list
4. Duplicate campaign names — allowed (campaign_id is the unique key, not name)
5. `default_config` with invalid fields — accept any JSON; validation happens at session creation

---

## Definition of Done

- [ ] Campaign model created with all columns
- [ ] CRUD API endpoints functional with per-user isolation
- [ ] Pagination and status filtering work
- [ ] Soft delete sets status to `archived`
- [ ] 12+ tests pass
- [ ] Lint clean (`ruff check . --fix`)
- [ ] DEVLOG updated
- [ ] Decision log updated

---

## Estimated Time

| Task | Estimate |
|------|----------|
| Tests (TDD) | 20 min |
| Model + schemas | 15 min |
| API routes | 20 min |
| Wire into app | 5 min |
| DEVLOG + decision log | 10 min |

---

## After This Ticket: What Comes Next

- **PC-05:** Add `campaign_id` FK to Session model — links sessions to campaigns
- **PC-06:** Frontend campaign list and card views
