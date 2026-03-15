# P5-01 Primer: Dashboard Data Export Script

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** All prior phases (P0–P4) should be complete. See `docs/DEVLOG.md`.

## What Is This Ticket?

P5-01 produces `output/export_dashboard.py` — a script that reads the JSONL ledger and aggregates all data into a single `output/dashboard_data.json` file consumed by the 8-panel HTML dashboard (P5-02 through P5-06).

## Why It Matters

- The dashboard (P5-02–P5-06) is a single-file HTML that reads from `dashboard_data.json` — this script is the data pipeline
- Separating data export from rendering ensures the dashboard is a pure read-only view — no logic in HTML
- Every dashboard panel needs pre-aggregated data: hero KPIs, per-cycle cards, quality trends, dimension correlations, ad library, token economics, SPC health, competitive patterns
- **State Is Sacred** (Pillar 5): The ledger is the single source of truth; this script transforms but never mutates it

## What Already Exists

These modules already produce dashboard-ready data:

| Module | Function | Dashboard Panel |
|--------|----------|----------------|
| `iterate/token_tracker.py` | `get_token_summary()` → TokenSummary | Panel 6 (Token Economics) |
| `iterate/marginal_analysis.py` | `get_marginal_dashboard_data()` | Panel 6 (Marginal Analysis) |
| `evaluate/cost_reporter.py` | Cross-format cost reporting with USD rates | Panel 6 (Cost Attribution) |
| `evaluate/spc_monitor.py` | `get_control_chart_data()` | Panel 7 (System Health) |
| `evaluate/confidence_router.py` | Confidence routing statistics | Panel 7 (Confidence) |
| `generate/competitive_trends.py` | `get_competitive_dashboard_data()` | Panel 8 (Competitive Intel) |
| `output/replay.py` | `generate_replay()` → PipelineReplay | Panel 1 (Pipeline Summary) |
| `iterate/quality_ratchet.py` | `get_ratchet_state()` | Panel 3 (Quality Trends) |
| `evaluate/correlation.py` | Dimension correlation analysis | Panel 4 (Dimension Deep-Dive) |
| `output/assembler.py` | `AssembledAd` with copy, scores, rationales | Panel 5 (Ad Library) |

## What This Ticket Must Accomplish

**Goal:** Create an export script that reads the JSONL ledger and calls existing module functions to produce `dashboard_data.json` with all 8 panels' data.

### Deliverables Checklist

#### A. Export Script (`output/export_dashboard.py`)

The script should:

1. Accept a ledger path (default: `data/ledger.jsonl`) and output path (default: `output/dashboard_data.json`)
2. Call existing module functions to gather data for all 8 panels
3. Write a single JSON file with this top-level structure:

```python
{
    "generated_at": "ISO-8601 timestamp",
    "ledger_path": "path/to/ledger.jsonl",

    # Panel 1: Pipeline Summary — Hero KPIs
    "pipeline_summary": {
        "total_ads_generated": int,
        "total_ads_published": int,
        "total_ads_discarded": int,
        "publish_rate": float,          # published / generated
        "total_batches": int,
        "total_tokens": int,
        "total_cost_usd": float,
        "avg_score": float,             # across all published ads
    },

    # Panel 2: Iteration Cycles — Per-cycle before/after
    "iteration_cycles": [
        {
            "ad_id": str,
            "cycle": int,
            "score_before": float,
            "score_after": float,
            "weakest_dimension": str,
            "action_taken": str,       # "regenerated" | "published" | "discarded"
        },
    ],

    # Panel 3: Quality Trends — Score progression over batches
    "quality_trends": {
        "batch_scores": [{"batch": int, "avg_score": float, "threshold": float}],
        "ratchet_history": [{"batch": int, "threshold": float}],
    },

    # Panel 4: Dimension Deep-Dive — Per-dimension trends + correlation
    "dimension_deep_dive": {
        "dimension_trends": {
            "clarity": [float],
            "value_proposition": [float],
            "cta": [float],
            "brand_voice": [float],
            "emotional_resonance": [float],
        },
        "correlation_matrix": dict,     # from evaluate/correlation.py
    },

    # Panel 5: Ad Library — All ads with copy, scores, rationales
    "ad_library": [
        {
            "ad_id": str,
            "brief_id": str,
            "copy": dict,              # headline, primary_text, description, cta
            "scores": dict,            # per-dimension
            "aggregate_score": float,
            "rationale": dict,         # per-dimension rationale
            "status": str,             # published | discarded
            "cycle_count": int,
            "image_path": str | None,
        },
    ],

    # Panel 6: Token Economics — Cost attribution + marginal analysis
    "token_economics": {
        "by_stage": dict,              # from token_tracker
        "by_model": dict,              # from token_tracker
        "cost_per_published": float,
        "marginal_analysis": dict,     # from get_marginal_dashboard_data()
        "cost_report": dict,           # from cost_reporter
    },

    # Panel 7: System Health — SPC + confidence + compliance
    "system_health": {
        "spc": dict,                   # from spc_monitor control chart data
        "confidence_stats": dict,      # from confidence_router
        "compliance_stats": dict,      # pass/fail counts
    },

    # Panel 8: Competitive Intelligence — Patterns + trends
    "competitive_intel": dict,         # from get_competitive_dashboard_data()
}
```

4. Include a `main()` function runnable via `python output/export_dashboard.py`
5. Handle missing data gracefully — if a module has no data (e.g., no video events), use empty defaults

#### B. Tests (`tests/test_output/test_export_dashboard.py`)

TDD first. Minimum 6 tests:

- Test export produces valid JSON with all 8 panel keys
- Test pipeline_summary has correct counts (generated, published, discarded)
- Test iteration_cycles reconstructs before/after from evaluation events
- Test ad_library includes all ads with required fields
- Test token_economics calls token_tracker and marginal_analysis
- Test graceful handling of empty ledger (no crash, empty arrays)

#### C. Documentation

- Add P5-01 entry in `docs/DEVLOG.md`

### Architectural Decisions

- **One JSON file for all panels**: The dashboard HTML reads a single file — no multiple API endpoints, no server
- **Reuse existing functions**: Do NOT duplicate logic from token_tracker, spc_monitor, etc. — call them directly
- **Idempotent**: Running the script twice produces the same output for the same ledger
- **No ledger mutation**: Read-only access to the ledger

### Files to Create

| File | Why |
|------|-----|
| `output/export_dashboard.py` | The export script |
| `tests/test_output/test_export_dashboard.py` | Export tests |

### Files You Should READ for Context

| File | Why |
|------|-----|
| `iterate/ledger.py` | `read_events()`, `read_events_filtered()`, `get_ad_lifecycle()` |
| `iterate/token_tracker.py` | `get_token_summary()` — Panel 6 data |
| `iterate/marginal_analysis.py` | `get_marginal_dashboard_data()` — Panel 6 marginal analysis |
| `evaluate/cost_reporter.py` | Cross-format cost report — Panel 6 cost attribution |
| `evaluate/spc_monitor.py` | `get_control_chart_data()` — Panel 7 SPC |
| `evaluate/confidence_router.py` | Confidence statistics — Panel 7 |
| `generate/competitive_trends.py` | `get_competitive_dashboard_data()` — Panel 8 |
| `output/replay.py` | `generate_replay()` — Panel 1 pipeline summary |
| `iterate/quality_ratchet.py` | `get_ratchet_state()` — Panel 3 ratchet history |
| `evaluate/correlation.py` | Dimension correlation — Panel 4 |
| `output/assembler.py` | `AssembledAd` — Panel 5 ad library |

### Definition of Done

- `python output/export_dashboard.py` produces `output/dashboard_data.json`
- JSON contains all 8 panel keys with correct data types
- All data is sourced from existing modules (no duplicated logic)
- Empty ledger doesn't crash — produces valid JSON with empty arrays
- Tests pass (6+ tests)
- Lint clean
- DEVLOG updated

**Estimated Time:** 45–60 minutes

### After This Ticket: What Comes Next

**P5-02** through **P5-06** build the HTML dashboard that reads `dashboard_data.json`. Complete P5-01 first — the dashboard panels depend on this data contract.
