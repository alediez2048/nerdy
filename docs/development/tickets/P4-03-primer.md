# P4-03 Primer: Competitive Intelligence — Automated Refresh + Trends

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** P0-09/P0-10 built initial pattern DB + query interface. See `docs/development/DEVLOG.md`.

---

## What Is This Ticket?

P4-03 extends the competitive intelligence system (built in P0-09/P0-10) with **temporal trend tracking**, **automated refresh workflow**, and **strategy shift alerts**. The pattern DB becomes time-aware — you can ask "what hooks are trending up?" and "has competitor X changed strategy?"

### Why It Matters

- **Pillar 6: Learning Is Structural** — Competitive patterns evolve; the system must track changes over time
- **Section 4.8.8:** Monthly refresh recommended; track temporal trends
- **Bonus:** +10 points for competitive intelligence from Meta Ad Library (shared with P0-09, P0-10, P1-01)
- Strategy shift detection enables proactive brief adjustment (feeds P4-02 self-healing)

---

## What Was Already Done

- `data/competitive/patterns.json` — 40 structured pattern records from P0-09 with fields: `competitor`, `hook_type`, `emotional_angle`, `cta_style`, `target_audience`, `source_url`, `pattern_id`
- `data/competitive/competitor_summaries.json` — Per-competitor strategy summaries with `dominant_hooks`, `emotional_levers`, `gaps` (opportunities)
- `generate/competitive.py` — Full query interface:
  - `load_patterns()` — Load + cache pattern DB
  - `query_patterns(audience, campaign_goal, hook_type, competitor, tags, top_n)` — Filter + rank
  - `get_competitor_summary(competitor)` — Strategy summary for one competitor
  - `get_all_competitors()` — List all competitors
  - `get_landscape_context(audience, campaign_goal)` — Formatted string for prompt injection
- `generate/brief_expansion.py` — Already injects competitive context via `get_landscape_context()` into `ExpandedBrief.competitive_context`

---

## What This Ticket Must Accomplish

### Goal

Add temporal awareness to the competitive intelligence system: track when patterns were observed, detect trends and strategy shifts, and surface alerts for the dashboard.

### Deliverables Checklist

#### A. Temporal Pattern Schema

Create `generate/competitive_trends.py`:

- [ ] `PatternSnapshot` dataclass — `pattern_id: str`, `competitor: str`, `hook_type: str`, `emotional_angle: str`, `cta_style: str`, `observed_date: str`, `source_url: str | None`
- [ ] `TrendResult` dataclass — `hook_type: str`, `direction: str` (rising/falling/stable), `current_pct: float`, `previous_pct: float`, `change_pct: float`
- [ ] Add `observed_date` field to existing pattern records (backfill with initial date)

#### B. Trend Analysis

- [ ] `compute_hook_trends(patterns: list, window_months: int) -> list[TrendResult]` — Compare hook type distribution between current window and previous window
- [ ] `compute_competitor_shifts(patterns: list, competitor: str) -> list[TrendResult]` — Detect strategy changes for a specific competitor
- [ ] `get_trending_hooks(patterns: list, direction: str) -> list[str]` — Return hook types trending in given direction

#### C. Strategy Shift Alerts

- [ ] `StrategyAlert` dataclass — `competitor: str`, `alert_type: str`, `description: str`, `severity: str` (info/warning/action)
- [ ] `detect_strategy_shifts(patterns: list) -> list[StrategyAlert]` — Flag when a competitor significantly changes hook distribution, adopts new emotional angle, or abandons a CTA style
- [ ] Threshold: >15% shift in any category triggers an alert

#### D. Refresh Workflow

- [ ] `RefreshResult` dataclass — `new_patterns: int`, `updated_patterns: int`, `alerts: list[StrategyAlert]`
- [ ] `run_competitive_refresh(current_patterns: list, new_observations: list) -> RefreshResult` — Merge new observations, compute trends, generate alerts
- [ ] Deduplicate by `(competitor, source_url)` — update if re-observed, add if novel

#### E. Dashboard Data

- [ ] `get_competitive_dashboard_data(patterns: list) -> dict` — Structured data for Panel 8:
  - `hook_distribution`: hook type counts/percentages (pie/bar chart)
  - `strategy_radar`: per-competitor dimension scores
  - `gap_analysis`: opportunities where competitors are weak
  - `temporal_trends`: hook shifts over time

### Files to Create/Modify

| File | Action |
|------|--------|
| `generate/competitive_trends.py` | **Create** — Trend analysis + alerts |
| `tests/test_generation/test_competitive_trends.py` | **Create** — Tests |
| `data/competitive/patterns.json` | **Modify** — Add `observed_date` to existing records |

### Files to READ for Context

| File | Why |
|------|-----|
| `generate/competitive.py` | Existing query interface — understand current schema |
| `data/competitive/patterns.json` | Current pattern records to extend |
| `data/competitive/competitor_summaries.json` | Current competitor analysis |
| PRD Section 4.8 | Full competitive intelligence architecture |

---

## Important Context

### Architectural Decisions

| Decision | Reference | Summary |
|----------|-----------|---------|
| Structured pattern extraction | R2-Q2 | hook_type, emotional_angle, cta_style — queryable, not free-text |
| Monthly refresh cadence | Section 4.8.8 | Re-scan Meta Ad Library periodically |
| Dashboard integration | Section 4.8.7 | Hook distribution + strategy radar + gap analysis |
| Pipeline integration | Section 4.8.6 | Patterns feed brief expansion (P1-01), generation (P1-02), evaluation (P1-04) |

---

## Definition of Done

- [ ] Existing patterns have `observed_date` field
- [ ] Trend analysis detects rising/falling hook types
- [ ] Strategy shift alerts fire on >15% distribution change
- [ ] Refresh workflow merges new patterns, deduplicates, computes trends
- [ ] Dashboard data structure ready for Panel 8 visualization
- [ ] Tests verify: trend computation, alert thresholds, refresh dedup

---

## Estimated Time: 45–60 minutes
