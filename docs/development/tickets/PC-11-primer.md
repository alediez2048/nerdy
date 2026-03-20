# PC-11 Primer: Campaign Roll-up Stats

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** PC-04 (Campaign CRUD API), PC-05 (Session campaign_id FK), PC-08 (CampaignDetail view). See `docs/DEVLOG.md`.

---

## What Is This Ticket?

PC-11 adds aggregate statistics to campaigns — roll-up metrics computed from all sessions within a campaign. Both the API and frontend display stats like total sessions, ads generated/published, average quality score, total cost, and session status breakdown.

### Why It Matters

- Campaign cards and detail pages currently show session count but no performance data
- Users need to evaluate campaign effectiveness at a glance without clicking into each session
- Roll-up stats enable comparison between campaigns ("Spring Push" vs "Back-to-School")
- Stats come from existing `results_summary` data on sessions — no new pipeline work

---

## What Was Already Done

- PC-04: `CampaignSummary` schema has `session_count`
- PC-05: Sessions linked to campaigns via `campaign_id` FK
- PC-06: `CampaignCard` shows session count
- PC-08: `CampaignDetail` shows session list
- Session `results_summary` JSON contains: `ads_generated`, `ads_published`, `avg_score`, `cost_so_far`

---

## What This Ticket Must Accomplish

### Goal

Compute and display aggregate metrics across a campaign's sessions on both the campaign card (summary) and campaign detail page (full breakdown).

### Deliverables Checklist

#### A. API — Campaign Stats (`app/api/routes/campaigns.py` — modify)

- [ ] New helper: `_compute_campaign_stats(db, campaign_id) -> dict`
  - Queries all sessions with matching `campaign_id`
  - Aggregates:
    - `total_sessions`: count
    - `sessions_by_status`: `{ pending: N, running: N, completed: N, failed: N }`
    - `total_ads_generated`: sum across sessions
    - `total_ads_published`: sum across sessions
    - `avg_quality_score`: weighted average across sessions (by ads_published count)
    - `total_cost`: sum of `cost_so_far`
    - `session_types`: `{ image: N, video: N }`
- [ ] Include stats in `GET /campaigns/{id}` response
- [ ] Include summary stats in `GET /campaigns` list response (lightweight: session_count + total_ads + avg_score)

#### B. Schema Updates (`app/api/schemas/campaign.py` — modify)

- [ ] `CampaignStats` schema:
  ```python
  class CampaignStats(BaseModel):
      total_sessions: int = 0
      sessions_by_status: dict[str, int] = {}
      total_ads_generated: int = 0
      total_ads_published: int = 0
      avg_quality_score: float = 0.0
      total_cost: float = 0.0
      session_types: dict[str, int] = {}
  ```
- [ ] `CampaignDetail`: add `stats: CampaignStats`
- [ ] `CampaignSummary`: add lightweight stats (`total_ads_published`, `avg_quality_score`)

#### C. Frontend — CampaignCard Enhancement (`app/frontend/src/components/CampaignCard.tsx` — modify)

- [ ] Show roll-up metrics below badges:
  - Total ads published (e.g. "42 ads published")
  - Average score (e.g. "7.4 avg")
  - Total cost (e.g. "$12.50")
- [ ] Mini sparkline of session scores if available (optional)

#### D. Frontend — CampaignDetail Stats Panel (`app/frontend/src/views/CampaignDetail.tsx` — modify)

- [ ] Stats panel above session list:
  - Session status breakdown (pie or bar)
  - Total ads generated vs published
  - Average quality score
  - Total cost
  - Session type breakdown (image vs video)
- [ ] Style consistent with session Overview tab metrics

#### E. Tests (`tests/test_app/test_campaigns.py` — extend)

- [ ] TDD first
- [ ] Test stats with 0 sessions → all zeros
- [ ] Test stats with multiple sessions → correct aggregation
- [ ] Test avg_quality_score weighted by ads_published
- [ ] Test stats include session type breakdown
- [ ] Test list endpoint includes summary stats
- [ ] Minimum: 6+ new tests

#### F. Documentation

- [ ] Add ticket entry in `docs/DEVLOG.md`

---

## Branch & Merge Workflow

Work on `develop` branch per project convention.

---

## Important Context

### Files to Create

None — extends existing files.

### Files to Modify

| File | Action |
|------|--------|
| `app/api/routes/campaigns.py` | Add stats computation |
| `app/api/schemas/campaign.py` | Add CampaignStats schema |
| `app/frontend/src/components/CampaignCard.tsx` | Show summary stats |
| `app/frontend/src/views/CampaignDetail.tsx` | Add stats panel |
| `app/frontend/src/types/campaign.ts` | Add stats types |
| `tests/test_app/test_campaigns.py` | Stats tests |
| `docs/DEVLOG.md` | Add ticket entry |

### Files You Should NOT Modify

- Any pipeline code (`generate/`, `evaluate/`, `iterate/`, `output/`)
- `app/models/session.py` — no model changes
- `app/models/campaign.py` — no model changes

### Files You Should READ for Context

| File | Why |
|------|-----|
| `app/api/routes/campaigns.py` | Current campaign routes |
| `app/api/routes/sessions.py` | How results_summary is used |
| `app/frontend/src/tabs/Overview.tsx` | Stats display pattern |
| `app/frontend/src/components/SessionCard.tsx` | How session metrics are shown |

---

## Suggested Implementation Pattern

```python
def _compute_campaign_stats(db: Session, campaign_id: str) -> dict:
    sessions = db.query(SessionModel).filter(
        SessionModel.campaign_id == campaign_id
    ).all()

    total_ads_gen = 0
    total_ads_pub = 0
    total_cost = 0.0
    weighted_score_sum = 0.0
    total_weight = 0
    status_counts: dict[str, int] = {}
    type_counts: dict[str, int] = {}

    for s in sessions:
        r = s.results_summary or {}
        c = s.config or {}
        gen = r.get("ads_generated", 0) or r.get("total_ads_generated", 0)
        pub = r.get("ads_published", 0)
        avg = r.get("avg_score", 0.0)
        cost = r.get("cost_so_far", 0.0)

        total_ads_gen += gen
        total_ads_pub += pub
        total_cost += cost
        if pub > 0:
            weighted_score_sum += avg * pub
            total_weight += pub

        status_counts[s.status] = status_counts.get(s.status, 0) + 1
        stype = c.get("session_type", "image")
        type_counts[stype] = type_counts.get(stype, 0) + 1

    return {
        "total_sessions": len(sessions),
        "sessions_by_status": status_counts,
        "total_ads_generated": total_ads_gen,
        "total_ads_published": total_ads_pub,
        "avg_quality_score": round(weighted_score_sum / total_weight, 2) if total_weight else 0.0,
        "total_cost": round(total_cost, 2),
        "session_types": type_counts,
    }
```

---

## Edge Cases to Handle

1. Campaign with all pending sessions — no results_summary → all stats are 0
2. Sessions with missing results_summary fields — default to 0
3. Weighted average with 0 published ads — return 0.0, not division by zero
4. Mixed image/video campaigns — type breakdown handles both
5. Large campaigns (50+ sessions) — stats query should be efficient (single query)

---

## Definition of Done

- [ ] Campaign detail includes computed stats
- [ ] Campaign list includes summary stats per campaign
- [ ] CampaignCard shows ads published + avg score
- [ ] CampaignDetail shows full stats panel
- [ ] Stats correctly aggregated from session results_summary
- [ ] 6+ new tests pass
- [ ] Lint clean
- [ ] DEVLOG updated

---

## Estimated Time

| Task | Estimate |
|------|----------|
| Tests (TDD) | 15 min |
| Stats computation | 15 min |
| Schema updates | 10 min |
| Frontend card + detail | 20 min |
| DEVLOG | 5 min |

---

## After This Ticket: What Comes Next

- **PC-12:** Campaign archiving + management refinements
