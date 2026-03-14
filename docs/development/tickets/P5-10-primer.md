# P5-10 Primer: Generated Ad Library Export

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** P1-20 (50+ ads generated), P5-01 (dashboard data export) should be complete. See `docs/DEVLOG.md`.

---

## What Is This Ticket?

P5-10 produces the **generated ad library export** — 50+ ads with full scores, rationales, and lifecycle metadata as JSON and CSV. This is a required submission deliverable: "Generated ad samples with evaluation scores."

### Why It Matters

- Submission requirements explicitly list "Generated ad samples with evaluation scores"
- Automatic deduction of -5 points for "Fewer than 50 ads generated" and -15 for "No evaluation scores on generated ads"
- The ad library is the primary evidence of system output quality
- Must be filterable so reviewers can explore ads by audience, goal, score range, cycle, or status
- Complete metadata enables the dashboard ad browser (P5-04) and demo (P5-09)

---

## What Was Already Done

- P1-20: 50+ ads generated with full evaluation scores in the JSONL ledger
- P5-01: `export_dashboard.py` aggregates ledger data into `dashboard_data.json` (includes ad library panel data)
- P5-04: Dashboard ad browser reads from this export
- JSONL ledger contains all raw events: AdGenerated, AdEvaluated, AdRegenerated, AdPublished, AdDiscarded

---

## What This Ticket Must Accomplish

### Goal

Export the complete ad library as both JSON and CSV with full metadata, scores, rationales, and lifecycle information. The export must be filterable and self-documenting.

### Deliverables Checklist

#### A. Export Script (`output/export_ad_library.py`)

- [ ] Read the JSONL ledger and reconstruct each ad's complete lifecycle
- [ ] For each ad, include:
  - `ad_id` — unique identifier
  - `brief` — original brief (audience, product, campaign goal, tone)
  - `cycle` — which iteration cycle produced this ad
  - `copy` — full ad copy (primary text, headline, description, CTA button)
  - `scores` — per-dimension scores (clarity, value_proposition, call_to_action, brand_voice, emotional_resonance)
  - `aggregate_score` — weighted average
  - `rationale` — per-dimension evaluation rationale (contrastive)
  - `confidence` — evaluator confidence score
  - `status` — published | discarded | regenerated
  - `lifecycle` — array of events with timestamps (generated -> evaluated -> regenerated -> re-evaluated -> published/discarded)
  - `model_used` — which model generated this ad (Flash vs. Pro)
  - `token_cost` — total tokens spent on this ad (generation + evaluation + regeneration)
  - `seed` — deterministic seed for reproducibility
  - `image_path` — path to generated image (if available)
  - `image_scores` — visual attribute scores (if available)
  - `coherence_score` — text-image coherence score (if available)
- [ ] Output both formats:
  - `output/ad_library.json` — full nested structure with all metadata
  - `output/ad_library.csv` — flattened for spreadsheet analysis (scores as separate columns, rationales truncated if needed)

#### B. Filtering Support

- [ ] JSON export includes a `summary` header with:
  - Total ads generated
  - Total publishable (score >= 7.0)
  - Average score across all ads
  - Average score across publishable ads
  - Per-dimension averages
  - Total token cost
  - Cost per publishable ad
- [ ] CSV export is sorted by aggregate score (descending) by default
- [ ] Both exports include all fields needed for filtering by: audience, campaign goal, score range, cycle number, status

#### C. Tests (`tests/test_output/test_ad_library_export.py`)

- [ ] TDD first
- [ ] Test export produces valid JSON with required fields
- [ ] Test export produces valid CSV with correct column count
- [ ] Test all 50+ ads are present in export
- [ ] Test summary statistics are mathematically correct
- [ ] Test lifecycle reconstruction matches ledger events
- [ ] Minimum: 5+ tests

#### D. Documentation

- [ ] Add P5-10 entry in `docs/DEVLOG.md`

---

## Branch & Merge Workflow

```bash
git switch main && git pull
git switch -c feature/P5-10-ad-library-export
```

---

## Important Context

### Architectural Decisions

| Decision | Reference | Summary |
|----------|-----------|---------|
| Data storage | R2-Q8 | Append-only JSONL ledger is the source of truth |
| Contrastive rationales | R3-Q10 | Every evaluation includes contrastive reasoning — include in export |
| Reproducibility | R3-Q4 | Per-ad seed chains enable deterministic replay |

### Files to Create

| File | Why |
|------|-----|
| `output/export_ad_library.py` | Export script |
| `output/ad_library.json` | Full ad library (JSON) |
| `output/ad_library.csv` | Flattened ad library (CSV) |
| `tests/test_output/test_ad_library_export.py` | Export tests |

### Files You Should READ for Context

| File | Why |
|------|-----|
| JSONL ledger file | Source of all ad events |
| `output/export_dashboard.py` | Existing export script — reuse ledger parsing logic |
| P0-02 ledger module | How events are structured |
| `docs/reference/requirements.md` (lines 128-133) | Required output formats |

---

## Definition of Done

- [ ] `output/ad_library.json` contains 50+ ads with complete metadata
- [ ] `output/ad_library.csv` contains the same data in a flat, filterable format
- [ ] Every ad has: copy, 5 dimension scores, aggregate score, rationale, lifecycle, status
- [ ] Summary statistics in JSON header are correct
- [ ] Export script is re-runnable (`python output/export_ad_library.py`)
- [ ] Tests pass
- [ ] Lint clean
- [ ] DEVLOG updated
- [ ] Feature branch pushed

---

## Estimated Time: 45–60 minutes

---

## After This Ticket: What Comes Next

**P5-11** (README) references the ad library export and includes instructions for generating it. This is the second-to-last ticket in Phase 5.
