# PH-02 Primer: CostAttributor Module

**For:** New Agent session
**Project:** Ad-Ops-Autopilot
**Date:** May 2026
**Phase plan:** [`PH-00-phase-plan.md`](PH-00-phase-plan.md)
**Depends on:** PH-01 (LedgerReader)
**Branch:** `feature/PH-02-cost-attributor`

---

## What Is This Ticket?

Cost attribution today is split between two near-duplicate top-level functions and routed through nine different campaign + dashboard endpoints:

GitNexus blast-radius:
- `compute_session_cost_usd` — **CRITICAL**, 4 direct callers, **9 processes** (campaigns + dashboard)
- `sum_session_display_cost_usd` — **CRITICAL**, 4 direct callers, **8 processes**
- Both functions co-touch `get_summary`, `get_costs`, `update_campaign`, `delete_campaign`, `get_campaign`, `list_campaigns` — exactly where the DEVLOG's "display cost vs. true cost" divergence keeps appearing.

Compounding factors per DEVLOG entries:
- `tokens_consumed: 0` hardcoded in many historical events → cost must fall back to per-call rates from `config.yaml`
- Video has a winner-variant rule (display cost excludes A/B alternate)
- `data/cost_manifest.json` exists as a backfill baseline for sessions where the ledger is too thin
- Rate maps for Fal / Veo / NB2 / NB Pro live in `evaluate/cost_reporter.py` and partly in `config.yaml`

The math is fine; the **seam** is not.

---

## What This Ticket Must Accomplish

### Goal

A single **CostAttributor** module that absorbs:
- Rate-table lookup (per model, per call vs. per token, with config fallback)
- Winner-variant exclusion (video display cost)
- Cost-manifest baseline fallback
- Per-format breakdown (text / image / video)
- Confidence level (how much of the cost is ledger-derived vs. baselined)

Single public entry: `attribute_session_cost(session_id, *, ledger=None, manifest=None) -> SessionCostBreakdown` returning `{ text_usd, image_usd, video_usd, total_usd, confidence }`.

All callers — every campaign route, every dashboard route, every backfill script, the CLI summary — call this one function. The internal rate tables, classification logic, and manifest fallback become private.

### Deliverables Checklist

#### A. Design (grilling session — BEFORE implementation)
- [ ] Run `gitnexus_context` on both existing entry points and map the actual divergence (do they truly compute the same thing, or are there intentional differences?)
- [ ] Decide the public API shape (single function vs. class — keep it small)
- [ ] Decide `confidence` semantics (e.g. ratio of ledger-derived $ to baselined $)
- [ ] Decide how the manifest fallback is exposed (parameter? auto-loaded?)
- [ ] Confirm rate-table source of truth — `config.yaml` only, no module-level constants

#### B. Implementation
- [ ] Create `evaluate/cost_attributor.py` (likely location) with the public entry + `SessionCostBreakdown` dataclass
- [ ] Move rate-table logic from `cost_reporter.py` private to the attributor (or convert `cost_reporter.py` into the attributor)
- [ ] Migrate `app/api/routes/dashboard.py` calls (`get_summary`, `get_costs`, `get_global_dashboard`) to the attributor
- [ ] Migrate `app/api/routes/campaigns.py` calls (`update_campaign`, `delete_campaign`, `get_campaign`, `list_campaigns`) to the attributor
- [ ] Migrate `iterate/batch_processor.py` cost calls
- [ ] Migrate `scripts/backfill_session_costs.py` (it should USE the attributor, not duplicate its logic)
- [ ] Delete the now-unused old entry points

#### C. Testing
- [ ] All existing pytest suites pass
- [ ] New unit tests on `CostAttributor` covering: ledger-only path, manifest-fallback path, video-winner-only rule, missing-rate fallback
- [ ] Snapshot test: for a fixture session, the attributor returns the same numbers the dashboard previously displayed
- [ ] Existing dashboard tests pass without modification

---

## Acceptance Criteria

- [ ] `git grep "compute_session_cost_usd\|sum_session_display_cost_usd"` returns hits ONLY inside `cost_attributor.py` (or zero hits if those names are retired)
- [ ] For a known fixture session, dashboard cost displays are identical pre- and post-refactor (snapshot diff)
- [ ] `gitnexus_impact({target: "attribute_session_cost"})` shows the expected callers (dashboard + campaign routes + scripts)
- [ ] DEVLOG entry committed
- [ ] PH-01's LedgerReader is the **only** path to ledger events used by this module — no inline `json.loads`

---

## Key Files

| File | Action |
|------|--------|
| `evaluate/cost_reporter.py` | Convert to `cost_attributor.py` OR move logic into a new module and delete |
| `evaluate/cost_attributor.py` | **NEW** (or renamed) — public API + SessionCostBreakdown |
| `app/api/routes/dashboard.py` | Migrate 3 routes to the attributor |
| `app/api/routes/campaigns.py` | Migrate 4 routes to the attributor |
| `iterate/batch_processor.py` | Migrate cost lookups |
| `scripts/backfill_session_costs.py` | Migrate to the attributor |
| `data/cost_manifest.json` | No change — but consumed via the attributor only |
| `tests/test_evaluation/test_cost_*.py` | New tests + migrations |

---

## Out of Scope for PH-02

- Changing what is *charged* (no new rate sources, no new model tiers)
- Per-user cost limits (future ticket)
- Cost forecasting / budgeting features
- Persisting cost breakdowns to Postgres (decision #2 in PH-00: derive from ledger, no new tables)

---

## Verification Before Merge

Same gate as PH-01. Additionally:
- Pre/post fixture-session dashboard cost diff must be empty (or differences explicitly explained in the DEVLOG entry as bug-fixes).
