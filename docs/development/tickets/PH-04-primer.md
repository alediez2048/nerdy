# PH-04 Primer: EvaluationPipeline Composite

**For:** New Agent session
**Project:** Ad-Ops-Autopilot
**Date:** May 2026
**Phase plan:** [`PH-00-phase-plan.md`](PH-00-phase-plan.md)
**Depends on:** PH-01 (LedgerWriter)
**Branch:** `feature/PH-04-eval-pipeline`

---

## What Is This Ticket?

The `evaluate/` directory contains **22 modules**, each a pure function that does one job well — but the question "how do we evaluate an ad?" requires reading at least eight of them:

| File | Responsibility |
|---|---|
| `evaluator.py` | 5-dimension text scoring (CoT) — `evaluate_ad` |
| `dimensions.py` | Weights, floors, aggregation rules |
| `confidence_router.py` | Improvable-range routing (5.5 ≤ score ≤ 7.0 → Pro escalation) |
| `weight_recalibrator.py` | Post-hoc weight adjustment |
| `coherence_checker.py` | Text-image semantic coherence |
| `image_evaluator.py` / `image_scorer.py` / `image_selector.py` | Visual attribute checklist + Pareto selection across image variants |
| `video_evaluator.py` / `video_scorer.py` / `video_coherence.py` / `video_attributes.py` | Video parallel of the above |
| `brief_adherence.py` | "Did the ad do what the brief asked?" (PD-12) |
| `spc_monitor.py` | Evaluator drift detection |
| `correlation.py` / `performance_correlation.py` | Cross-dimension correlation analysis |

The ordering and conditional execution of these (text → routing → image-only-if-publishable → adherence → SPC update) lives inside `iterate/batch_processor.process_batch` as a 100-line linear block. There is no composite "evaluate this ad" surface.

GitNexus confirms `evaluator.evaluate_ad` is called by `process_batch` and by **14+ test functions directly** — meaning tests bypass any higher-level composite. Classic pure-function-island anti-pattern: leaves are testable, but the bugs live in how they're composed.

---

## What This Ticket Must Accomplish

### Goal

An **EvaluationPipeline** module with a single public entry:

```python
result = evaluation_pipeline.evaluate(
    ad: GeneratedAd,
    brief: ExpandedBrief,
    session_config: SessionConfig,
) -> EvaluationResult
```

Where `EvaluationResult` exposes:
- `text_scores` (per-dimension + aggregate, with rationales)
- `visual_scores` (image and/or video attribute results)
- `coherence_score`
- `adherence_score`
- `routing_decision` (publish / regenerate / discard / escalate-to-pro)
- `improvable` (bool)
- `escalation_reason` (or None)
- `confidence_band`

All current evaluator modules become **private implementations** behind this composite. The pipeline owns the ordering: text → routing decision → image-only-if-publishable → adherence → SPC update.

### Deliverables Checklist

#### A. Design (grilling session — BEFORE implementation)
- [ ] Run `gitnexus_context` on `evaluate_ad`, `evaluate_image`, `route_ad`, `score_image`, `score_brief_adherence`
- [ ] Map the exact current sequence in `process_batch` (lines ~159–267 per earlier audit) — make it the contract
- [ ] Decide whether image and video evaluation share a base or stay parallel
- [ ] Decide handling of "skip image evaluation if format=copy-only" (PD copy-only mode)
- [ ] Decide test migration policy — which of the 14+ direct callers should switch to the composite, which legitimately need to test a private internal

#### B. Implementation
- [ ] Create `evaluate/evaluation_pipeline.py` with the public composite
- [ ] Move existing modules to `private/_*.py` naming or mark with `# private to EvaluationPipeline` (whichever fits the project's existing convention)
- [ ] Migrate `iterate/batch_processor.py` (lines ~159–267) to call `evaluation_pipeline.evaluate(...)`
- [ ] Migrate the 14+ test callers — public composite where possible, document the rest

#### C. Testing
- [ ] All 670 existing tests pass — especially the golden-set tests in `tests/test_evaluation/test_golden_set.py`
- [ ] Snapshot: for a fixture ad+brief, `EvaluationResult` matches what `process_batch` previously produced (deep-equal)
- [ ] New tests on the composite covering: routing decisions, format-conditional evaluation, adherence inclusion
- [ ] SPC monitor still receives events in the same order

---

## Acceptance Criteria

- [ ] One public class/function from `evaluate/` — `EvaluationPipeline.evaluate(...)` or `evaluate.evaluate(...)`
- [ ] `process_batch`'s evaluation block shrinks from ~100 lines to ~5
- [ ] Golden-set test scores byte-identical pre- and post-refactor
- [ ] `gitnexus_impact({target: "evaluate_ad"})` shows no callers outside the new pipeline (or only the documented private tests)
- [ ] DEVLOG entry committed

---

## Key Files

| File | Action |
|------|--------|
| `evaluate/evaluation_pipeline.py` | **NEW** — composite |
| `evaluate/evaluator.py` | Becomes private implementation |
| `evaluate/image_evaluator.py` / `image_scorer.py` / `image_selector.py` | Private |
| `evaluate/video_evaluator.py` / `video_scorer.py` / `video_coherence.py` / `video_attributes.py` | Private |
| `evaluate/coherence_checker.py` | Private |
| `evaluate/confidence_router.py` | Private |
| `evaluate/brief_adherence.py` | Private |
| `evaluate/dimensions.py`, `evaluate/spc_monitor.py`, `evaluate/correlation.py` | Keep as referenced types/utilities |
| `iterate/batch_processor.py` | Shrink evaluation block |
| `tests/test_evaluation/test_golden_set.py` | Migrate 14+ direct callers to the composite |
| `tests/test_evaluation/test_inversion.py` | Migrate `_eval_text` helper |
| `scripts/run_calibration.py` / `scripts/recalibrate_references.py` | Keep using internals (calibration is private to the evaluator owner) — or migrate, decide in grilling |

---

## Out of Scope for PH-04

- Adding a new evaluation dimension
- Changing weights, floors, or improvable-range thresholds
- New evaluator models (e.g. a non-Gemini evaluator)
- SPC algorithm changes

---

## Verification Before Merge

Standard gate plus:
- Golden-set regression — every reference ad's aggregate score must be identical pre/post (within float epsilon).
- Calibration script (`scripts/run_calibration.py`) still runs without modification, or with documented migration.
