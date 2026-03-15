# PA-08 Primer: Watch Live Progress View (React)

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** PA-07 (Progress Reporting) must be complete — SSE hook available. See `docs/DEVLOG.md`.

---

## What Is This Ticket?

PA-08 builds the **"Watch Live" progress view** — an SSE-powered real-time dashboard that shows a pipeline run in progress. Six live elements update as events stream in (R5-Q4, Section 4.7.5).

### Why It Matters

- **Visible Reasoning Is a First-Class Output** (Pillar 7): Users watch the system think in real time
- Pipeline runs take minutes — without a live view, users have no idea what's happening
- The live score feed and quality trend chart demonstrate the quality improvement loop in action
- Auto-redirect on completion takes users straight to the full dashboard

---

## What Was Already Done

- PA-07: `useSessionProgress(sessionId)` React hook — connects to SSE, returns typed `ProgressEvent`
- PA-07: SSE endpoint streams events at every pipeline stage boundary
- PA-06: Session list with "Watch Live" button for running sessions
- Design tokens and component library from PA-05

---

## What This Ticket Must Accomplish

### Goal

Build the Watch Live page with 6 real-time elements that update from the SSE stream, plus auto-redirect on pipeline completion.

### Deliverables Checklist

#### A. Watch Live Page (`src/views/WatchLive.tsx`)

- [ ] Route: `/sessions/{sessionId}/live`
- [ ] Uses `useSessionProgress(sessionId)` hook
- [ ] Displays 6 live elements (below)
- [ ] Connection status indicator (connected / reconnecting / error)
- [ ] "Back to Sessions" navigation
- [ ] Auto-redirect to session detail on `PIPELINE_COMPLETE` event

#### B. Six Live Elements

1. **Cycle Indicator** (`src/components/progress/CycleIndicator.tsx`)
   - [ ] Shows current cycle out of total (e.g., "Cycle 2/5")
   - [ ] Visual progress ring or step indicator
   - [ ] Highlights current cycle, shows completed cycles as done

2. **Ad Count Progress Bar** (`src/components/progress/AdCountBar.tsx`)
   - [ ] Shows ads generated / ads target (e.g., "25/50 generated")
   - [ ] Second bar: ads published / ads generated
   - [ ] Animated fill on each `AD_GENERATED` / `AD_PUBLISHED` event

3. **Live Score Feed** (`src/components/progress/ScoreFeed.tsx`)
   - [ ] Scrolling list of recent `AD_EVALUATED` events
   - [ ] Each entry: ad number, score, pass/fail indicator
   - [ ] Color-coded: green ≥ 7.0, yellow 5.5–7.0, red < 5.5
   - [ ] Auto-scrolls to newest

4. **Running Cost Accumulator** (`src/components/progress/CostAccumulator.tsx`)
   - [ ] Displays `cost_so_far` as animating counter
   - [ ] Shows cost per published ad (updates as ads publish)
   - [ ] Budget bar if budget cap was set in config

5. **Live Quality Trend Chart** (`src/components/progress/QualityTrend.tsx`)
   - [ ] Line chart showing `current_score_avg` over time/events
   - [ ] Updates on each `AD_EVALUATED` or `CYCLE_COMPLETE` event
   - [ ] Horizontal reference line at 7.0 threshold
   - [ ] Simple SVG or lightweight chart (Chart.js via CDN if needed)

6. **Latest Ad Preview** (`src/components/progress/LatestAdPreview.tsx`)
   - [ ] Shows the most recently evaluated ad's copy (if included in event data)
   - [ ] Dimension scores displayed as mini bars
   - [ ] Pass/fail badge
   - [ ] Fades in on each new evaluation

#### C. Responsive Layout

- [ ] Grid layout: 2x3 on desktop, stacked on mobile
- [ ] Dark theme matching design tokens (ink/surface backgrounds)
- [ ] Smooth animations for updating values

#### D. Tests

- [ ] Test all 6 elements render with mock progress data
- [ ] Test elements update when new events arrive
- [ ] Test auto-redirect on pipeline completion
- [ ] Test connection error state displays correctly
- [ ] Minimum: 4+ tests

#### E. Documentation

- [ ] Add PA-08 entry in `docs/DEVLOG.md`

---

## Important Context

### Watch Live Spec (PRD Section 4.7.5)

> "Watch Live" (optional): SSE-powered dashboard: cycle indicator, ads generated progress bar, live score feed, running cost accumulator, live quality trend chart, latest ad preview.

### Event Types & What They Update

| Event Type | Elements Updated |
|------------|-----------------|
| `cycle_start` | Cycle Indicator |
| `batch_start` | — |
| `ad_generated` | Ad Count Bar |
| `ad_evaluated` | Score Feed, Quality Trend, Latest Ad Preview |
| `ad_published` | Ad Count Bar, Cost Accumulator |
| `batch_complete` | — |
| `cycle_complete` | Cycle Indicator, Quality Trend |
| `pipeline_complete` | All → redirect to session detail |
| `pipeline_error` | Error state display |

### Files to Create

| File | Why |
|------|-----|
| `src/views/WatchLive.tsx` | Watch Live page |
| `src/components/progress/CycleIndicator.tsx` | Cycle progress |
| `src/components/progress/AdCountBar.tsx` | Ad count bars |
| `src/components/progress/ScoreFeed.tsx` | Live score list |
| `src/components/progress/CostAccumulator.tsx` | Running cost |
| `src/components/progress/QualityTrend.tsx` | Quality chart |
| `src/components/progress/LatestAdPreview.tsx` | Latest ad |

### Files You Should READ for Context

| File | Why |
|------|-----|
| `docs/reference/prd.md` (Section 4.7.5) | Progress monitoring spec |
| `src/hooks/useSessionProgress.ts` | SSE hook from PA-07 |
| `src/design/tokens.ts` | Design system tokens |
| `app/workers/progress.py` | Event type constants and structure |

---

## Definition of Done

- [ ] Watch Live page with 6 live elements updating from SSE
- [ ] Cycle indicator, ad count bar, score feed, cost accumulator, quality trend, latest ad preview
- [ ] Auto-redirect to session detail on completion
- [ ] Connection status indicator
- [ ] Responsive layout
- [ ] Tests pass
- [ ] Lint clean
- [ ] DEVLOG updated

---

## Estimated Time: 90–120 minutes

---

## After This Ticket: What Comes Next

**PA-09 (Session Detail — Dashboard Integration)** builds the session detail page that users land on after a pipeline completes. It wraps the existing 7-tab dashboard (from P5) in session context.
