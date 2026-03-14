# P1-09 Primer: Distilled Context Objects

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** P0-06 (evaluator calibration), P1-02 (ad generator), P1-04 (CoT evaluator), P1-07 (Pareto selection), P1-08 (brief mutation) must be complete. See `docs/DEVLOG.md`.

---

## What Is This Ticket?

P1-09 implements **distilled context objects** — compact, structured summaries that replace raw iteration history in the generator prompt. As the pipeline iterates (generate, evaluate, regenerate, mutate), the context window fills with prior attempts, scores, and rationales. Without distillation, prompt size grows linearly with cycle depth, eventually blowing context limits or drowning the generator in noise.

The distilled context object for each regeneration cycle contains exactly three things:

1. **Best attempt so far** — the highest-scoring variant from the prior cycle
2. **What needs to improve** — the weakest dimension and its contrastive rationale ("what a +2 version would look like")
3. **Anti-patterns to avoid** — specific failure patterns from prior attempts ("do NOT use generic CTAs like 'Learn More'")

This replaces ALL raw history. The prompt stays compact regardless of whether the ad is on cycle 1 or cycle 5.

### Why It Matters

- **Every Token Is an Investment** (Pillar 3): Raw history wastes tokens on information the generator does not need. The destination matters, not the journey.
- **Prevention Over Detection Over Correction** (Pillar 2): Compact prompts prevent context overflow rather than detecting and truncating it.
- On Gemini's free tier, context tokens are not free — every token in the prompt is a token not available for generation.
- Without distillation, cycle 4 prompts contain 4x the context of cycle 1, but the generator only needs the latest state. This is pure waste.

---

## What Was Already Done

These modules exist and are tested — do NOT recreate them:

| Module | What It Provides |
|--------|-----------------|
| `evaluate/evaluator.py` | `evaluate_ad()` returns `EvaluationResult` with per-dimension scores and contrastive rationales |
| `iterate/ledger.py` | `log_event()` for context distillation events; `read_events()`, `get_ad_lifecycle()` for full history |
| `iterate/checkpoint.py` | `get_pipeline_state()` — tracks which ads are in which cycle |
| `generate/seeds.py` | `get_ad_seed()` — deterministic seeds per cycle |
| `data/config.yaml` | Pipeline parameters |

---

## What This Ticket Must Accomplish

### Goal

Build the context distillation layer that compresses full iteration history into a fixed-size context object for the generator prompt, ensuring prompt size stays constant regardless of cycle depth.

### Deliverables Checklist

#### A. Context Distiller Module (`iterate/context_distiller.py`)

- [ ] `DistilledContext` dataclass:
  - `ad_id: str`
  - `cycle: int`
  - `best_attempt: str` — the ad copy text of the best variant so far
  - `best_scores: dict[str, float]` — per-dimension scores of best attempt
  - `weakest_dimension: str` — the dimension most needing improvement
  - `improvement_guidance: str` — contrastive rationale ("what +2 looks like")
  - `anti_patterns: list[str]` — specific things to avoid based on failed attempts
  - `token_count: int` — approximate token count of this context object
- [ ] `distill(ad_id: str, ledger_path: str) -> DistilledContext`
  - Reads all events for this ad_id from the ledger
  - Identifies the best attempt across all cycles (highest weighted average)
  - Extracts the weakest dimension and its contrastive rationale from the most recent evaluation
  - Compiles anti-patterns from failed attempts (low-scoring dimensions with their rationales)
  - Deduplicates anti-patterns (no repeats across cycles)
  - Returns a fixed-size DistilledContext regardless of cycle count
- [ ] `format_for_prompt(context: DistilledContext) -> str`
  - Renders the distilled context as a structured prompt section
  - Uses clear headers: BEST SO FAR, IMPROVE THIS, AVOID THESE
  - Total output capped at a reasonable token budget (configurable, default ~300 tokens)
- [ ] `get_context_efficiency(ad_id: str, ledger_path: str) -> dict`
  - Compares raw history size vs. distilled context size
  - Returns compression ratio and token savings

#### B. Tests (`tests/test_pipeline/test_context_distiller.py`)

- [ ] TDD first
- [ ] Test `distill` with single cycle returns best attempt and weakest dimension
- [ ] Test `distill` with 3 cycles still produces fixed-size output
- [ ] Test `distill` with 5 cycles produces same-size output as 3 cycles (size invariance)
- [ ] Test `distill` correctly identifies best attempt across multiple cycles
- [ ] Test anti-patterns are deduplicated across cycles
- [ ] Test `format_for_prompt` output stays within token budget
- [ ] Test `format_for_prompt` includes all three sections (best, improve, avoid)
- [ ] Test `get_context_efficiency` reports compression ratio > 1 for multi-cycle ads
- [ ] Minimum: 7+ tests

#### C. Documentation

- [ ] Add P1-09 entry in `docs/DEVLOG.md`

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
| Distilled context objects | R2-Q4 | Compact distillation per cycle: best attempt + improvement needed + anti-patterns. Replaces all raw history. Generator needs the destination, not the journey. |
| Contrastive rationales | R3-Q10 | "What would +2 look like?" — this is the improvement_guidance field. Dramatically reduces regeneration cycles. |
| Token awareness | R1-Q7 | Context tokens count against the budget. Distillation is a token-saving mechanism. |

### Integration Points

The distilled context slots into the generation pipeline like this:

1. P1-07 (Pareto selection) completes a cycle
2. **P1-09 `distill()` compresses the cycle into a DistilledContext**
3. P1-02 (ad generator) receives `format_for_prompt(context)` as part of its input
4. Generator produces variants informed by what worked, what to improve, and what to avoid
5. Back to P1-07 for the next cycle

### Files to Create

| File | Why |
|------|-----|
| `iterate/context_distiller.py` | Distillation logic, prompt formatting, efficiency tracking |
| `tests/test_pipeline/test_context_distiller.py` | Distillation + formatting tests |

### Files You Should READ for Context

| File | Why |
|------|-----|
| `evaluate/evaluator.py` | EvaluationResult — the scores and rationales you distill |
| `iterate/ledger.py` | `get_ad_lifecycle()` — how to retrieve full history for an ad |
| `docs/reference/prd.md` (R2-Q4, R3-Q10) | Full rationale for distilled context and contrastive rationales |

---

## Definition of Done

- [ ] `distill()` produces a fixed-size DistilledContext regardless of cycle depth
- [ ] Context includes best attempt, weakest dimension with improvement guidance, and deduplicated anti-patterns
- [ ] `format_for_prompt()` output stays within token budget
- [ ] Prompt size is constant whether the ad is on cycle 1 or cycle 5
- [ ] Anti-patterns are deduplicated across cycles
- [ ] Context distillation events logged to ledger
- [ ] Tests pass
- [ ] Lint clean
- [ ] DEVLOG updated
- [ ] Committed on `develop`

---

## Estimated Time: 30-45 minutes

---

## After This Ticket: What Comes Next

**Next P1 tickets:**
- **P1-10** (Quality ratchet) — Uses distilled context scores to compute rolling thresholds
- **P1-11** (Token attribution engine) — Tracks context token savings from distillation
- **P1-13** (Batch-sequential processor) — Orchestrates the full pipeline with distilled context flowing between cycles

Distilled context is the pipeline's memory compression layer. Without it, deep iteration cycles become token-prohibitive on the free tier. With it, the system can iterate indefinitely while keeping prompt costs constant.
