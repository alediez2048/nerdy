# P5-05 Primer: Dashboard HTML — Token Economics (Panel 6)

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** P5-04 (Dashboard Panel 5) should be complete. See `docs/DEVLOG.md`.

## What Is This Ticket?

P5-05 adds Panel 6 to the existing `output/dashboard.html`:

- **Panel 6: Token Economics** — Cost attribution, cost-per-ad trend, marginal analysis, model routing, projected cost

## Why It Matters

- **Every Token Is an Investment** (Pillar 3): The north star metric is Performance Per Token — this panel makes it visible
- The reviewer needs to see cost-consciousness, not just quality — a system that produces great ads at 10x the cost isn't viable
- Marginal analysis shows the system knows when to stop regenerating (diminishing returns detection)
- Model routing breakdown shows intelligent resource allocation (Flash for easy, Pro for hard)
- "All 6 sub-panels render" is the acceptance criterion

## What Already Exists

- `output/dashboard.html` from P5-02/03/04 — Panel 6 is a placeholder tab
- `output/dashboard_data.json` from P5-01 — contains `token_economics` section
- `iterate/token_tracker.py` — `get_token_summary()` with by_stage, by_model, cost_per_published
- `iterate/marginal_analysis.py` — `get_marginal_dashboard_data()` with gain_curve, token_spend, dimension_breakdown, recommendation
- `evaluate/cost_reporter.py` — Cross-format cost report with USD rates per model

## What This Ticket Must Accomplish

**Goal:** Replace Panel 6 placeholder with 6 sub-panels showing token economics.

### Deliverables Checklist

#### A. Panel 6: Token Economics — 6 Sub-Panels

**Sub-Panel 6.1: Cost Attribution Pie/Donut Chart**
- Tokens consumed by pipeline stage (generation, evaluation, regeneration, distillation, routing, other)
- Data source: `token_economics.by_stage`
- Chart.js doughnut chart with stage labels and percentages

**Sub-Panel 6.2: Cost-Per-Ad Trend**
- Line chart: x-axis = batch number, y-axis = tokens per published ad for that batch
- Shows whether cost efficiency improves over time (should trend down as patterns are learned)
- Data source: Derived from `iteration_cycles` per-batch token totals / published count

**Sub-Panel 6.3: Marginal Analysis — Gain Curve**
- Line chart: x-axis = regeneration cycle (1, 2, 3), y-axis = average quality gain
- Shows diminishing returns: cycle 1 gives the most improvement, cycle 3 gives diminishing
- Overlay: horizontal line at min_gain threshold (0.2) — cycles below this are "not worth it"
- Data source: `token_economics.marginal_analysis.gain_curve`

**Sub-Panel 6.4: Model Routing Breakdown**
- Stacked bar or pie: tokens consumed by model (Gemini Flash, Gemini Pro, Nano Banana, Veo, etc.)
- Shows that Flash handles the bulk (cheap) and Pro is reserved for difficult cases
- Data source: `token_economics.by_model`

**Sub-Panel 6.5: Dimension-Level Marginal Breakdown**
- Grouped bar chart: x-axis = dimension, bars = avg gain at cycle 1, 2, 3
- Shows which dimensions benefit most from regeneration
- Data source: `token_economics.marginal_analysis.dimension_breakdown`

**Sub-Panel 6.6: Auto-Cap Recommendation Card**
- Text card showing the system's recommended max regeneration cycles
- Includes: recommended cycles, reason, estimated token savings
- Data source: `token_economics.marginal_analysis.recommendation`

**Layout**: 2×3 grid of sub-panels within the Panel 6 tab.

#### B. Tests (`tests/test_output/test_dashboard_token_economics.py`)

- Test all 6 sub-panels render (check for canvas elements or card elements)
- Test cost attribution chart has data from by_stage
- Test marginal analysis gain curve shows diminishing returns
- Test model routing chart displays all models from data
- Test auto-cap recommendation card shows reason text

Minimum: 5 tests

#### C. Documentation

- Add P5-05 entry in `docs/DEVLOG.md`

### Architectural Decisions

- **6 sub-panels in one tab**: Use a 2×3 CSS grid. Each sub-panel is a card with a title and a chart or text
- **Chart.js for everything**: Doughnut for attribution, line for trends, bar for comparison — all Chart.js
- **Auto-cap card is text, not chart**: It's a recommendation — display it prominently with the number and reason
- **USD cost**: Use the rates from `evaluate/cost_reporter.py` to convert tokens to dollars where possible

### Files to Modify

| File | Why |
|------|-----|
| `output/dashboard.html` | Add Panel 6 content |

### Files to Create

| File | Why |
|------|-----|
| `tests/test_output/test_dashboard_token_economics.py` | Token economics tests |

### Files You Should READ for Context

| File | Why |
|------|-----|
| `output/dashboard.html` | Existing dashboard structure |
| `output/dashboard_data.json` | `token_economics` data structure |
| `iterate/token_tracker.py` | TokenSummary fields |
| `iterate/marginal_analysis.py` | Marginal dashboard data structure |
| `evaluate/cost_reporter.py` | USD cost rates per model |

### Definition of Done

- All 6 sub-panels render with real data
- Cost attribution pie chart shows token distribution by stage
- Marginal analysis gain curve shows diminishing returns with threshold line
- Model routing breakdown visible
- Auto-cap recommendation displayed with reason
- Tests pass
- Lint clean
- DEVLOG updated

**Estimated Time:** 45–60 minutes

### After This Ticket: What Comes Next

**P5-06** adds Panels 7–8 (System Health + Competitive Intel) — the final dashboard panels.
