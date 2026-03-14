# PA-08 Primer: Watch Live Progress View (React)

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** PA-07 (progress reporting SSE infrastructure) must be complete. See `docs/DEVLOG.md`.

---

## What Is This Ticket?

PA-08 builds the **"Watch Live" progress dashboard** — a dedicated React view that displays real-time pipeline execution status. It consumes the SSE stream from PA-07 and renders six live-updating elements: a cycle indicator, an ad count progress bar, a live score feed, a cost accumulator, a live quality trend chart, and a latest ad preview. This is the user's window into what the pipeline is doing right now.

### Why It Matters

- **Visible Reasoning Is a First-Class Output** (Pillar 7): The pipeline must show its work as it happens, not just after completion
- Pipeline runs span multiple cycles and batches — users need confidence the system is working and improving
- Live quality trend shows the ratchet in action, building trust in the autonomous improvement loop
- The latest ad preview gives immediate, tangible feedback — users see real output as it's produced

---

## What Was Already Done

- PA-07: Celery progress publisher, Redis pub/sub, FastAPI SSE endpoint, `useSessionProgress` hook
- PA-06: Session list UI with status badges and card layout
- PA-04: Session CRUD API with detail endpoint
- P5-02/P5-03: Dashboard panel designs (static versions — this ticket creates the live equivalents)

---

## What This Ticket Must Accomplish

### Goal

Build a dedicated "Watch Live" React view with 6 real-time progress elements, all powered by the SSE stream from PA-07.

### Deliverables Checklist

#### A. Watch Live Page (`frontend/src/pages/WatchLive.tsx`)

- [ ] Route: `/sessions/{sessionId}/live`
- [ ] Accessible from session list card ("Watch Live" button on running sessions)
- [ ] Connects to SSE endpoint via `useSessionProgress` hook from PA-07
- [ ] Shows connection status indicator (connected / reconnecting / disconnected)
- [ ] Auto-redirects to session detail view when pipeline completes

#### B. Cycle Indicator Component (`frontend/src/components/progress/CycleIndicator.tsx`)

- [ ] Displays current cycle number and total expected cycles
- [ ] Visual step indicator (e.g., stepper dots or progress segments)
- [ ] Shows cycle phase: generating / evaluating / regenerating / complete
- [ ] Updates on `cycle_start` and `cycle_complete` events

#### C. Ad Count Progress Bar (`frontend/src/components/progress/AdCountBar.tsx`)

- [ ] Horizontal segmented bar showing: generated (gray) / evaluated (blue) / published (green) / discarded (red)
- [ ] Numeric labels: "X generated, Y evaluated, Z published"
- [ ] Updates on `ad_generated`, `ad_evaluated`, `ad_published` events
- [ ] Target count shown as total bar width

#### D. Live Score Feed (`frontend/src/components/progress/ScoreFeed.tsx`)

- [ ] Scrolling feed of recent evaluation results
- [ ] Each entry: ad excerpt (first 50 chars), overall score, pass/fail badge
- [ ] Color-coded: green (>=7.0), yellow (5.5-7.0), red (<5.5)
- [ ] Shows last 10 entries, auto-scrolls to newest
- [ ] Updates on `ad_evaluated` events

#### E. Cost Accumulator (`frontend/src/components/progress/CostAccumulator.tsx`)

- [ ] Running total of API cost in dollars
- [ ] Breakdown: text generation / evaluation / image generation
- [ ] Cost-per-published-ad (running average)
- [ ] Updates on every event that includes `cost_so_far`

#### F. Live Quality Trend Chart (`frontend/src/components/progress/QualityTrend.tsx`)

- [ ] Line chart showing average score over time (per batch or per cycle)
- [ ] Horizontal line at current quality ratchet threshold
- [ ] X-axis: batch/cycle number; Y-axis: average score
- [ ] Points appear as batches complete
- [ ] Uses a lightweight chart library (e.g., Recharts or Chart.js)
- [ ] Updates on `batch_complete` and `cycle_complete` events

#### G. Latest Ad Preview (`frontend/src/components/progress/LatestAdPreview.tsx`)

- [ ] Shows the most recently evaluated ad in Meta ad format
- [ ] Fields: primary text, headline, description, CTA button
- [ ] Per-dimension score badges (color-coded)
- [ ] Overall score prominently displayed
- [ ] Transitions smoothly when a new ad arrives
- [ ] Updates on `ad_evaluated` events (with ad content in payload)

#### H. Tests (`tests/test_frontend/test_watch_live.test.tsx`)

- [ ] TDD first
- [ ] Test all 6 progress elements render with initial empty state
- [ ] Test cycle indicator updates on cycle events
- [ ] Test ad count bar segments update correctly
- [ ] Test score feed scrolls and limits to 10 entries
- [ ] Test cost accumulator displays running totals
- [ ] Test quality trend chart adds points on batch complete
- [ ] Test latest ad preview updates on new evaluation
- [ ] Test connection status indicator reflects SSE state
- [ ] Minimum: 8+ tests

#### I. Documentation

- [ ] Add PA-08 entry in `docs/DEVLOG.md`

---

## Branch & Merge Workflow

```bash
git switch main && git pull
git switch -c feature/PA-08-watch-live-progress
```

---

## Important Context

### Architectural Decisions

| Decision | Reference | Summary |
|----------|-----------|---------|
| Progress monitoring | R5-Q4 | Dedicated progress dashboard with cycle indicator, ad count, live scores, cost, quality trend, and ad preview — all SSE-powered |
| Visible reasoning | Pillar 7 | Real-time pipeline visibility builds trust and enables intervention |

### Files to Create

| File | Why |
|------|-----|
| `frontend/src/pages/WatchLive.tsx` | Main Watch Live page |
| `frontend/src/components/progress/CycleIndicator.tsx` | Cycle step indicator |
| `frontend/src/components/progress/AdCountBar.tsx` | Ad generation progress bar |
| `frontend/src/components/progress/ScoreFeed.tsx` | Live evaluation score feed |
| `frontend/src/components/progress/CostAccumulator.tsx` | Running cost display |
| `frontend/src/components/progress/QualityTrend.tsx` | Live quality trend chart |
| `frontend/src/components/progress/LatestAdPreview.tsx` | Most recent ad preview |
| `tests/test_frontend/test_watch_live.test.tsx` | Component tests |

### Files to Modify

| File | Action |
|------|--------|
| `frontend/src/App.tsx` | Add `/sessions/:id/live` route |
| `frontend/src/components/SessionList.tsx` | Add "Watch Live" button on running session cards |
| `docs/DEVLOG.md` | Add ticket entry |

### Files You Should READ for Context

| File | Why |
|------|-----|
| PA-07 primer | SSE infrastructure and `useSessionProgress` hook API |
| PA-06 primer | Session list component structure |
| P5-02 primer | Dashboard panel 1-2 design patterns (static equivalents) |
| P5-03 primer | Quality trend chart design (static equivalent) |
| `interviews.md` (R5-Q4) | Full rationale for progress view design |

---

## Suggested Implementation Pattern

```tsx
// frontend/src/pages/WatchLive.tsx
function WatchLive() {
  const { sessionId } = useParams();
  const { progress, connectionStatus } = useSessionProgress(sessionId);

  useEffect(() => {
    if (progress?.type === "pipeline_complete") {
      navigate(`/sessions/${sessionId}`);
    }
  }, [progress]);

  return (
    <div className="watch-live">
      <ConnectionBadge status={connectionStatus} />
      <CycleIndicator cycle={progress.cycle} phase={progress.phase} />
      <AdCountBar counts={progress.adCounts} target={progress.targetCount} />
      <div className="live-panels">
        <ScoreFeed evaluations={progress.recentEvals} />
        <CostAccumulator costs={progress.costs} />
      </div>
      <QualityTrend dataPoints={progress.batchAverages} threshold={progress.ratchetThreshold} />
      <LatestAdPreview ad={progress.latestAd} />
    </div>
  );
}
```

---

## Edge Cases to Handle

1. Pipeline completes before user opens Watch Live — show final state summary, not a blank page
2. SSE disconnects mid-run — show reconnecting state, resume from `Last-Event-ID`
3. Very fast pipeline (few ads) — all 6 elements should render meaningfully even with minimal data
4. Very slow pipeline (rate-limited) — heartbeat keeps connection alive; UI shows "waiting for next batch"
5. No ads published yet — score feed and ad preview show "Waiting for first evaluation..."
6. Browser tab backgrounded — EventSource may be throttled; catch up on refocus

---

## Definition of Done

- [ ] All 6 progress elements update in real time during pipeline run
- [ ] Cycle indicator shows current cycle and phase
- [ ] Ad count bar reflects generated/evaluated/published/discarded counts
- [ ] Score feed shows color-coded recent evaluations
- [ ] Cost accumulator tracks running spend
- [ ] Quality trend chart plots batch averages with ratchet threshold line
- [ ] Latest ad preview shows most recently evaluated ad
- [ ] Connection status indicator works correctly
- [ ] Auto-redirect to session detail on pipeline completion
- [ ] Tests pass
- [ ] Lint clean
- [ ] DEVLOG updated
- [ ] Feature branch pushed

---

## Estimated Time

| Task | Estimate |
|------|----------|
| WatchLive page + routing | 15 min |
| CycleIndicator + AdCountBar | 25 min |
| ScoreFeed + CostAccumulator | 25 min |
| QualityTrend chart | 30 min |
| LatestAdPreview | 20 min |
| Tests | 30 min |
| DEVLOG update | 5–10 min |

---

## After This Ticket: What Comes Next

**PA-09 (Session detail — dashboard integration)** wraps the existing 5-tab dashboard in session context. While PA-08 shows what's happening now, PA-09 shows the full results after (or during) a run. Together they form the complete session monitoring experience.
