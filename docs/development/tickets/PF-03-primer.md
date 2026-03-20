# PF-03 Primer: Critical Feature QA — Dashboard & Analytics

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** PF-01 (cleanup), PF-02 (session QA). See `docs/DEVLOG.md`.

---

## What Is This Ticket?

PF-03 is the second QA pass — focused on the dashboard, analytics, and data visualization features. It covers the global dashboard (8 tabs), session-scoped dashboard (7 tabs), and data accuracy. Like PF-02, this documents bugs; fixes are in PF-04/05.

### Why It Matters

- Dashboard panels were built across P5 tickets — each panel may have data format mismatches
- The global dashboard aggregates across all sessions — edge cases with mixed image/video data
- Session-scoped dashboard must filter correctly — wrong scope = misleading data
- Charts and visualizations may not render with edge-case data (empty sessions, single-ad sessions)

---

## What This Ticket Must Accomplish

### Goal

Test every dashboard panel and analytics view, verify data accuracy, and document bugs.

### QA Test Script

#### 1. Global Dashboard (`/dashboard`)

- [ ] Page loads without errors
- [ ] **Pipeline Summary tab:** total ads, published count, avg score, cost, throughput
- [ ] **Iteration Cycles tab:** cycle-over-cycle improvement chart, data points accurate
- [ ] **Quality Trends tab:** dimension trend lines render, scores match ledger data
- [ ] **Dimension Deep-Dive tab:** per-dimension analysis, correlation matrix displays
- [ ] **Ad Library tab:** all ads across sessions, filter by status/score, images/videos display
- [ ] **Token Economics tab:** cost breakdown by purpose, marginal analysis charts
- [ ] **System Health tab:** evaluator drift indicators, SPC charts, confidence distribution
- [ ] **Competitive Intel tab:** competitor patterns, structural atoms display
- [ ] Timeframe filter (all/day/month/year) — verify data scoping works

#### 2. Session Dashboard (from session detail view)

- [ ] **Overview tab:** stats match session results_summary (ads generated, published, score, cost)
- [ ] **Quality tab:** dimension scores for this session's ads only
- [ ] **Ad Library tab:** only this session's ads displayed, not global
- [ ] **Competitive tab:** competitive context used for this session's briefs
- [ ] **Token Economics tab:** costs scoped to this session
- [ ] **Curated Set tab:** curation specific to this session
- [ ] **System Health tab:** evaluator performance for this session

#### 3. Data Accuracy Checks

- [ ] Ad count in dashboard matches actual ledger entries
- [ ] Published/discarded counts match ledger events
- [ ] Average score calculation correct (weighted by ads_published, not simple mean)
- [ ] Cost figures match sum of token consumption in ledger
- [ ] Dimension scores match individual ad evaluations
- [ ] Video sessions: video-specific metrics accurate (videos_generated, videos_selected)

#### 4. Edge Cases

- [ ] Dashboard with no sessions — graceful empty state
- [ ] Dashboard with only image sessions — no video metrics shown
- [ ] Dashboard with only video sessions — no image metrics shown
- [ ] Dashboard with mixed image/video — both represented
- [ ] Session with 0 published ads — charts handle empty data
- [ ] Single-ad session — trends still render (even if just one point)

### Deliverables

- [ ] Append findings to `docs/development/PF-02-bug-report.md` (or create `PF-03-bug-report.md`)
- [ ] Data accuracy issues flagged separately (higher priority than cosmetic bugs)

---

## Branch & Merge Workflow

Work on `video-implementation-2.0` branch (current branch).

---

## Important Context

### Files You Should READ for Context

| File | Why |
|------|-----|
| `app/frontend/src/views/GlobalDashboard.tsx` | Global dashboard with 8 tabs |
| `app/frontend/src/views/SessionDetail.tsx` | Session-scoped dashboard |
| `app/frontend/src/tabs/Overview.tsx` | Overview metrics |
| `app/frontend/src/tabs/Quality.tsx` | Quality dimension charts |
| `app/frontend/src/tabs/AdLibrary.tsx` | Ad library with filters |
| `app/frontend/src/tabs/TokenEconomics.tsx` | Cost analytics |
| `output/export_dashboard.py` | Backend data export for dashboards |

### Files You Should NOT Modify

- Do NOT fix bugs — document them for PF-04/05

---

## Definition of Done

- [ ] All dashboard tabs tested in global and session context
- [ ] Data accuracy verified against ledger data
- [ ] Edge cases tested
- [ ] Bug report updated with findings
- [ ] DEVLOG updated

---

## Estimated Time

| Task | Estimate |
|------|----------|
| Global dashboard QA (8 tabs) | 20 min |
| Session dashboard QA (7 tabs) | 15 min |
| Data accuracy checks | 10 min |
| Edge cases | 10 min |
| Bug report | 10 min |
| DEVLOG | 5 min |

---

## After This Ticket: What Comes Next

- **PF-04:** Frontend bug fixes (using PF-02 + PF-03 bug reports)
- **PF-05:** Backend bug fixes
