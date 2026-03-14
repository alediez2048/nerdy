# P0-07 Primer: Golden Set Regression Tests

**For:** New Cursor Agent session  
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG  
**Date:** March 2026  
**Previous work:** P0-06 (evaluator calibration) must be complete. See `docs/DEVLOG.md`.

---

## What Is This Ticket?

P0-07 formalizes the calibration results from P0-06 into a **permanent regression test suite**. The golden set is a fixed collection of 15–20 ads with human-assigned scores that the evaluator must stay calibrated against. This test suite runs before every evaluation batch to catch drift.

### Why It Matters

- **Evaluator drift** (R1-Q1): Without regression tests, the evaluator can silently inflate/deflate scores
- The golden set is the ground truth the evaluator is measured against forever
- If a prompt change improves one dimension but breaks another, the golden set catches it
- This is the foundation for SPC drift detection (P2-04)

---

## What Was Already Done

- P0-05: Reference ads collected and labeled
- P0-06: Evaluator calibrated against labeled ads — scores within ±1.0 on 80%+
- Evaluator module exists in `evaluate/evaluator.py`

---

## What This Ticket Must Accomplish

### Goal

Create a permanent golden set test file and automated regression test suite that validates evaluator calibration on every run.

### Deliverables Checklist

#### A. Golden Set Data (`tests/test_data/golden_ads.json`)

- [ ] 15–20 ads with human-assigned scores across all 5 dimensions
- [ ] Mix of excellent (8+), good (6–8), and poor (<6) ads
- [ ] Include Varsity Tutors ads and competitor ads
- [ ] Each entry: ad text, campaign_goal, human_scores (per dimension), quality_label
- [ ] Scores are FINAL — this file does not change after this ticket

#### B. Regression Test Suite (`tests/test_evaluation/test_golden_set.py`)

- [ ] `test_evaluator_calibration` — run evaluator against all golden ads, verify ±1.0 tolerance on 80%+
- [ ] `test_excellent_ads_score_high` — ads labeled "excellent" average ≥7.0
- [ ] `test_poor_ads_score_low` — ads labeled "poor" average ≤5.0
- [ ] `test_dimension_ordering` — for each ad, the weakest human-scored dimension should be among the bottom 2 evaluator-scored dimensions
- [ ] `test_floor_constraints` — ads with Clarity <6.0 or Brand Voice <5.0 are rejected regardless of aggregate
- [ ] Tests are automated and runnable with `python -m pytest tests/test_evaluation/test_golden_set.py -v`

#### C. Documentation

- [ ] Add P0-07 entry in `docs/DEVLOG.md`
- [ ] Document golden set composition (how ads were selected, scoring methodology)

---

## Branch & Merge Workflow

All work is done directly on `develop`. No feature branches.

```bash
git switch develop && git pull
```

---

## Important Context

### Architectural Decisions

| Decision | Reference | Summary |
|----------|-----------|---------|
| Test design | R2-Q3 (Option A) | Golden set regression as baseline safety |
| Evaluator drift | R1-Q1 | SPC monitoring catches deviation from golden set baselines |

### Files to Create

| File | Why |
|------|-----|
| `tests/test_data/golden_ads.json` | Permanent golden set with human scores |

### Files to Modify

| File | Why |
|------|-----|
| `tests/test_evaluation/test_golden_set.py` | May already exist from P0-06 — extend it |

### Files You Should READ for Context

| File | Why |
|------|-----|
| `data/reference_ads.json` | Source for golden set selection |
| `evaluate/evaluator.py` | Module under test |
| `.claude/skills/adops-tdd/SKILL.md` | Golden set test patterns |

---

## Definition of Done

- [ ] `tests/test_data/golden_ads.json` with 15–20 human-scored ads
- [ ] 5+ regression tests passing
- [ ] Evaluator within ±1.0 of human labels on 80%+
- [ ] Tests automated and runnable
- [ ] DEVLOG updated
- [ ] Committed on `develop`

---

## Estimated Time: 30–45 minutes

---

## After This Ticket: What Comes Next

- **P0-08** (Checkpoint-resume) — completes core infrastructure
- **P0-09** (Competitive pattern database) — initial scan via Meta Ad Library
- **P0-10** (Competitive pattern query interface) — query utility for pipeline consumption
- **P2-01** (Inversion tests) — extends golden set with dimension-degraded variants
- **P2-04** (SPC drift detection) — uses golden set baselines for control charts
