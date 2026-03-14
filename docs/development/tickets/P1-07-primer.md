# P1-07 Primer: Pareto-Optimal Regeneration

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** P0-06 (evaluator calibration), P1-02 (ad generator), P1-04 (CoT evaluator), P1-06 (model routing) must be complete. See `docs/DEVLOG.md`.

---

## What Is This Ticket?

P1-07 implements **Pareto-optimal regeneration** to prevent dimension collapse during the improve cycle. Instead of regenerating a single ad and hoping all dimensions improve, the system generates 3-5 variants per cycle and selects the **Pareto-dominant** variant — the one where no other variant scores strictly higher on every dimension. The variant count is controlled by `data/config.yaml` (`pareto_variants`).

Dimension collapse is the central failure mode this ticket prevents: naive "fix the weakest dimension" prompting creates whack-a-mole oscillation where improving CTA tanks Brand Voice, improving Brand Voice tanks Clarity, and the system burns tokens going in circles.

### Why It Matters

- **Prevention Over Detection Over Correction** (Pillar 2): Pareto selection structurally prevents collapse — no variant is chosen if it regresses any dimension vs. the prior cycle's best.
- **Every Token Is an Investment** (Pillar 3): Generating 3-5 variants costs 3-5x per cycle, but eliminates oscillation cycles that cost 10-20x in wasted regeneration.
- Without Pareto filtering, the feedback loop cannot guarantee monotonic improvement across all five dimensions.
- This is the mathematical backbone of the iteration engine — P1-08 (brief mutation) only fires when Pareto selection itself fails.

---

## What Was Already Done

These modules exist and are tested — do NOT recreate them:

| Module | What It Provides |
|--------|-----------------|
| `evaluate/evaluator.py` | `evaluate_ad()` returns `EvaluationResult` with per-dimension scores (clarity, value_prop, cta, brand_voice, emotional_resonance) |
| `generate/seeds.py` | `get_ad_seed()` — deterministic seed per ad/cycle; different seeds per variant |
| `iterate/ledger.py` | `log_event()` for logging selection decisions; `read_events()` for history |
| `iterate/checkpoint.py` | `should_skip_ad()` — skip already-processed ads on resume |
| `data/config.yaml` | `pareto_variants` count and dimension floors |
| `data/brand_knowledge.json` | Brand voice profiles used by generator |

---

## What This Ticket Must Accomplish

### Goal

Build the Pareto selection layer that generates multiple variants per regeneration cycle, evaluates each, selects the Pareto-dominant variant, and rejects any variant that regresses a dimension vs. the prior cycle.

### Deliverables Checklist

#### A. Pareto Selection Module (`iterate/pareto_selection.py`)

- [ ] `ParetoCandidate` dataclass — ad_id, variant_index, scores (dict of dimension -> float), weighted_average, ad_content
- [ ] `is_pareto_dominant(candidate: ParetoCandidate, others: list[ParetoCandidate]) -> bool`
  - Returns True if no other candidate scores strictly higher on ALL dimensions
  - A candidate is Pareto-dominant if for every other candidate, there exists at least one dimension where this candidate scores equal or higher
- [ ] `filter_regressions(candidates: list[ParetoCandidate], prior_scores: dict) -> list[ParetoCandidate]`
  - Removes any candidate where ANY dimension score is lower than the prior cycle's corresponding score
  - If all candidates regress on at least one dimension, returns empty list (signals brief mutation needed)
- [ ] `select_best(candidates: list[ParetoCandidate], prior_scores: dict | None) -> ParetoCandidate | None`
  - First filters regressions (if prior_scores provided)
  - Then finds Pareto-dominant candidates from the remaining set
  - If multiple Pareto-dominant candidates exist, selects the one with highest weighted average
  - Returns None if no valid candidate exists (triggers P1-08 brief mutation)
  - Logs selection rationale to ledger
- [ ] `generate_and_select(ad_id: str, brief: dict, prior_scores: dict | None, config: dict) -> ParetoCandidate | None`
  - Generates `pareto_variants` variants (from config, default 3)
  - Evaluates each variant
  - Runs `select_best` and returns winner or None

#### B. Tests (`tests/test_pipeline/test_pareto_selection.py`)

- [ ] TDD first
- [ ] Test `is_pareto_dominant` identifies dominant candidate correctly
- [ ] Test `is_pareto_dominant` returns False when another candidate beats on all dimensions
- [ ] Test `filter_regressions` removes candidates that regress on any dimension
- [ ] Test `filter_regressions` returns empty list when all candidates regress
- [ ] Test `select_best` picks highest weighted average among Pareto-dominant set
- [ ] Test `select_best` returns None when no non-regressing candidate exists
- [ ] Test first cycle (no prior_scores) skips regression filtering
- [ ] Test variant count respects config `pareto_variants`
- [ ] Minimum: 8+ tests

#### C. Documentation

- [ ] Add P1-07 entry in `docs/DEVLOG.md`

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
| Pareto-optimal filtering | R1-Q5 | Generate 3-5 variants, select Pareto-dominant. No dimension regresses. Structural prevention of collapse. |
| Dimension independence | R2-Q3 | Five dimensions are independently measurable — Pareto selection relies on this independence. |
| Brief mutation on failure | R1-Q2 | When Pareto selection returns None (all candidates regress), hand off to P1-08 brief mutation. |

### Key Concept: Pareto Dominance

Candidate A **Pareto-dominates** candidate B if A is at least as good as B on every dimension AND strictly better on at least one. A candidate is **Pareto-optimal** if no other candidate dominates it. In a set of 3-5 variants, there may be 1-3 Pareto-optimal candidates — we pick the one with the highest weighted average as the tiebreaker.

### Files to Create

| File | Why |
|------|-----|
| `iterate/pareto_selection.py` | Pareto filtering, regression check, selection logic |
| `tests/test_pipeline/test_pareto_selection.py` | Pareto + regression tests |

### Files You Should READ for Context

| File | Why |
|------|-----|
| `evaluate/evaluator.py` | EvaluationResult structure — the scores you compare |
| `generate/seeds.py` | Variant seeds: `get_ad_seed(global_seed, brief_id, cycle, variant_index)` |
| `data/config.yaml` | `pareto_variants` count |
| `iterate/ledger.py` | How to log selection rationale |
| `docs/reference/prd.md` (R1-Q5) | Full rationale for Pareto filtering |

---

## Definition of Done

- [ ] `is_pareto_dominant()` correctly identifies dominant candidates
- [ ] `filter_regressions()` rejects any candidate with a dimension regression vs. prior cycle
- [ ] `select_best()` returns None when no valid candidate exists (handoff signal to P1-08)
- [ ] No dimension regresses between cycles when a candidate is selected
- [ ] Variant count driven by `pareto_variants` config — no hardcoded count
- [ ] Selection rationale logged to ledger
- [ ] Tests pass
- [ ] Lint clean
- [ ] DEVLOG updated
- [ ] Committed on `develop`

---

## Estimated Time: 45-60 minutes

---

## After This Ticket: What Comes Next

**Next P1 tickets:**
- **P1-08** (Brief mutation + escalation) — Fires when `select_best()` returns None after all variants regress
- **P1-09** (Distilled context objects) — Compresses iteration history so the generator prompt stays compact across cycles
- **P1-10** (Quality ratchet) — Uses Pareto-selected scores to compute the rolling high-water mark

Pareto selection is the quality guarantor: it ensures every regeneration cycle either improves or triggers escalation. Without it, the feedback loop has no mathematical guarantee of progress.
