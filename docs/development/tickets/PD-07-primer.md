# PD-07 Primer: Cost Tracking Completion

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** PD-01 (tokens_estimate bug fix). See `docs/DEVLOG.md` and `docs/development/COST_TRACKING_ISSUES.md`.

---

## What Is This Ticket?

Cost tracking has known data integrity issues accumulated across multiple phases. Past sessions logged `tokens_consumed: 0` for all Gemini API calls because the code discarded `usage_metadata`. Video costs from Fal.ai have no billing API, so per-call costs are estimates. A hardcoded `HISTORICAL_SPEND_USD = 84.68` baseline is applied to global and campaign dashboards as a workaround. Multiple cascading fix attempts created inconsistent cost display across session, campaign, and global views.

Several root causes have already been fixed (token capture, model cost rates, per-call routing), but the data from 12 existing sessions still shows zero cost, and the display layer has not been unified. This ticket completes the cost tracking story end-to-end: validate the fixes, backfill historical sessions, unify the display, add accuracy guardrails, and clean up the baseline workaround.

### Why It Matters

- Users see `$0.00` cost for historical sessions, undermining trust in the dashboard.
- The `HISTORICAL_SPEND_USD` baseline is a hardcoded magic number that will drift further from reality as new sessions run.
- Inconsistent display logic across session/campaign/global views means the same cost data renders differently depending on where you look.
- Without a backfill, 12 sessions of cost data are permanently lost, making campaign-level ROI analysis impossible.

---

## What Was Already Done

- `generate/gemini_client.py` now captures `usage_metadata.total_token_count` (fixed in PD-01).
- `MODEL_COST_RATES` updated with invoice-derived rates (`$0.28/video call` from Fal.ai invoices).
- Global dashboard applies `$84.68` baseline from real billing data.
- `compute_event_cost()` correctly routes per-token vs per-call pricing.
- Root cause analysis documented in `docs/development/COST_TRACKING_ISSUES.md` (Phases 1-5).

---

## What This Ticket Must Accomplish

### Goal

Complete cost tracking so every session (historical and new) displays accurate or clearly-labeled estimated costs, with guardrails to prevent regression.

### Deliverables Checklist

#### A. Validate (`evaluate/cost_reporter.py`, pipeline)

- [ ] Run 1-ad image session, verify `tokens_consumed > 0` in the session ledger.
- [ ] Run 1-video session, verify `VideoGenerated` event has correct `model_used`.
- [ ] Compare computed cost with billing delta to confirm accuracy within 10%.

#### B. Backfill (`scripts/backfill_session_costs.py`)

- [ ] For each of the 12 existing sessions, estimate cost from ad count x avg tokens per ad.
- [ ] Write migration script (`scripts/backfill_session_costs.py`) to update `session.results_summary.cost_so_far` in the DB.
- [ ] Script must be idempotent (safe to run multiple times).
- [ ] Log which sessions were backfilled and with what estimated amounts.

#### C. Display (`app/frontend/src/tabs/Overview.tsx`, `app/frontend/src/tabs/TokenEconomics.tsx`)

- [ ] Session Overview tab shows cost from `results_summary` (backfilled) OR computed from ledger (new sessions).
- [ ] Add "Estimated" label for backfilled sessions vs "Actual" label for new sessions with real token data.
- [ ] Campaign and global dashboards sum session costs consistently.

#### D. Accuracy Guardrails (`app/api/routes/dashboard.py`, `evaluate/cost_reporter.py`)

- [ ] Pre-commit or lint check that no new `tokens_consumed: 0` hardcodes are added.
- [ ] Health check endpoint comparing computed total with `HISTORICAL_SPEND_USD` and flagging drift > 15%.

#### E. Cleanup

- [ ] Once all sessions have real or backfilled cost data, remove `HISTORICAL_SPEND_USD` constant and baseline fallback code.
- [ ] Remove any dead code paths that were part of earlier cascading fix attempts.

#### F. Documentation

- [ ] Add PD-07 entry to `docs/development/DEVLOG.md`.
- [ ] Update `docs/development/COST_TRACKING_ISSUES.md` to mark completed phases.

---

## Important Context

### Files to Create

| File | Why |
|------|-----|
| `scripts/backfill_session_costs.py` | Migration script to estimate and write cost data for 12 historical sessions (create new or update if it already exists) |

### Files to Modify

| File | Action |
|------|--------|
| `evaluate/cost_reporter.py` | Add health check comparison logic, validate compute path |
| `app/api/routes/dashboard.py` | Add health check endpoint, remove `HISTORICAL_SPEND_USD` fallback after backfill |
| `app/api/routes/campaigns.py` | Ensure campaign cost aggregation uses session-level costs consistently |
| `app/frontend/src/tabs/Overview.tsx` | Show cost with "Estimated" / "Actual" label based on data source |
| `app/frontend/src/tabs/TokenEconomics.tsx` | Unify cost display with session-level data |
| `docs/development/DEVLOG.md` | Add PD-07 entry |
| `docs/development/COST_TRACKING_ISSUES.md` | Mark completed phases |

### Files You Should READ for Context

| File | Why |
|------|-----|
| `docs/development/COST_TRACKING_ISSUES.md` | Full root cause analysis and phased remediation plan — this is the source of truth for what needs doing |
| `data/cost_manifest.json` | Cost rate definitions and historical data (if it exists) |
| `generate/gemini_client.py` | Verify token capture is working correctly post-PD-01 |
| `app/workers/tasks/pipeline_task.py` | See how `cost_so_far` flows into `results_summary` |
| `output/export_dashboard.py` | See how global dashboard currently computes cost totals |

---

## Edge Cases to Handle

1. Sessions with zero ads produced (cost should be non-zero if API calls were made but all ads discarded).
2. Video-only sessions where all cost is per-call estimates, not per-token.
3. Sessions that crashed mid-run and have partial ledger data.
4. Backfill script run against a DB that already has some sessions with real cost data — must not overwrite real data with estimates.

---

## Definition of Done

- [ ] New sessions log `tokens_consumed > 0` for all Gemini API calls.
- [ ] All 12 historical sessions have backfilled cost estimates in `results_summary.cost_so_far`.
- [ ] Session Overview tab displays cost with appropriate "Estimated" or "Actual" label.
- [ ] Campaign and global dashboards show consistent cost totals.
- [ ] `HISTORICAL_SPEND_USD` baseline and fallback code removed.
- [ ] Health check endpoint validates cost accuracy.
- [ ] All tests pass (`python -m pytest tests/ -v`).
- [ ] Lint clean (`ruff check . --fix`).
- [ ] DEVLOG updated.

---

## Estimated Time

| Task | Estimate |
|------|----------|
| Validate token capture + video cost | 15 min |
| Backfill script | 30 min |
| Display unification (Overview + TokenEconomics) | 30 min |
| Accuracy guardrails + health check | 20 min |
| Cleanup (remove baseline, dead code) | 10 min |
| Documentation | 10 min |
| **Total** | **~2 hours** |

---

## After This Ticket: What Comes Next

- PD-08 (Honest Architecture Documentation) depends on this and all other PD tickets being complete.
- Once cost tracking is accurate, campaign ROI analysis becomes meaningful in the dashboard.
