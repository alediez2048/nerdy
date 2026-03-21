# Phase PD: Pipeline Debt — Consistency, Integrity & Honest Architecture

## Context

After completing P0–P5 and the application layer (PA/PB/PC), a comprehensive audit revealed 23 inconsistencies across the codebase. These range from critical runtime bugs to architectural promises that were designed but never wired into the active pipeline. Phase PD addresses these honestly: fixing what's broken, removing what's dead, and documenting what's intentionally deferred.

**North star:** The system should never lie about what it does. If a config field isn't used, don't collect it. If a dashboard tab has no data for a session type, say so. If a module is implemented but not integrated, document it.

## Tickets (8)

### PD-01: Critical Bug Fixes
- Fix `tokens_estimate` undefined variable in `evaluate/evaluator.py:561` (→ `tokens_actual`)
- Compute real `avg_score` in image pipeline results (currently hardcoded to 7.0)
- Propagate real `current_score_avg` in progress events (currently hardcoded to 7.0)
- **AC:** No hardcoded 7.0 in pipeline results or progress events; evaluator doesn't crash on log

### PD-02: Unified Dashboard with Content-Type Filter
- Add content-type filter/toggle to session-level and global dashboards: **All | Copy | Image | Video**
- Each `_build_*` function in `export_dashboard.py` accepts an optional `content_type` filter and returns type-appropriate data
- Pipeline Summary counts `VideoSelected`/`VideoBlocked` alongside `AdPublished`/`AdDiscarded`
- Quality Trends, Iteration Cycles, Dimension Deep-Dive: adapt columns and metrics based on active filter (5 text dimensions for copy/image, composite + attribute % + coherence for video)
- System Health: handle missing per-dimension confidence for video sessions
- Add `video_scores` to TypeScript `Ad` interface in `GlobalDashboard.tsx`
- Frontend panels render type-appropriate columns based on active filter — no empty panels, no "N/A" banners
- **AC:** Dashboard shows relevant, complete data for any content-type filter selection; mixed sessions aggregate correctly under "All"

### PD-03: Dead Config Cleanup
- Remove or disable `model_tier`, `budget_cap_usd`, `dimension_weights` from `NewSessionForm.tsx` (pipeline ignores them)
- Either wire 9 video prompt framework fields (`video_scene`, `video_visual_style`, etc.) through `video_spec.py` or remove from form
- Add "not yet implemented" tooltips for any fields kept for future use
- **AC:** Every config field the user can set is either used by the pipeline or clearly marked as planned

### PD-04: Video Evaluation Consolidation
- Choose ONE video evaluation path: `video_evaluator.py` (real API calls) vs `video_attributes.py` + `video_coherence.py` (placeholders)
- Delete the unused path; resolve the 5-attribute vs 10-attribute and 4.0 vs 6.0 threshold conflicts
- Fix composite score normalization: `attr_pct * 0.4 + (coherence_avg / 10) * 0.6` (currently mixing 0–1 and 1–10 scales)
- **AC:** Single canonical video evaluation with consistent thresholds and normalized scoring

### PD-05: Curated Set Video Support + Content-Type Filter
- Add `<video>` rendering to `CuratedSet.tsx` tab (reuse pattern from `AdLibrary.tsx`)
- Include video preview in curated export ZIP
- Add content-type filter to curated set view (consistent with PD-02 dashboard filter)
- **AC:** Video ads display and export correctly in curation workflow; filter matches dashboard UX

### PD-06: Pipeline Iteration Wiring
- Wire `quality_ratchet.py` into `batch_processor.py` (replace hardcoded `batch_average: 7.0`)
- Wire `pareto_selection.py` into regeneration path
- Enforce `model_router.py` routing decisions (actually re-generate with Pro when escalated)
- Create `iterate/feedback_loop.py` — the orchestrator that ties ratchet + Pareto + routing + brief mutation
- **AC:** Pipeline executes at least 1 regeneration cycle for ads scoring 5.5–7.0; quality ratchet tracks real batch averages

### PD-07: Cost Tracking Completion
- Validate new token capture works (run 1-ad test session, verify `tokens_consumed` > 0)
- Backfill historical session costs per plan in `COST_TRACKING_ISSUES.md`
- Add "Estimated" vs "Actual" labels to cost displays
- Remove `HISTORICAL_SPEND_USD` once all sessions have real cost data
- **AC:** Per-session cost matches billing within ±15%; no hardcoded baseline in production code

### PD-08: Honest Architecture Documentation
- Update `systemsdesign.md` to distinguish "implemented" vs "integrated" for iterate/ modules
- Add decision log entry for Phase PD: why these gaps exist and what the fix plan is
- Update `MEMORY.md` with PD phase status
- **AC:** A reader of the docs knows exactly what works end-to-end vs what's implemented-but-not-wired

## Dependency Graph

```
PD-01 (Critical Bugs)
  │
  ├─→ PD-02 (Dashboard Video Support)
  │     │
  │     └─→ PD-05 (Curated Set Video)
  │
  ├─→ PD-04 (Video Eval Consolidation)
  │     │
  │     └─→ PD-02 (Dashboard needs canonical video scores)
  │
  ├─→ PD-06 (Pipeline Iteration Wiring)
  │     │
  │     └─→ PD-07 (Cost Tracking — needs real token flow)
  │
  ├─→ PD-03 (Dead Config Cleanup) — independent
  │
  └─→ PD-08 (Documentation) — after all others
```

## Priority Order

1. **PD-01** — Critical bugs, 30 min, unblocks everything
2. **PD-04** — Video eval consolidation, 1 hr, unblocks PD-02
3. **PD-02** — Unified dashboard with content-type filter, 3 hrs
4. **PD-03** — Dead config cleanup, 1 hr (independent)
5. **PD-05** — Curated set video, 30 min
6. **PD-06** — Pipeline iteration wiring, 3-4 hrs (largest ticket)
7. **PD-07** — Cost tracking completion, 2 hrs
8. **PD-08** — Documentation, 1 hr (do last)

## Key Principle

> "Don't pretend. Fix what's broken, remove what's dead, document what's deferred."

## Status: ⏳ PENDING
