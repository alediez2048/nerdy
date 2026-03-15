# P5-02 Primer: Dashboard HTML — Pipeline Summary + Iteration Cycles (Panels 1–2)

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** P5-01 (dashboard data export) should be complete. See `docs/DEVLOG.md`.

## What Is This Ticket?

P5-02 builds the first two panels of the 8-panel single-file HTML dashboard:

- **Panel 1: Pipeline Summary** — Hero KPIs at a glance
- **Panel 2: Iteration Cycles** — Per-ad before/after improvement cards

## Why It Matters

- The dashboard is the primary evidence artifact for the reviewer — it shows system quality at a glance
- Panel 1 answers "what did the system produce?" in 5 seconds
- Panel 2 answers "does the feedback loop actually improve ads?" with concrete before/after evidence
- **The Reviewer Is a User, Too** (Pillar 8): Hero metrics respect their time; before/after cards make improvement tangible
- The assignment rubric: "Quality trend visualization (+2 bonus)" — this is part of that

## What Already Exists

- `output/dashboard_data.json` from P5-01 — contains `pipeline_summary` and `iteration_cycles` sections
- No HTML dashboard files exist yet — this ticket creates the base HTML file

## What This Ticket Must Accomplish

**Goal:** Create a single-file HTML dashboard (`output/dashboard.html`) with Panels 1–2. Subsequent tickets (P5-03 through P5-06) add Panels 3–8 to this same file.

### Deliverables Checklist

#### A. Dashboard HTML (`output/dashboard.html`)

**Single-file architecture:**
- One HTML file with embedded CSS and JavaScript (no external dependencies beyond CDN)
- Use Chart.js via CDN for any charts needed (loaded once, used by all panels)
- Reads `dashboard_data.json` from the same directory via fetch()
- Responsive layout — works on desktop and laptop screens
- Clean, professional design (dark header, card-based layout, clear typography)
- Tab navigation for panels (all 8 tabs present, Panels 3–8 show "Coming soon" placeholder)

**Panel 1: Pipeline Summary — Hero KPIs**

8 hero metric cards in a responsive grid:

| Metric | Source field | Format |
|--------|-------------|--------|
| Total Ads Generated | `pipeline_summary.total_ads_generated` | Integer |
| Ads Published | `pipeline_summary.total_ads_published` | Integer |
| Publish Rate | `pipeline_summary.publish_rate` | Percentage |
| Avg Score | `pipeline_summary.avg_score` | X.X / 10 |
| Total Batches | `pipeline_summary.total_batches` | Integer |
| Total Tokens | `pipeline_summary.total_tokens` | Formatted with commas |
| Total Cost | `pipeline_summary.total_cost_usd` | $X.XX |
| Ads Discarded | `pipeline_summary.total_ads_discarded` | Integer |

Each card: large number, label underneath, subtle background color coding (green for good metrics, amber for neutral, red for failures).

**Panel 2: Iteration Cycles — Before/After Cards**

For each ad that went through regeneration, show a card with:
- Ad ID and cycle number
- Score before → Score after (with delta arrow: green up, red down)
- Weakest dimension that triggered regeneration
- Action taken (regenerated / published / discarded)

Cards sorted by improvement delta (biggest improvement first). Color-code by outcome: green border for published, red for discarded.

#### B. Tests (`tests/test_output/test_dashboard_html.py`)

Since this is HTML, tests validate the data contract and rendering logic rather than pixel-perfect output:

- Test dashboard.html file exists after generation
- Test HTML contains all 8 tab labels
- Test Panel 1 renders all 8 hero metrics from sample data
- Test Panel 2 renders iteration cycle cards from sample data
- Test dashboard loads `dashboard_data.json` correctly (mock fetch)

Minimum: 4 tests

#### C. Optional: Dashboard Generator Script

If the HTML needs dynamic content beyond what JavaScript can handle, create `output/generate_dashboard.py` that reads `dashboard_data.json` and produces `dashboard.html` using string templates. This is optional — inline JavaScript reading JSON at runtime is preferred.

#### D. Documentation

- Add P5-02 entry in `docs/DEVLOG.md`

### Architectural Decisions

- **Single-file HTML**: No server, no build step — open in browser and it works. CDN for Chart.js is the only external dependency
- **Tab navigation**: All 8 panels live in one page with tab switching. Panels 3–8 are placeholders until their tickets are done
- **Data contract**: Dashboard reads whatever P5-01 produces. If a field is missing, show "N/A" — don't crash
- **No framework**: Vanilla HTML/CSS/JS. No React, no Vue, no build tools

### Files to Create

| File | Why |
|------|-----|
| `output/dashboard.html` | The single-file HTML dashboard |
| `tests/test_output/test_dashboard_html.py` | Dashboard tests |

### Files You Should READ for Context

| File | Why |
|------|-----|
| `output/export_dashboard.py` | Understand the JSON data contract |
| `output/dashboard_data.json` | Sample data to render |
| PRD Section 4.5 | Dashboard architecture specification |

### Definition of Done

- `output/dashboard.html` opens in a browser and renders Panels 1–2
- All 8 hero KPI cards display correctly with real data
- Iteration cycle cards show before/after scores with visual delta
- Tab navigation present for all 8 panels (3–8 as placeholders)
- No external dependencies beyond Chart.js CDN
- Tests pass
- Lint clean
- DEVLOG updated

**Estimated Time:** 60–90 minutes

### After This Ticket: What Comes Next

**P5-03** adds Panels 3–4 (Quality Trends + Dimension Deep-Dive) to the same `dashboard.html` file.
