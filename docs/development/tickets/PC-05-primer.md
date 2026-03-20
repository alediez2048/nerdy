# PC-05 Primer: Session campaign_id FK + Migration + API Filter

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** PC-04 (Campaign model + CRUD API), PA-02 (Session model), PA-04 (Session CRUD API). See `docs/DEVLOG.md`.

---

## What Is This Ticket?

PC-05 adds a `campaign_id` foreign key to the Session model so sessions can belong to a campaign. It extends the session API to filter by campaign, and ensures backward compatibility — existing sessions with no campaign continue to work.

### Why It Matters

- This is the relational link between Campaign and Session — without it, campaigns are empty shells
- The session list API needs to filter by campaign so the Campaign Detail view (PC-08) can show only its sessions
- Session creation within a campaign context (PC-09) requires this FK
- Must be backward compatible: `campaign_id` is nullable, existing sessions unaffected

---

## What Was Already Done

- PC-04: `app/models/campaign.py` — Campaign model with `sessions` relationship
- PA-02: `app/models/session.py` — Session model (no campaign reference yet)
- PA-04: `app/api/routes/sessions.py` — Session CRUD with filters (session_type, audience, campaign_goal, status)
- PA-04: `app/api/schemas/session.py` — `SessionSummary`, `SessionDetail`, `SessionCreate`

---

## What This Ticket Must Accomplish

### Goal

Add `campaign_id` to the Session model as a nullable FK, extend the session API to filter/assign by campaign, and update schemas to include campaign info.

### Deliverables Checklist

#### A. Model Change (`app/models/session.py` — modify)

- [ ] Add `campaign_id: Mapped[str | None] = mapped_column(String(64), ForeignKey("campaigns.campaign_id"), nullable=True, index=True)`
- [ ] Add `campaign = relationship("Campaign", back_populates="sessions")`

#### B. Schema Changes (`app/api/schemas/session.py` — modify)

- [ ] `SessionCreate`: add optional `campaign_id: str | None = None`
- [ ] `SessionSummary`: add `campaign_id: str | None = None`
- [ ] `SessionDetail`: add `campaign_id: str | None = None` and `campaign_name: str | None = None`

#### C. API Changes (`app/api/routes/sessions.py` — modify)

- [ ] `POST /sessions`: accept optional `campaign_id` in body, validate it exists and belongs to user, store on session row
- [ ] `GET /sessions`: add `campaign_id` query parameter filter
- [ ] `GET /sessions/{session_id}`: include `campaign_name` from joined campaign
- [ ] Validation: if `campaign_id` provided but campaign doesn't exist or belongs to another user → 404

#### D. Campaign Sessions Endpoint (`app/api/routes/campaigns.py` — modify)

- [ ] `GET /campaigns/{campaign_id}/sessions` — return paginated sessions filtered by campaign_id
- [ ] Reuses same `SessionSummary` schema and session list logic

#### E. Tests (`tests/test_app/test_sessions.py` — extend + `tests/test_app/test_campaigns.py` — extend)

- [ ] TDD first
- [ ] Test create session with `campaign_id` — session linked to campaign
- [ ] Test create session without `campaign_id` — `campaign_id` is null (backward compat)
- [ ] Test create session with invalid `campaign_id` — returns 404
- [ ] Test create session with another user's `campaign_id` — returns 404
- [ ] Test list sessions filter by `campaign_id`
- [ ] Test list sessions with no campaign filter — returns all sessions (including campaign-linked)
- [ ] Test `GET /campaigns/{id}/sessions` returns only campaign's sessions
- [ ] Test session detail includes `campaign_name`
- [ ] Minimum: 8+ new tests

#### F. Documentation

- [ ] Add ticket entry in `docs/DEVLOG.md`

---

## Branch & Merge Workflow

Work on `develop` branch per project convention.

---

## Important Context

### Files to Create

None — this ticket extends existing files.

### Files to Modify

| File | Action |
|------|--------|
| `app/models/session.py` | Add `campaign_id` FK + relationship |
| `app/api/schemas/session.py` | Add `campaign_id` to create/summary/detail |
| `app/api/routes/sessions.py` | Filter + validate campaign_id |
| `app/api/routes/campaigns.py` | Add `/campaigns/{id}/sessions` endpoint |
| `tests/test_app/test_sessions.py` | New campaign-linked session tests |
| `tests/test_app/test_campaigns.py` | Campaign sessions endpoint tests |
| `docs/DEVLOG.md` | Add ticket entry |

### Files You Should NOT Modify

- Any `generate/`, `evaluate/`, `iterate/`, `output/` pipeline code
- `app/workers/tasks/pipeline_task.py` — pipeline doesn't care about campaigns
- `app/models/campaign.py` — already has `sessions` relationship from PC-04

### Files You Should READ for Context

| File | Why |
|------|-----|
| `app/models/session.py` | Current model to extend |
| `app/models/campaign.py` | Campaign model (PC-04) |
| `app/api/routes/sessions.py` | Current session routes |
| `app/api/routes/campaigns.py` | Campaign routes (PC-04) |
| `app/api/schemas/session.py` | Current session schemas |

---

## Architectural Decisions

| Decision | Rationale |
|----------|-----------|
| Nullable FK | Existing sessions have no campaign — must remain valid |
| FK on `campaign_id` string, not `id` int | Consistent with how session_id is used throughout the codebase |
| User validation on campaign_id at create | Prevents assigning sessions to other users' campaigns |
| Campaign sessions endpoint on campaign router | Logically grouped: "show me this campaign's sessions" |

---

## Suggested Implementation Pattern

```python
# In create_session:
if body.campaign_id:
    campaign = db.query(CampaignModel).filter(
        CampaignModel.campaign_id == body.campaign_id,
        CampaignModel.user_id == user["user_id"],
    ).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    session_row.campaign_id = body.campaign_id
```

```python
# In list_sessions — new filter:
if campaign_id:
    query = query.filter(SessionModel.campaign_id == campaign_id)
```

---

## Edge Cases to Handle

1. Session created with archived campaign_id — allow it (archived ≠ deleted)
2. Campaign deleted (if ever hard-deleted in future) — FK constraint catches it
3. Move session between campaigns — not in scope (future: PATCH with campaign_id)
4. Session with campaign_id but campaign has no default_config — fine, campaign_id is just a grouping label here

---

## Definition of Done

- [ ] Session model has nullable `campaign_id` FK
- [ ] Session CRUD accepts and filters by `campaign_id`
- [ ] Campaign sessions endpoint returns correct sessions
- [ ] Backward compat: existing sessions with no campaign unaffected
- [ ] 8+ new tests pass
- [ ] Lint clean
- [ ] DEVLOG updated

---

## Estimated Time

| Task | Estimate |
|------|----------|
| Tests (TDD) | 15 min |
| Model + schema changes | 10 min |
| API route changes | 15 min |
| Campaign sessions endpoint | 10 min |
| DEVLOG | 5 min |

---

## After This Ticket: What Comes Next

- **PC-06:** Frontend CampaignList + CampaignCard (consumes `GET /campaigns` API)
- **PC-08:** CampaignDetail view (consumes `GET /campaigns/{id}/sessions`)
- **PC-09:** Pre-fill session form from campaign defaults
