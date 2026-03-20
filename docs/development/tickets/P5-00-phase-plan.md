# Phase P5: Dashboard, Documentation & Submission

## Context

P5 produces all submission deliverables: the 8-panel HTML dashboard, decision log, technical writeup, demo video, ad library export, and README. Every rubric category touches P5 — quality visualization (25%), documentation (20%), and the demo itself (-10 deduction without it). This phase is non-negotiable.

## Tickets (11)

### P5-01: Dashboard Data Export Script
- `output/export_dashboard.py` — reads JSONL ledger, aggregates into `output/dashboard_data.json`
- All 8 panels' data in one JSON file
- **AC:** Script runs, JSON contains all panel data

### P5-02: Dashboard HTML — Panels 1–2 (Pipeline Summary + Iteration Cycles)
- Panel 1: 8 hero KPIs (total ads, published, discarded, avg score, cost-per-ad, etc.)
- Panel 2: Per-cycle before/after cards showing improvement
- **AC:** All 8 hero metrics render, cycle cards show before/after

### P5-03: Dashboard HTML — Panels 3–4 (Quality Trends + Dimension Deep-Dive)
- Panel 3: Score progression chart, dimension trend lines, ratchet line overlay
- Panel 4: Correlation heatmap, r > 0.7 flagged red
- **AC:** 4 chart views toggle, ratchet monotonically increasing

### P5-04: Dashboard HTML — Panel 5 (Ad Library)
- Filterable browser: per-ad cards with scores, expandable rationales, before/after pairs
- Filters: score range, status, audience, goal, search
- **AC:** All 50+ ads browsable, rationales expand

### P5-05: Dashboard HTML — Panel 6 (Token Economics)
- Cost attribution pie, cost-per-ad trend, marginal analysis curve, model routing breakdown
- **AC:** All sub-panels render (simplify if needed — skip projected cost)

### P5-06: Dashboard HTML — Panels 7–8 (System Health + Competitive Intel)
- Panel 7: SPC control charts, confidence routing stats, escalation log
- Panel 8: Competitor pattern table, hook distribution, strategy differences
- **AC:** SPC renders, ratchet monotonically increasing

### P5-07: Decision Log
- Polish existing `docs/deliverables/decisionlog.md`
- All major choices as ADRs + narrative reflection
- **AC:** Covers all major choices, honest about failures

### P5-08: Technical Writeup
- `docs/deliverables/writeup.md` — 1–2 pages: architecture, methodology, findings, trends, costs, limitations
- **AC:** Concise, covers all areas

### P5-09: Demo Video (7 min)
- Act 1: Naive approach fails (why you can't just prompt an LLM)
- Act 2: Architecture (9 pillars, decomposition, evaluation-first)
- Act 3: Results — before/after + dashboard walkthrough
- **AC:** ≤ 7 minutes, shows dashboard in Act 3

### P5-10: Generated Ad Library Export
- `output/ad_library.json` — 50+ ads with full scores, rationales, lifecycle
- `output/ad_library.csv` — flattened for spreadsheet analysis
- **AC:** Complete metadata, filterable

### P5-11: README with One-Command Setup
- Setup, usage, configuration, architecture, dashboard launch
- **AC:** New developer runs pipeline + dashboard in < 5 minutes

## Dependency Graph

```
P5-01 (Export Script) ← needs pipeline run data
  │
  ├─→ P5-02 (Panels 1-2)
  ├─→ P5-03 (Panels 3-4)
  ├─→ P5-04 (Panel 5)
  ├─→ P5-05 (Panel 6)
  └─→ P5-06 (Panels 7-8)
           │
           └─→ All panels done
                    │
P5-07 (Decision Log) ── standalone (polish existing)
P5-08 (Writeup) ── after pipeline + dashboard done
P5-09 (Demo Video) ── last (needs everything working)
P5-10 (Ad Library Export) ── after pipeline run
P5-11 (README) ── after pipeline + dashboard done
```

## Rubric Deductions Prevented

| Deliverable | Deduction if missing |
|-------------|---------------------|
| Working demo (P5-09) | -10 |
| Runnable with instructions (P5-11) | -10 |
| 50+ ads (P5-10) | -5 |
| Evaluation scores (P5-01) | -15 |
| Decision log (P5-07) | -10 |

## Status: ⏳ NOT STARTED (critical path — must ship)
