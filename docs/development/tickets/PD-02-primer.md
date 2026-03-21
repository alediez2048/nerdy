# PD-02 Primer: Dashboard Video Session Support

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** P5-01 (dashboard export), PC-01 through PC-05 (video pipeline), PD-01 (bug fixes). See `docs/DEVLOG.md`.

---

## What Is This Ticket?

The 8-panel HTML dashboard was designed for image sessions that use a 5-dimension text scoring model (clarity, value_proposition, cta, brand_voice, emotional_resonance). Video sessions use a completely different scoring structure: binary attribute checks (hook_timing, ugc_authenticity, pacing, text_legibility, no_artifacts) plus a coherence score. This mismatch causes 5 of 7 dashboard tabs to show empty or broken data for video-only sessions.

The backend already emits `VideoSelected` and `VideoBlocked` events and the `AdLibrary` tab partially handles them, but the aggregation functions in `export_dashboard.py` and the TypeScript types in `GlobalDashboard.tsx` do not account for video scoring. This ticket bridges that gap so the dashboard renders meaningful data for both session types.

### Why It Matters
- Users running video sessions see a dashboard with mostly empty panels — it looks broken.
- Pipeline Summary undercounts published/discarded ads because it ignores `VideoSelected`/`VideoBlocked` events.
- Quality Trends and Dimension Deep-Dive panels show zero data since videos produce no `AdEvaluated` events with 5-dimension scores.
- Violates Pillar 8 (The Reviewer Is a User, Too) — the dashboard must be useful regardless of session type.
- Violates Pillar 9 (The Tool Is the Product) — broken panels erode trust.

---

## What Was Already Done

- `_build_ad_library()` in `export_dashboard.py` (lines 387-394) already handles `VideoSelected` as published and `VideoBlocked` as discarded for status determination.
- `AdLibrary.tsx` (line 18-19) already has `video_url` and `video_scores` optional fields in its local `Ad` interface.
- `app/workers/progress.py` defines video-specific event types: `VIDEO_PIPELINE_START`, `VIDEO_AD_START`, `VIDEO_GENERATING`, `VIDEO_EVALUATING`, `VIDEO_AD_COMPLETE`, `VIDEO_PIPELINE_COMPLETE`.
- `evaluate/video_evaluator.py` defines the canonical video score structures: `VideoEvalResult` (5 binary attributes + `attribute_pass_pct`) and `VideoCoherenceResult` (dimension scores + `avg_score`).
- Pipeline task emits `VideoSelected` and `VideoBlocked` events with video scores embedded.

---

## What This Ticket Must Accomplish

### Goal
Make all dashboard panels render meaningful data for video sessions by recognizing video event types and video score structures.

### Deliverables Checklist

#### A. Implementation

**Backend — `output/export_dashboard.py`:**
- [ ] **Panel 1 — Pipeline Summary (`_build_pipeline_summary`):** Count `VideoSelected` events as published and `VideoBlocked` events as discarded, in addition to existing `AdPublished`/`AdDiscarded` counts. Include video composite scores in `avg_score` computation.
- [ ] **Panel 2 — Iteration Cycles (`_build_iteration_cycles`):** Videos do not produce multi-cycle `AdEvaluated` events. For video ads, either show a single-cycle entry with attribute pass percentage and coherence score, or display an honest "N/A — video ads are single-pass" indicator.
- [ ] **Panel 3 — Quality Trends (`_build_quality_trends`):** Include video composite scores (derived from `attribute_pass_pct` and coherence `avg_score`) in the `all_eval_scores` distribution histogram so video sessions have populated score buckets.
- [ ] **Panel 4 — Dimension Deep-Dive (`_build_dimension_deep_dive`):** The correlation matrix requires exactly 5 dimensions and uses `DIMENSIONS` tuple. For video sessions, either show video-specific metrics (attribute_pass_pct, coherence_avg, per-attribute pass rates) in a separate structure, or return an explicit `"video_mode": true` flag so the frontend can show an appropriate banner.
- [ ] **Panel 6 — System Health (`_build_system_health` if it exists):** Handle missing per-dimension confidence scores for video sessions. Avoid showing 0% across the board — show "N/A" or video-appropriate health metrics.

**Frontend — `app/frontend/src/views/GlobalDashboard.tsx`:**
- [ ] **Ad interface (lines 40-55):** Add optional `video_scores` field (`Record<string, number> | null`) and optional `video_url` field (`string | null`) to the `Ad` interface.
- [ ] **Ad Library score grid (lines 567-573):** When `ad.video_scores` is present, render video-specific score columns (composite_score, attribute_pass_pct, coherence_avg) instead of the 5-dimension image grid. Use `gridTemplateColumns: 'repeat(3, 1fr)'` for video ads.

**Frontend — `app/frontend/src/tabs/AdLibrary.tsx`:**
- [ ] Verify the existing `video_scores` field in the local `Ad` interface is used in the score rendering section. If the expanded ad detail still renders a 5-column grid unconditionally, add a conditional branch for video ads.

#### B. Tests
- [ ] Add test for `_build_pipeline_summary` with mixed image + video events verifying correct published/discarded counts.
- [ ] Add test for `_build_quality_trends` with video-only events verifying non-empty score distribution.
- [ ] Add test for `_build_dimension_deep_dive` with video-only events verifying it does not crash and returns a meaningful structure (even if `"video_mode": true`).
- [ ] Verify existing dashboard tests in `tests/test_output/test_export_dashboard.py` still pass (they already contain `VideoSelected`/`VideoBlocked` fixtures at lines 237 and 266).

#### C. Integration Expectations
- [ ] A video-only session produces a dashboard with non-empty data in all 7 tabs.
- [ ] A mixed image+video session produces correct aggregated data across both types.
- [ ] No regressions in image-only session dashboards.

#### D. Documentation
- [ ] Add PD-02 entry to `docs/development/DEVLOG.md`.

---

## Important Context

### Files to Modify

| File | Action |
|------|--------|
| `output/export_dashboard.py` | Update `_build_pipeline_summary`, `_build_iteration_cycles`, `_build_quality_trends`, `_build_dimension_deep_dive`, and system health to handle video events and scores |
| `app/frontend/src/views/GlobalDashboard.tsx` | Add `video_scores` and `video_url` to `Ad` interface; conditionally render video score grid |
| `app/frontend/src/tabs/AdLibrary.tsx` | Ensure expanded ad detail renders video scores when present |

### Files You Should READ for Context

| File | Why |
|------|-----|
| `evaluate/video_evaluator.py` | Canonical video score structures: `VideoEvalResult` (5 binary attributes, `attribute_pass_pct`) and `VideoCoherenceResult` (dimensions, `avg_score`, `is_coherent`) |
| `app/workers/tasks/pipeline_task.py` | Video event emission — see `VideoSelected` (~line 459) and `VideoBlocked` (~line 483) event payloads to know what fields are available |
| `app/workers/progress.py` | Video-specific progress event type constants (lines 30-36) |
| `tests/test_output/test_export_dashboard.py` | Existing test fixtures with `VideoSelected`/`VideoBlocked` events (lines 237, 266) — extend these |
| `output/export_dashboard.py` lines 332-420 | `_build_ad_library` already handles video status — reference this pattern |

### Dependencies
- **PD-01** must be completed first (bug fixes — real scores must flow before dashboard can aggregate them).
- **PD-04** (video eval consolidation) provides the canonical score structure. If PD-04 is not done yet, use the existing `VideoEvalResult`/`VideoCoherenceResult` structures from `evaluate/video_evaluator.py` as the source of truth.

---

## Definition of Done

- [ ] Pipeline Summary counts `VideoSelected` as published and `VideoBlocked` as discarded.
- [ ] Quality Trends score histogram includes video composite scores.
- [ ] Dimension Deep-Dive does not crash for video-only sessions; shows video metrics or N/A banner.
- [ ] `GlobalDashboard.tsx` `Ad` interface includes `video_scores` and `video_url` fields.
- [ ] Ad Library score grid conditionally renders 3-column video scores vs 5-column image scores.
- [ ] All existing dashboard tests pass; new tests cover video-specific panel logic.
- [ ] DEVLOG updated.

---

## Estimated Time

| Task | Estimate |
|------|----------|
| Pipeline Summary — add video event counting | 15 min |
| Iteration Cycles — video-aware logic or N/A banner | 15 min |
| Quality Trends — include video composite scores | 15 min |
| Dimension Deep-Dive — video metrics or N/A flag | 20 min |
| System Health — handle missing confidence scores | 10 min |
| GlobalDashboard.tsx — type updates + conditional grid | 15 min |
| AdLibrary.tsx — verify/fix score rendering | 10 min |
| Tests | 20 min |
| **Total** | **2 hours** |
