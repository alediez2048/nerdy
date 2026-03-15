# P5-03 Primer: Dashboard HTML — Quality Trends + Dimension Deep-Dive (Panels 3–4)

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** P5-02 (Dashboard Panels 1–2) should be complete. See `docs/DEVLOG.md`.

## What Is This Ticket?

P5-03 adds Panels 3–4 to the existing `output/dashboard.html`:

- **Panel 3: Quality Trends** — Score progression over batches with ratchet line
- **Panel 4: Dimension Deep-Dive** — Per-dimension trend lines + correlation heatmap

## Why It Matters

- Quality trend visualization is a **+2 bonus point** item in the rubric
- Panel 3 is the clearest proof that the feedback loop improves quality over time
- Panel 4 proves dimensions are measured independently (no halo effect) — a key evaluator validation
- Correlation values r > 0.7 must be flagged red (acceptance criterion) — this catches dimension collapse
- **Learning Is Structural** (Pillar 6): Trend visualization makes learning visible

## What Already Exists

- `output/dashboard.html` from P5-02 — has tab navigation with Panels 3–4 as placeholders
- `output/dashboard_data.json` from P5-01 — contains `quality_trends` and `dimension_deep_dive` sections
- `evaluate/correlation.py` — produces correlation matrix data
- `iterate/quality_ratchet.py` — ratchet threshold history

## What This Ticket Must Accomplish

**Goal:** Replace Panel 3–4 placeholders in `dashboard.html` with fully rendered chart views.

### Deliverables Checklist

#### A. Panel 3: Quality Trends

**4 chart views that toggle** (acceptance criterion):

1. **Average Score per Batch** — Line chart: x-axis = batch number, y-axis = avg aggregate score. Include the quality threshold line (7.0) and ratchet line (monotonically increasing)
2. **Score Distribution** — Box plot or histogram showing score spread per batch (min, Q1, median, Q3, max)
3. **Publish Rate per Batch** — Bar chart: published vs discarded per batch, with cumulative publish rate line overlay
4. **Cost per Batch** — Bar chart: tokens consumed per batch, with cost-per-published-ad trend line

All charts use Chart.js. Toggle between views with buttons or a dropdown.

The **ratchet line must be monotonically increasing** (acceptance criterion) — this is the quality floor that only goes up.

#### B. Panel 4: Dimension Deep-Dive

Two sub-views:

1. **Dimension Trend Lines** — 5 line charts (one per dimension) overlaid on a single chart, showing per-batch average for each dimension. Legend shows dimension names with color coding. Include dimension floor lines (Clarity ≥ 6.0, Brand Voice ≥ 5.0)

2. **Correlation Heatmap** — 5×5 grid showing Pearson correlation between every pair of dimensions. Color scale: green (< 0.3, independent), yellow (0.3–0.7, moderate), **red (> 0.7, halo effect detected)**. Display the r-value in each cell. Flag any r > 0.7 cell in red (acceptance criterion).

Data source: `dimension_deep_dive.dimension_trends` and `dimension_deep_dive.correlation_matrix` from `dashboard_data.json`.

#### C. Tests (`tests/test_output/test_dashboard_panels_3_4.py`)

- Test Panel 3 renders batch score chart with correct data points
- Test Panel 3 includes ratchet line that is monotonically non-decreasing
- Test Panel 4 correlation heatmap flags r > 0.7 in red
- Test all 4 chart view toggles are present in Panel 3

Minimum: 4 tests

#### D. Documentation

- Add P5-03 entry in `docs/DEVLOG.md`

### Architectural Decisions

- **Chart.js for all charts**: Already loaded by P5-02. Consistent look across panels
- **Correlation heatmap**: Use a canvas-based or HTML table approach — Chart.js doesn't natively do heatmaps, so either use a plugin or render with HTML table + CSS background colors
- **Toggle views**: Use simple button group with JavaScript to show/hide chart canvases — no framework needed
- **Ratchet validation**: The ratchet line values come from the data; the HTML doesn't enforce monotonicity — that's the pipeline's job. But the chart should make it visually obvious

### Files to Modify

| File | Why |
|------|-----|
| `output/dashboard.html` | Add Panels 3–4 content |

### Files to Create

| File | Why |
|------|-----|
| `tests/test_output/test_dashboard_panels_3_4.py` | Panel 3–4 tests |

### Files You Should READ for Context

| File | Why |
|------|-----|
| `output/dashboard.html` | Existing dashboard structure from P5-02 |
| `output/dashboard_data.json` | `quality_trends` and `dimension_deep_dive` data |
| `evaluate/correlation.py` | How correlation matrix is computed |
| `iterate/quality_ratchet.py` | How ratchet threshold works |

### Definition of Done

- Panel 3 shows 4 toggleable chart views (batch scores, distribution, publish rate, cost)
- Ratchet line is visible and monotonically increasing
- Panel 4 shows dimension trend lines with floor lines
- Correlation heatmap renders with r-values; r > 0.7 flagged red
- Tests pass
- Lint clean
- DEVLOG updated

**Estimated Time:** 60–90 minutes

### After This Ticket: What Comes Next

**P5-04** adds Panel 5 (Ad Library) — the filterable ad browser.
