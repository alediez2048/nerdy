# PH-05 Primer: AdProcessingStage State Machine

**For:** New Agent session
**Project:** Ad-Ops-Autopilot
**Date:** May 2026
**Phase plan:** [`PH-00-phase-plan.md`](PH-00-phase-plan.md)
**Depends on:** PH-04 (EvaluationPipeline composite)
**Branch:** `feature/PH-05-stage-machine`

---

## What Is This Ticket?

After PH-03 (orchestrator) and PH-04 (evaluation composite), `iterate/batch_processor.process_batch` still drives a ~150-line linear sequence of stages with **implicit, undocumented preconditions**:

```
expand_brief  →  generate_ad  →  evaluate (via EvaluationPipeline)
              →  route_ad     →  generate_image (only if publishable)
              →  score_image  →  score_adherence  →  publish_or_regen
```

If a future contributor reorders or inserts a stage, nothing catches it at type-check time. Bugs surface only when a downstream consumer reads a field that the prior stage was supposed to populate.

This ticket adds a **type-level guard**: each stage takes an `Ad<StageN>` and returns an `Ad<StageN+1>`. The compiler/type-checker (mypy, pyright) prevents calling a later stage with an earlier-stage input.

---

## What This Ticket Must Accomplish

### Goal

A typed stage progression. Two viable approaches; decide in grilling:

**Approach A — discriminated unions / generics:**
```python
class AdAtStage(Generic[Stage]): ...
def stage_generate(ad: AdAtStage[Brief]) -> AdAtStage[Generated]: ...
def stage_evaluate(ad: AdAtStage[Generated]) -> AdAtStage[Evaluated]: ...
```

**Approach B — runtime tag + runtime guard:**
```python
@dataclass
class Ad:
    stage: AdStage           # Enum
    # ... fields, populated as stages advance
def stage_generate(ad: Ad) -> Ad:
    assert ad.stage == AdStage.BRIEF, f"expected BRIEF, got {ad.stage}"
    ...
    return replace(ad, stage=AdStage.GENERATED, copy=...)
```

The orchestrator (PH-03) calls stages in order; the stage type/tag makes "out of order" structurally impossible (Approach A) or loud-fail at runtime (Approach B).

### Deliverables Checklist

#### A. Design (grilling session — BEFORE implementation)
- [ ] Pick Approach A or B based on: existing codebase typing strictness, contributor familiarity, refactor surface
- [ ] Enumerate the stages (likely: `BRIEF`, `EXPANDED`, `GENERATED`, `EVALUATED`, `ROUTED`, `IMAGED`, `SCORED`, `PUBLISHED`, `DISCARDED`)
- [ ] Decide whether to model regeneration cycles as "back to GENERATED" or as a parallel attempt-count dimension
- [ ] Confirm the EvaluationPipeline composite slots in cleanly (its result lives on the `EVALUATED` stage)

#### B. Implementation
- [ ] Create `iterate/ad_stages.py` (or similar) with the stage enum + typed Ad
- [ ] Convert `batch_processor.process_batch` to a `for brief in briefs: ad = stage_expand(brief); ad = stage_generate(ad); ...` chain
- [ ] Each `stage_*` function is a small wrapper that calls the existing generate/evaluate/score code
- [ ] Type-check the codebase: `mypy iterate/ evaluate/ generate/` should not regress

#### C. Testing
- [ ] All existing tests pass
- [ ] New tests: each stage in isolation (e.g. "given an `Ad<Generated>`, `stage_evaluate` returns `Ad<Evaluated>` with populated scores")
- [ ] Negative test: type-checker rejects calling `stage_score_image` on an `Ad<Brief>` (mypy reveal_type or equivalent)

---

## Acceptance Criteria

- [ ] `process_batch` reads as a clear stage chain — adding a new stage is one new function + one new chain entry
- [ ] Type-checker (mypy/pyright) prevents calling a stage with the wrong input stage (Approach A) — or all stages fail loudly with a meaningful assertion (Approach B)
- [ ] No silent miscalls possible: a test that intentionally calls stages out of order must fail
- [ ] DEVLOG entry committed

---

## Key Files

| File | Action |
|------|--------|
| `iterate/ad_stages.py` | **NEW** — stage enum + typed Ad |
| `iterate/batch_processor.py` | Rewrite the inner loop as a stage chain |
| `iterate/pipeline_orchestrator.py` (from PH-03) | Calls stages via the chain |
| `generate/ad_generator.py`, `evaluate/evaluation_pipeline.py`, etc. | No direct change — wrapped by stage_* functions |
| `tests/test_pipeline/` | New stage-isolation tests |

---

## Out of Scope for PH-05

- Adding new stages (e.g. a moderation step)
- Persisting stage progression to Postgres
- Changing what each stage *does* — only how callers express the order

---

## Verification Before Merge

Standard gate plus:
- `mypy` / `pyright` runs cleanly on the touched modules.
- Adversarial test: a unit test that deliberately calls `stage_score_image(Ad<Brief>)` is rejected at type-check time (or fails at runtime, depending on approach).
