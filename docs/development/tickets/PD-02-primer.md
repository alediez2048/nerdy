# PD-02 Primer: Unified Dashboard with Content-Type Filter

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** P5-01 (dashboard export), PC-01 through PC-05 (video pipeline), PD-01 (bug fixes), PD-04 (video eval consolidation). See `docs/DEVLOG.md`.

---

## What Is This Ticket?

The dashboard was designed for image sessions with 5-dimension text scoring. Video sessions use a completely different scoring structure (binary attributes + coherence), causing 5 of 7 tabs to show empty or broken data. Rather than bolting "N/A" banners onto panels that don't apply, PD-02 adds a **content-type filter** to both session-level and global dashboards. When the user selects a content type (All | Copy | Image | Video), every panel adapts its columns, metrics, and visualizations to show complete, relevant data for that type.

This follows the same pattern as `SessionFilters` (which already filters by status, type, audience, goal) — extending it to the dashboard level so every panel is always showing meaningful data instead of empty grids.

### Why It Matters
- Users running video sessions currently see a dashboard with mostly empty panels — it looks broken and erodes trust.
- Pipeline Summary undercounts published/discarded ads because it ignores `VideoSelected`/`VideoBlocked` events.
- Quality Trends, Dimension Deep-Dive, and System Health show zero data for video sessions.
- A unified filter is cleaner than per-panel conditionals or separate dashboards per type.
- Violates Pillar 8 (The Reviewer Is a User, Too) and Pillar 9 (The Tool Is the Product).

---

## What Was Already Done

- `_build_ad_library()` in `export_dashboard.py` already handles `VideoSelected` as published and `VideoBlocked` as discarded.
- `AdLibrary.tsx` already renders `<video>` elements and `video_scores` for video ads.
- `SessionFilters.tsx` already implements a filter pattern (status chips, type chips, dropdown filters) that can be extended.
- `Overview.tsx` already switches metrics based on `sessionType === 'video'`.
- `evaluate/video_evaluator.py` defines the canonical video score structures after PD-04.

---

## What This Ticket Must Accomplish

### Goal

Add a content-type filter (All | Copy | Image | Video) to session-level and global dashboards so every panel renders type-appropriate, complete data based on the active filter.

### Deliverables Checklist

#### A. Backend — `output/export_dashboard.py`

- [ ] Add `content_type: str | None = None` parameter to `build_dashboard_data()` and `build_dashboard_data_from_events()`
- [ ] Add `_filter_events_by_content_type(events, content_type)` helper that filters events:
  - `"copy"` → `AdGenerated`, `AdEvaluated`, `AdPublished`, `AdDiscarded` (text-only events)
  - `"image"` → above + `ImageGenerated`, `ImageEvaluated`, `AspectRatioGenerated`
  - `"video"` → `VideoGenerated`, `VideoEvaluated`, `VideoSelected`, `VideoBlocked`, `VideoCoherenceChecked`
  - `None` / `"all"` → all events (no filter)
- [ ] **Pipeline Summary (`_build_pipeline_summary`):** Count `VideoSelected` as published, `VideoBlocked` as discarded. When filtered to video, show video-specific KPIs (videos_generated, videos_selected, videos_blocked, avg composite score). When "all", aggregate across types.
- [ ] **Iteration Cycles (`_build_iteration_cycles`):** When filtered to video, show per-ad video evaluation data (attribute pass %, coherence score) instead of multi-cycle 5-dimension iteration. Videos are single-pass — show the evaluation result, not an empty iteration table.
- [ ] **Quality Trends (`_build_quality_trends`):** When filtered to video, use video composite scores in the score distribution histogram. When "all", merge both score types into the distribution.
- [ ] **Dimension Deep-Dive (`_build_dimension_deep_dive`):** When filtered to video, return video-specific dimension data: per-attribute pass rates (hook_timing, ugc_authenticity, pacing, text_legibility, no_artifacts) and per-coherence-dimension averages (message_alignment, audience_match, emotional_consistency, narrative_flow). Skip the 5-dimension correlation matrix. When "all", return both structures.
- [ ] **System Health (`_build_system_health`):** When filtered to video, skip per-dimension confidence routing (videos don't have it). Show video-specific health: attribute pass rate trend, coherence score trend, video generation failure rate.
- [ ] **Token Economics (`_build_token_economics`):** Already content-type agnostic (groups by model). No changes needed — filter just reduces the events fed in.

#### B. Backend — API Routes

- [ ] `app/api/routes/dashboard.py` — Add `content_type` query parameter to session-level dashboard endpoints (`get_summary`, `get_cycles`, `get_dimensions`, `get_costs`, `get_ads`, `get_spc`) and pass through to `build_dashboard_data()`.
- [ ] `app/api/routes/dashboard.py` — Add `content_type` query parameter to `get_global_dashboard()` and pass through to `build_dashboard_data_from_events()`.

#### C. Frontend — Filter Component

- [ ] Create `ContentTypeFilter` component (or extend existing `SessionFilters`): row of chips — All | Copy | Image | Video. Active chip highlighted. Callback `onFilterChange(type: string)`.
- [ ] Add `ContentTypeFilter` to `SessionDetail.tsx` above the tab bar. Pass selected type as query param to all dashboard API calls.
- [ ] Add `ContentTypeFilter` to `GlobalDashboard.tsx` alongside existing timeframe selector. Pass selected type to `fetchGlobalDashboard()`.
- [ ] Update `api/dashboard.ts` — all fetch functions accept optional `contentType` parameter, append `?content_type=<value>` to URL.

#### D. Frontend — Panel Adaptations

- [ ] **GlobalDashboard.tsx `Ad` interface:** Add `video_scores?: { composite_score: number; attribute_pass_pct: number; coherence_avg: number } | null` and `video_url?: string | null`.
- [ ] **Pipeline Summary panel:** When backend returns video KPIs, render video-specific metric cards (Videos Generated, Videos Selected, Videos Blocked, Avg Composite) instead of the 5-dimension text metrics.
- [ ] **Quality Trends panel:** Score distribution histogram works with any numeric scores — just needs data from backend. No structural change needed.
- [ ] **Dimension Deep-Dive panel:** When backend returns `video_dimensions` instead of `dimension_trends`, render video attribute pass rates as a bar chart and coherence dimension averages as a separate bar chart. Skip correlation matrix.
- [ ] **Ad Library score grid:** When `ad.video_scores` is present, render 3-column grid (Composite, Attr%, Coherence) instead of 5-column grid. Already partially done in `AdLibrary.tsx`.
- [ ] **System Health panel:** When backend returns video health data, render attribute trend and coherence trend instead of confidence routing pie chart.

#### E. Tests

- [ ] Test `_filter_events_by_content_type()` with mixed events — verify correct filtering for each type.
- [ ] Test `_build_pipeline_summary` with `content_type="video"` — verify VideoSelected/VideoBlocked counted correctly.
- [ ] Test `_build_quality_trends` with `content_type="video"` — verify non-empty score distribution.
- [ ] Test `_build_dimension_deep_dive` with `content_type="video"` — verify video dimensions returned, no crash.
- [ ] Test `content_type="all"` aggregates across both types.
- [ ] Verify existing dashboard tests still pass (no regressions for image-only).

#### F. Documentation

- [ ] Add PD-02 entry to `docs/development/DEVLOG.md`.

---

## Important Context

### Files to Create

| File | Why |
|------|-----|
| `app/frontend/src/components/ContentTypeFilter.tsx` | Reusable filter component for dashboard content-type selection |

### Files to Modify

| File | Action |
|------|--------|
| `output/export_dashboard.py` | Add `content_type` parameter to all `_build_*` functions; add `_filter_events_by_content_type()` helper; adapt each panel for video data |
| `app/api/routes/dashboard.py` | Add `content_type` query parameter to all dashboard endpoints |
| `app/frontend/src/views/GlobalDashboard.tsx` | Add ContentTypeFilter; update Ad interface; adapt panels for video data |
| `app/frontend/src/views/SessionDetail.tsx` | Add ContentTypeFilter above tab bar; pass content_type to dashboard API calls |
| `app/frontend/src/api/dashboard.ts` | Add `contentType` parameter to all fetch functions |
| `app/frontend/src/tabs/AdLibrary.tsx` | Verify video score grid rendering in expanded view |
| `tests/test_output/test_export_dashboard.py` | Add content-type filter tests |

### Files You Should READ for Context

| File | Why |
|------|-----|
| `evaluate/video_evaluator.py` | Canonical video score structures after PD-04 |
| `app/workers/tasks/pipeline_task.py` | Video event payloads — `VideoSelected` (~line 459), `VideoBlocked` (~line 483) |
| `app/frontend/src/components/SessionFilters.tsx` | Existing filter pattern to follow for ContentTypeFilter |
| `app/frontend/src/tabs/Overview.tsx` | Already handles `sessionType === 'video'` — reference for conditional rendering |
| `output/export_dashboard.py` lines 332-420 | `_build_ad_library` already handles video events — reference pattern |

### Dependencies

- **PD-01** must be completed first (real scores must flow before dashboard can aggregate them).
- **PD-04** (video eval consolidation) provides the canonical score structure. If PD-04 is not done yet, use existing `VideoEvalResult`/`VideoCoherenceResult` from `evaluate/video_evaluator.py`.

---

## Architectural Decision: Why a Unified Filter Over Separate Dashboards

**Options considered:**
- **A. Per-panel "N/A" banners** — Least work, but panels that say "not applicable" are useless UI real estate.
- **B. Separate dashboards per content type** — Clean per-type views, but 3 UIs to maintain and a fragmented experience.
- **C. Unified dashboard with content-type filter (chosen)** — Single view, filter adapts all panels. Follows existing filter pattern (`SessionFilters`). Each panel is always showing complete, relevant data for the selected type.

**Why C wins:** It's the natural extension of how the app already works. SessionList has filters. GlobalDashboard has a timeframe selector. Adding a content-type filter is the same UX pattern. Users don't need to navigate to a different page to see video vs image metrics — they toggle a filter.

---

## Definition of Done

- [ ] Content-type filter (All | Copy | Image | Video) appears on session-level and global dashboards.
- [ ] Selecting "Video" shows video-specific metrics in all panels — no empty grids, no "N/A".
- [ ] Selecting "All" aggregates across content types correctly.
- [ ] Pipeline Summary counts `VideoSelected` as published, `VideoBlocked` as discarded.
- [ ] Quality Trends histogram includes video composite scores when "Video" or "All" selected.
- [ ] Dimension Deep-Dive shows video attribute/coherence data when "Video" selected.
- [ ] Ad Library renders 3-column video score grid for video ads.
- [ ] `GlobalDashboard.tsx` `Ad` interface includes `video_scores` and `video_url`.
- [ ] All existing dashboard tests pass; new tests cover content-type filtering.
- [ ] DEVLOG updated.

---

## Estimated Time

| Task | Estimate |
|------|----------|
| Backend: `_filter_events_by_content_type()` + wire to all `_build_*` | 45 min |
| Backend: API route query params | 15 min |
| Frontend: ContentTypeFilter component | 15 min |
| Frontend: Wire filter to SessionDetail + GlobalDashboard | 15 min |
| Frontend: Panel adaptations (Pipeline Summary, Dim Deep-Dive, System Health) | 45 min |
| Frontend: Ad interface + score grid | 15 min |
| Tests | 30 min |
| **Total** | **~3 hours** |

---

## After This Ticket: What Comes Next

- **PD-05** (Curated Set Video + Filter) — extends the same content-type filter pattern to the curation workflow.
- With PD-02 complete, every dashboard view shows relevant data regardless of session type.
