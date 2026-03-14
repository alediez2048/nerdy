# P1-08 Primer: Brief Mutation + Escalation

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** P0-06 (evaluator calibration), P1-01 (brief expansion), P1-04 (CoT evaluator), P1-07 (Pareto selection) must be complete. See `docs/DEVLOG.md`.

---

## What Is This Ticket?

P1-08 implements the **brief mutation and escalation** mechanism — the system's answer to "what happens when the feedback loop gets stuck?" When Pareto-optimal regeneration (P1-07) fails to find a non-regressing variant, the problem is not the generator — it is the brief. The system diagnoses the weakest dimension, mutates the brief to address it, and retries. If mutation also fails, it escalates with full diagnostics.

The cycle budget comes from `data/config.yaml` (`max_regeneration_cycles`):

- **Cycle 1:** Normal generation + Pareto selection.
- **Cycle 2:** If Pareto selection returns None, mutate the brief targeting the weakest dimension. Retry generation.
- **Cycle 3:** If still failing, escalate — archive the ad with full diagnostics (all attempts, scores, rationales) for human review.

### Why It Matters

- **The System Knows What It Doesn't Know** (Pillar 4): Escalation is self-awareness in action — the system recognizes when it cannot solve the problem and asks for help rather than burning tokens.
- **Every Token Is an Investment** (Pillar 3): Without a hard cycle cap, a stuck feedback loop silently drains the token budget. Three cycles is the empirically justified limit (R1-Q2).
- Brief mutation is the only approach that tries to fix the root cause (bad input) before giving up. Simply retrying with the same brief yields diminishing returns.
- Escalation diagnostics feed the learning loop — patterns in why briefs fail inform future brief expansion (P1-01).

---

## What Was Already Done

These modules exist and are tested — do NOT recreate them:

| Module | What It Provides |
|--------|-----------------|
| `evaluate/evaluator.py` | `evaluate_ad()` returns `EvaluationResult` with per-dimension scores and rationales |
| `iterate/ledger.py` | `log_event()` for mutation/escalation events; `get_ad_lifecycle()` for full history |
| `iterate/checkpoint.py` | `get_pipeline_state()`, `should_skip_ad()` — resume skips already-escalated ads |
| `generate/seeds.py` | `get_ad_seed()` — deterministic seed per cycle (mutation gets a new cycle number) |
| `data/config.yaml` | `max_regeneration_cycles` (default 3) |
| `data/brand_knowledge.json` | Brand constraints used during brief expansion |

---

## What This Ticket Must Accomplish

### Goal

Build the brief mutation and escalation layer that diagnoses stuck feedback loops, mutates briefs to address the weakest dimension, and escalates with full diagnostics when mutation fails.

### Deliverables Checklist

#### A. Brief Mutation Module (`iterate/brief_mutation.py`)

- [ ] `MutationDiagnosis` dataclass — ad_id, weakest_dimension, score, rationale, suggested_mutation
- [ ] `EscalationReport` dataclass — ad_id, attempts (list of all scores per cycle), diagnosis, mutation_applied, reason_for_escalation
- [ ] `diagnose_weakness(evaluation: EvaluationResult) -> MutationDiagnosis`
  - Identifies the lowest-scoring dimension from the evaluation
  - Extracts the evaluator's rationale for that dimension
  - Generates a specific mutation suggestion (e.g., "strengthen CTA by adding urgency and specific next step")
  - Maps each dimension to concrete brief adjustments:
    - Clarity: simplify message, reduce competing claims
    - Value Proposition: add specific proof points, differentiate from competitors
    - CTA: add urgency, lower friction, be more specific
    - Brand Voice: strengthen audience-specific tone, add few-shot examples
    - Emotional Resonance: target specific emotion (parent worry, student ambition)
- [ ] `mutate_brief(original_brief: dict, diagnosis: MutationDiagnosis) -> dict`
  - Returns a new brief with targeted adjustments based on diagnosis
  - Preserves all original brief fields; adds/modifies only the weak area
  - Logs the mutation to ledger as a `BriefMutated` event
- [ ] `should_escalate(ad_id: str, cycle: int, config: dict) -> bool`
  - Returns True if cycle >= `max_regeneration_cycles` from config
- [ ] `escalate(ad_id: str, attempts: list, diagnosis: MutationDiagnosis) -> EscalationReport`
  - Archives the ad with full diagnostic report
  - Logs an `AdEscalated` event to ledger with all attempts and scores
  - Returns structured report for human review

#### B. Tests (`tests/test_pipeline/test_brief_mutation.py`)

- [ ] TDD first
- [ ] Test `diagnose_weakness` correctly identifies lowest-scoring dimension
- [ ] Test `diagnose_weakness` maps each dimension to appropriate mutation strategy
- [ ] Test `mutate_brief` preserves original fields while adding mutation
- [ ] Test `mutate_brief` logs BriefMutated event to ledger
- [ ] Test `should_escalate` returns False on cycle 1 and 2
- [ ] Test `should_escalate` returns True on cycle 3 (default max_regeneration_cycles)
- [ ] Test `should_escalate` respects custom config override
- [ ] Test `escalate` produces complete EscalationReport with all attempts
- [ ] Test `escalate` logs AdEscalated event to ledger
- [ ] Minimum: 8+ tests

#### C. Documentation

- [ ] Add P1-08 entry in `docs/DEVLOG.md`

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
| Brief mutation + escalation | R1-Q2 | After 2 failures: mutate brief targeting weak dimension. After 3 total: escalate with full diagnostics. Only approach that fixes root cause before giving up. |
| Distilled context | R2-Q4 | Mutation context passed to generator as distilled object, not raw history. |
| Confidence-gated autonomy | R2-Q5 | Escalation is the system's way of saying "I need human help." |

### Integration with P1-07 (Pareto Selection)

The handoff works like this:

1. P1-07 `select_best()` returns None (all variants regressed)
2. P1-08 `diagnose_weakness()` analyzes why
3. P1-08 `mutate_brief()` adjusts the brief
4. Pipeline retries generation with mutated brief (back to P1-07)
5. If P1-07 still returns None, P1-08 `should_escalate()` returns True
6. P1-08 `escalate()` archives with diagnostics

### Files to Create

| File | Why |
|------|-----|
| `iterate/brief_mutation.py` | Diagnosis, mutation, escalation logic |
| `tests/test_pipeline/test_brief_mutation.py` | Mutation + escalation tests |

### Files You Should READ for Context

| File | Why |
|------|-----|
| `evaluate/evaluator.py` | EvaluationResult — the scores and rationales you diagnose |
| `iterate/ledger.py` | Event types and logging patterns |
| `data/config.yaml` | `max_regeneration_cycles` setting |
| `data/brand_knowledge.json` | Brand constraints that inform mutation strategies |
| `docs/reference/prd.md` (R1-Q2) | Full rationale for mutation + escalation design |

---

## Definition of Done

- [ ] `diagnose_weakness()` correctly identifies the lowest-scoring dimension and maps it to a concrete mutation
- [ ] `mutate_brief()` modifies only the targeted area while preserving the rest
- [ ] Mutation logged as `BriefMutated` event in ledger
- [ ] `should_escalate()` triggers on third failure (respects `max_regeneration_cycles` config)
- [ ] `escalate()` produces a complete diagnostic report with all attempts, scores, and rationales
- [ ] Escalation logged as `AdEscalated` event in ledger
- [ ] No hardcoded cycle limits — config-driven
- [ ] Tests pass
- [ ] Lint clean
- [ ] DEVLOG updated
- [ ] Committed on `develop`

---

## Estimated Time: 45-60 minutes

---

## After This Ticket: What Comes Next

**Next P1 tickets:**
- **P1-09** (Distilled context objects) — Compresses the mutation history so the generator sees a compact context instead of raw attempt logs
- **P1-10** (Quality ratchet) — Rolling threshold that incorporates successful mutation outcomes
- **P1-13** (Batch-sequential processor) — Orchestrates the full generate-evaluate-route-regenerate-mutate pipeline across batches

Brief mutation closes the feedback loop's failure path. After this ticket, the pipeline has a complete answer for every ad: publish, improve, mutate, or escalate. No ad is silently abandoned.
