# P5-06 Primer: Dashboard HTML — System Health + Competitive Intel (Panels 7–8)

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** P5-05 (Dashboard Panel 6) should be complete. See `docs/DEVLOG.md`.

## What Is This Ticket?

P5-06 adds Panels 7–8 to the existing `output/dashboard.html`, completing all 8 dashboard panels:

- **Panel 7: System Health** — SPC control charts, confidence routing, escalation log, compliance stats
- **Panel 8: Competitive Intelligence** — Competitor patterns, hook type trends, strategy shift alerts

## Why It Matters

- Panel 7 proves the system monitors its own reliability — **The System Knows What It Doesn't Know** (Pillar 4)
- SPC control charts show evaluator stability over time — "SPC renders; ratchet monotonically increasing" is the acceptance criterion
- Confidence routing stats show autonomous vs. escalated decisions — transparency about uncertainty
- Panel 8 shows the system learns from competitors — not operating in a vacuum
- These final two panels complete the dashboard, making the full system visible

## What Already Exists

- `output/dashboard.html` from P5-02/03/04/05 — Panels 7–8 are placeholder tabs
- `output/dashboard_data.json` from P5-01 — contains `system_health` and `competitive_intel` sections
- `evaluate/spc_monitor.py` — `get_control_chart_data()` with batch scores, UCL/LCL, breaches
- `evaluate/confidence_router.py` — Confidence routing statistics
- `iterate/spc.py` — `SPCResult` with mean, UCL, LCL, outliers, mean_shift, trend
- `iterate/self_healing.py` — Self-healing action log
- `generate/competitive_trends.py` — `get_competitive_dashboard_data()` with trends, shifts, patterns

## What This Ticket Must Accomplish

**Goal:** Replace Panel 7–8 placeholders, completing all 8 dashboard panels.

### Deliverables Checklist

#### A. Panel 7: System Health

**Sub-Panel 7.1: SPC Control Chart**
- Line chart: x-axis = batch number, y-axis = batch average score
- Include: center line (mean), UCL (+2σ), LCL (-2σ) as dashed lines
- Breaches highlighted as red data points
- The ratchet threshold line overlay (monotonically increasing)
- Data source: `system_health.spc`

**Sub-Panel 7.2: Confidence Routing Stats**
- Summary card or bar chart showing:
  - Total evaluations
  - Auto-published (high confidence): count + percentage
  - Flagged for review (medium confidence): count + percentage
  - Escalated (low confidence): count + percentage
- Data source: `system_health.confidence_stats`

**Sub-Panel 7.3: Self-Healing / Escalation Log**
- Table or timeline of healing actions triggered:
  - Timestamp, trigger (drift/plateau/outlier), action taken, result
- If no healing actions were triggered, show "System remained in control — no healing needed" message
- Data source: `system_health.escalation_log` (or derived from ledger events)

**Sub-Panel 7.4: Compliance Stats**
- Simple card: total ads checked, passed, failed, pass rate
- Breakdown by violation type if available (regex catches, prompt filter, evaluator flag)
- Data source: `system_health.compliance_stats`

**Layout**: 2×2 grid within the Panel 7 tab.

#### B. Panel 8: Competitive Intelligence

**Sub-Panel 8.1: Competitor Pattern Database**
- Table: competitor name, pattern count, top hook types, avg scores
- Sortable by pattern count or score
- Data source: `competitive_intel.patterns` or `competitive_intel.competitors`

**Sub-Panel 8.2: Hook Type Distribution**
- Bar chart: hook types (question, statistic, narrative, social_proof, challenge, curiosity) with frequency counts
- Compare: competitor distribution vs. system's generated distribution
- Data source: `competitive_intel.hook_distribution`

**Sub-Panel 8.3: Strategy Shift Alerts**
- Alert cards for any >15% shift in competitor strategy
- Each alert: competitor, shift type, magnitude, recommendation
- If no shifts detected, show "No significant strategy shifts detected"
- Data source: `competitive_intel.strategy_shifts`

**Sub-Panel 8.4: Trending Hooks**
- List of hooks with momentum (increasing usage across recent batches)
- Growth rate indicator (arrow up/down + percentage)
- Data source: `competitive_intel.trending_hooks`

**Layout**: 2×2 grid within the Panel 8 tab.

#### C. Tests (`tests/test_output/test_dashboard_panels_7_8.py`)

- Test Panel 7 SPC chart includes UCL/LCL lines
- Test Panel 7 confidence routing stats render with percentages
- Test Panel 7 ratchet line is monotonically non-decreasing
- Test Panel 8 competitor table renders with sortable columns
- Test Panel 8 strategy shift alerts render (or "no shifts" message)

Minimum: 5 tests

#### D. Documentation

- Add P5-06 entry in `docs/DEVLOG.md`

### Architectural Decisions

- **SPC chart**: Chart.js line chart with annotation plugin for UCL/LCL horizontal lines, or draw them as separate datasets
- **Compliance stats**: If detailed violation data isn't in `dashboard_data.json`, show aggregate pass/fail only
- **Competitive data**: If no competitor data exists (patterns DB is empty), show a clear "No competitive data collected" message rather than empty charts
- **Graceful degradation**: Each sub-panel handles missing data independently — a missing section doesn't break other panels

### Files to Modify

| File | Why |
|------|-----|
| `output/dashboard.html` | Add Panels 7–8 content (completing all 8 panels) |

### Files to Create

| File | Why |
|------|-----|
| `tests/test_output/test_dashboard_panels_7_8.py` | Panels 7–8 tests |

### Files You Should READ for Context

| File | Why |
|------|-----|
| `output/dashboard.html` | Existing dashboard structure with Panels 1–6 |
| `output/dashboard_data.json` | `system_health` and `competitive_intel` data |
| `evaluate/spc_monitor.py` | SPC control chart data structure |
| `iterate/spc.py` | SPCResult fields |
| `iterate/self_healing.py` | HealingAction data |
| `generate/competitive_trends.py` | Competitive dashboard data structure |
| `evaluate/confidence_router.py` | Confidence routing stats |

### Definition of Done

- All 8 dashboard panels are complete — no more placeholders
- SPC control chart renders with UCL/LCL lines and breach highlighting
- Ratchet line is monotonically increasing (visible in Panel 7)
- Confidence routing stats show auto/flagged/escalated percentages
- Competitive intelligence panel shows patterns, trends, shifts
- Graceful handling of empty data (no crashes, clear messages)
- Tests pass
- Lint clean
- DEVLOG updated

**Estimated Time:** 60–90 minutes

### After This Ticket: What Comes Next

**P5-07** (Decision Log) begins the documentation deliverables. The dashboard is now complete and can be referenced in the demo video (P5-09).
