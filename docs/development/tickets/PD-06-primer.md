# PD-06 Primer: Pipeline Iteration Wiring

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** P1-06 (model routing), P1-07 (Pareto selection), P1-08 (brief mutation), P1-10 (quality ratchet). See `docs/DEVLOG.md`.

---

## What Is This Ticket?

PD-06 is the largest and most critical PD ticket. It wires together four fully implemented but completely disconnected iteration components — quality ratchet, Pareto selection, model routing, and brief mutation — into a functioning feedback loop. Currently, the pipeline is single-pass: generate with Flash, evaluate, route (log the decision), done. The routing decision of "escalate" is logged but never acted upon. The quality ratchet computes thresholds but is never called. Pareto selection filters candidates but is never invoked. This ticket creates the missing `iterate/feedback_loop.py` orchestrator and wires everything into `batch_processor.py` so that escalated ads actually get regenerated, re-evaluated, and iteratively improved.

### Why It Matters

- **Every Token Is an Investment** (Pillar 3): Without iteration wiring, the system wastes Flash tokens on marginal ads that could be improved with targeted Pro spend, and never reclaims value from near-threshold ads
- **Prevention Over Detection Over Correction** (Pillar 2): The quality ratchet should prevent threshold regression, but it currently does nothing — its `update_ratchet()` is never called
- **Learning Is Structural** (Pillar 6): Pareto selection prevents dimension collapse during regeneration, but the regeneration loop does not exist yet
- The entire escalation tier (5.5-7.0 score range) is dead code — ads in this range are logged as "escalated" then silently dropped

---

## What Was Already Done

- **P1-06** (`generate/model_router.py`): `route_ad()` returns `RoutingDecision` with "discard"/"escalate"/"publish". Model map includes `escalation: gemini-2.0-pro`. Working and tested.
- **P1-07** (`iterate/pareto_selection.py`): `is_pareto_dominant()`, `select_pareto_front()`, `ParetoCandidate` dataclass. Filters regressing candidates, identifies Pareto-dominant variants, breaks ties with weighted aggregate. Working and tested.
- **P1-08** (`iterate/brief_mutation.py`): Brief mutation for last-resort regeneration. Exists and tested.
- **P1-10** (`iterate/quality_ratchet.py`): `compute_threshold()`, `get_ratchet_state()`, `update_ratchet()`. Formula: `max(base, rolling_N_avg - buffer)`. Working and tested.
- **`iterate/batch_processor.py`**: Calls `route_ad()` at line 170, logs the decision, but:
  - "escalate" branch (line 226) only increments counter and logs — no regeneration
  - `write_batch_checkpoint()` uses hardcoded `batch_avg = 7.0` (line 422) instead of computing from real scores
  - Never calls `get_ratchet_state()` or `update_ratchet()`

---

## What This Ticket Must Accomplish

### Goal

Create `iterate/feedback_loop.py` and wire it into `batch_processor.py` so that escalated ads undergo iterative regeneration with Pro model, Pareto selection, and optional brief mutation — transforming the pipeline from single-pass to multi-cycle.

### Deliverables Checklist

#### A. Create Feedback Loop Orchestrator (`iterate/feedback_loop.py`)

- [ ] `run_feedback_cycle(ad, scores, cycle_number, config, ledger_path) -> FeedbackResult` — single iteration cycle
- [ ] `run_feedback_loop(ad, initial_scores, config, ledger_path) -> FeedbackResult` — full loop (up to max cycles)
- [ ] Cycle logic:
  - Cycle 1-2: Generate 3-5 variants using Pro model (`gemini-2.0-pro`), evaluate all, select best via Pareto dominance, re-route
  - Cycle 3 (if still failing): Mutate brief via `brief_mutation.py`, generate one more set, evaluate, final route
  - After cycle 3: Discard with diagnostics (log why it failed across all cycles)
- [ ] `FeedbackResult` dataclass: `final_ad`, `final_scores`, `decision` (publish/discard), `cycles_used`, `variants_generated`, `brief_mutated` (bool), `diagnostics` (list of per-cycle summaries)
- [ ] Ledger logging: `FeedbackCycleCompleted` event per cycle with variants tried, scores, Pareto winner, decision

#### B. Wire Ratchet into Batch Processor (`iterate/batch_processor.py`)

- [ ] Collect all `AdEvaluated` scores during batch processing (accumulate in list)
- [ ] Replace hardcoded `batch_avg = 7.0` (line 422) with real average computed from collected scores
- [ ] After batch completes, call `update_ratchet()` with the real batch average
- [ ] Use `get_ratchet_state().current_threshold` as the effective threshold passed to `route_ad()` (instead of relying solely on config)

#### C. Wire Feedback Loop for Escalated Ads (`iterate/batch_processor.py`)

- [ ] In the "escalate" branch (line 226), call `run_feedback_loop()` instead of just logging
- [ ] Use the `FeedbackResult` to determine final outcome: publish (with image generation) or discard
- [ ] Update batch counters: if feedback loop publishes, increment `published`; if discards, increment `discarded`; track `regenerated` for total escalations attempted
- [ ] Log `AdPublished` or `AdDiscarded` event based on feedback loop result

#### D. Tests (`tests/test_pipeline/test_feedback_loop.py`)

- [ ] TDD first: write tests before implementation
- [ ] Test single cycle: escalated ad generates variants, Pareto selects best, re-routes
- [ ] Test publish path: variant scores above threshold after 1 cycle
- [ ] Test multi-cycle: first cycle still escalated, second cycle publishes
- [ ] Test brief mutation: 2 cycles fail, cycle 3 mutates brief, generates new variants
- [ ] Test max cycles discard: all 3 cycles fail, ad is discarded with diagnostics
- [ ] Test ratchet wiring: batch_avg computed from real scores, update_ratchet called
- [ ] Test ledger events: FeedbackCycleCompleted events logged per cycle
- [ ] Minimum: 8+ tests

#### E. Documentation

- [ ] Add PD-06 entry in `docs/DEVLOG.md`
- [ ] Update decision log if architectural choices were made

---

## Branch & Merge Workflow

```bash
git switch main && git pull
git switch -c feature/PD-06-pipeline-iteration-wiring
# ... implement ...
git push -u origin feature/PD-06-pipeline-iteration-wiring
```

Conventional Commits: `test:`, `feat:`, `fix:`, `docs:`

---

## Important Context

### Architectural Decisions

| Decision | Reference | Summary |
|----------|-----------|---------|
| Tiered routing | R1-Q4 | Flash for first draft, Pro only for escalation — minimize token spend |
| Pareto selection | R1-Q5 | Prevent dimension collapse: never accept a variant that regresses on any dimension |
| Quality ratchet | R1-Q9 | Monotonically non-decreasing threshold: `max(base, rolling_avg - buffer)` |
| Max regeneration cycles | R1-Q5, R1-Q9 | 2 regen cycles + 1 brief mutation cycle = 3 max before discard |
| Brief mutation as last resort | P1-08 | Mutate the brief only after 2 failed regeneration cycles |

### Files to Create

| File | Why |
|------|-----|
| `iterate/feedback_loop.py` | Orchestrator: ties ratchet + Pareto + routing + brief mutation into iteration cycles |
| `tests/test_pipeline/test_feedback_loop.py` | Tests for the feedback loop |

### Files to Modify

| File | Action |
|------|--------|
| `iterate/batch_processor.py` | Wire ratchet (real batch_avg), call feedback loop for escalated ads |
| `docs/DEVLOG.md` | Add PD-06 entry |

### Files You Should NOT Modify

- `iterate/quality_ratchet.py` — already implemented, use as-is
- `iterate/pareto_selection.py` — already implemented, use as-is
- `generate/model_router.py` — already implemented, use as-is (call `route_ad()` with Pro model context)
- `evaluate/evaluator.py` — already implemented, call `evaluate_ad()` for re-evaluation

### Files You Should READ for Context

| File | Why |
|------|-----|
| `iterate/batch_processor.py` | Current single-pass pipeline to extend — especially lines 155-244 (per-ad processing) and lines 405-446 (batch checkpoint with hardcoded avg) |
| `iterate/quality_ratchet.py` | `compute_threshold()`, `get_ratchet_state()`, `update_ratchet()` — APIs to call |
| `iterate/pareto_selection.py` | `ParetoCandidate`, `is_pareto_dominant()`, `select_pareto_front()` — APIs to call in variant selection |
| `generate/model_router.py` | `route_ad()`, `RoutingDecision`, `_MODEL_MAP` — routing API and model map (escalation uses `gemini-2.0-pro`) |
| `iterate/brief_mutation.py` | Brief mutation API for cycle-3 last resort |
| `evaluate/evaluator.py` | `evaluate_ad()` — re-evaluation API for generated variants |
| `docs/reference/prd.md` | Ticket acceptance criteria |
| `docs/reference/interviews.md` | R1-Q4 (model routing), R1-Q5 (Pareto), R1-Q9 (ratchet) |

### Cursor Rules to Follow

- `.cursor/rules/pipeline-patterns.mdc`

---

## Suggested Implementation Pattern

**Pipeline flow after wiring:**

```
Brief -> Expand -> Generate (Flash) -> Evaluate -> Route
  |-- >= threshold: Publish -> Image
  |-- 5.5 to threshold: Escalate -> feedback_loop.run_feedback_loop()
  |     |-- Cycle 1-2: Generate 3-5 variants (Pro) -> Evaluate all -> Pareto select -> Re-route
  |     |-- Cycle 3: Mutate brief -> Generate variants (Pro) -> Evaluate -> Pareto -> Final route
  |     |-- Still failing: Discard with diagnostics
  |-- < 5.5: Discard
```

**feedback_loop.py skeleton:**

```python
@dataclass
class FeedbackResult:
    final_ad: Any
    final_scores: dict[str, float]
    decision: str  # "publish" | "discard"
    cycles_used: int
    variants_generated: int
    brief_mutated: bool
    diagnostics: list[dict[str, Any]]

def run_feedback_loop(
    ad: Any,
    initial_scores: dict[str, float],
    brief: dict[str, Any],
    config: dict[str, Any],
    ledger_path: str,
) -> FeedbackResult:
    max_cycles = config.get("max_regen_cycles", 3)
    mutation_cycle = config.get("mutation_cycle", 3)

    for cycle in range(1, max_cycles + 1):
        if cycle == mutation_cycle:
            brief = mutate_brief(brief, ...)

        variants = generate_variants(ad, brief, n=config.get("pareto_variants", 3), model="gemini-2.0-pro")
        evaluated = [evaluate_ad(v, ...) for v in variants]
        candidates = [ParetoCandidate(...) for v, e in zip(variants, evaluated)]
        winner = select_pareto_front(candidates, prior_scores=initial_scores)

        if winner and route_ad(winner.ad_id, winner.weighted_average, ...).decision == "publish":
            return FeedbackResult(decision="publish", cycles_used=cycle, ...)

    return FeedbackResult(decision="discard", cycles_used=max_cycles, ...)
```

**batch_processor.py wiring (escalate branch, line 226):**

```python
elif routing.decision == "escalate":
    result.regenerated += 1
    from iterate.feedback_loop import run_feedback_loop
    feedback = run_feedback_loop(
        ad=ad,
        initial_scores=evaluation.scores,
        brief=brief,
        config=config,
        ledger_path=ledger_path,
    )
    if feedback.decision == "publish":
        result.published += 1
        # Generate image for the winning variant
        winning_image = _generate_and_select_image(...)
        log_event(ledger_path, {"event_type": "AdPublished", ...})
    else:
        result.discarded += 1
        log_event(ledger_path, {"event_type": "AdDiscarded", ...})
```

---

## Edge Cases to Handle

1. **All variants regress** — Pareto selection returns None because every variant is worse on at least one dimension vs. the original. Should trigger brief mutation on next cycle or discard if already at max cycles.
2. **Pro model API failure** — `generate_variants` fails mid-cycle. Catch, log, treat as cycle failure, continue to next cycle or discard.
3. **Empty variant set** — Generation returns 0 variants (all failed). Count as failed cycle.
4. **Ratchet threshold above 7.0** — If rolling average pushes threshold to, say, 7.3, ads scoring 7.0-7.3 now get escalated instead of published. The feedback loop must respect the ratcheted threshold.
5. **Brief mutation produces worse brief** — Cycle 3 mutated brief generates even lower scores. Discard with diagnostics showing the regression.
6. **Config missing** — `pareto_variants`, `max_regen_cycles`, `mutation_cycle` not in config. Use sensible defaults (3, 3, 3).

---

## Definition of Done

- [ ] `iterate/feedback_loop.py` exists with `run_feedback_loop()` orchestrating multi-cycle iteration
- [ ] Escalated ads in `batch_processor.py` call `run_feedback_loop()` instead of just logging
- [ ] `write_batch_checkpoint()` computes real batch average from collected scores (not hardcoded 7.0)
- [ ] `update_ratchet()` called after each batch with real average
- [ ] Pareto selection used to pick best variant per cycle
- [ ] Brief mutation triggered on cycle 3 if prior cycles failed
- [ ] Ads discarded after max cycles include diagnostics
- [ ] `FeedbackCycleCompleted` ledger events logged per cycle
- [ ] Tests pass (`python -m pytest tests/ -v`)
- [ ] Lint clean (`ruff check . --fix`)
- [ ] DEVLOG updated
- [ ] Feature branch pushed

---

## Estimated Time

| Task | Estimate |
|------|----------|
| Write tests (TDD) | 45 min |
| Create `iterate/feedback_loop.py` | 60 min |
| Wire ratchet into `batch_processor.py` | 30 min |
| Wire feedback loop into escalate branch | 30 min |
| Integration testing and edge cases | 30 min |
| DEVLOG update | 10 min |

**Total: 3-4 hours**

---

## After This Ticket: What Comes Next

- With PD-06 complete, the pipeline transforms from single-pass to iterative: escalated ads actually get regenerated, improving output quality and token efficiency
- PD-07+ tickets can build on the iteration infrastructure (e.g., iteration analytics, cycle-count dashboards)
- The quality ratchet becomes a live system, raising the bar as the pipeline improves
