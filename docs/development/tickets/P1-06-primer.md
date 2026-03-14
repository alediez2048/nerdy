# P1-06 Primer: Tiered Model Routing

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** P0-06 (evaluator calibration), P0-08 (checkpoint-resume), P1-04 (CoT evaluator), P1-05 (adaptive weighting) must be complete. See `docs/DEVLOG.md`.

---

## What Is This Ticket?

P1-06 implements **tiered model routing** so the pipeline concentrates expensive Gemini Pro tokens on ads that are actually improvable. After Flash generates a first draft and the evaluator scores it, routing logic triages the result into three buckets:

- **< 5.5** — Discard immediately. Cheap failure; not worth improving.
- **5.5 - 7.0** — Escalate to Gemini Pro for regeneration. This is the improvable range where Pro's quality delta justifies the cost.
- **> 7.0** — Publish directly. Already meets the quality threshold; no further spend needed.

The thresholds come from `data/config.yaml` (`improvable_range: [5.5, 7.0]`), making them tunable without code changes.

### Why It Matters

- **Every Token Is an Investment** (Pillar 3): 40-60% token reduction by not throwing Pro tokens at hopeless or already-good ads.
- **Multi-model orchestration with clear rationale** earns +3 bonus points on the rubric.
- Tiered routing is the economic backbone of the pipeline — without it, Pro gets called on every ad regardless of expected marginal gain.
- The routing decision itself is logged to the ledger, making the cost/quality tradeoff visible and auditable.

---

## What Was Already Done

These modules exist and are tested — do NOT recreate them:

| Module | What It Provides |
|--------|-----------------|
| `evaluate/evaluator.py` | `evaluate_ad()` returns `EvaluationResult` with per-dimension scores and weighted average |
| `iterate/ledger.py` | `log_event()` for appending routing decisions; `read_events()` for analysis |
| `iterate/checkpoint.py` | `get_pipeline_state()`, `should_skip_ad()` — skip already-routed ads on resume |
| `iterate/retry.py` | `retry_with_backoff()` — wraps API calls with exponential backoff |
| `generate/seeds.py` | `get_ad_seed()` — deterministic seed per ad/cycle |
| `data/config.yaml` | `improvable_range: [5.5, 7.0]` and model parameters |

---

## What This Ticket Must Accomplish

### Goal

Build the model routing layer that reads evaluation scores and routes ads to the correct processing path (discard / escalate / publish), logging every routing decision with full cost attribution.

### Deliverables Checklist

#### A. Model Router Module (`generate/model_router.py`)

- [ ] `RoutingDecision` dataclass — ad_id, score, decision (discard | escalate | publish), model_used, reason
- [ ] `route_ad(evaluation: EvaluationResult, config: dict) -> RoutingDecision`
  - Reads `improvable_range` from config (default `[5.5, 7.0]`)
  - Score < lower bound: return discard decision
  - Score >= upper bound: return publish decision
  - Score in range: return escalate decision (target model: Gemini Pro)
  - Logs the routing decision to ledger via `log_event()`
- [ ] `get_model_for_stage(stage: str, routing: RoutingDecision) -> str`
  - Returns the appropriate model identifier based on stage and routing
  - First draft always uses Flash; escalation uses Pro
- [ ] `get_routing_stats(ledger_path: str) -> dict`
  - Reads ledger to compute: total routed, discarded count, escalated count, published count, estimated token savings vs. all-Pro baseline

#### B. Tests (`tests/test_pipeline/test_model_router.py`)

- [ ] TDD first
- [ ] Test score < 5.5 routes to discard
- [ ] Test score >= 7.0 routes to publish
- [ ] Test score in [5.5, 7.0) routes to escalate
- [ ] Test boundary values (exactly 5.5 and exactly 7.0)
- [ ] Test custom improvable_range from config overrides defaults
- [ ] Test routing decision is logged to ledger
- [ ] Test `get_routing_stats` computes correct counts from ledger
- [ ] Minimum: 7+ tests

#### C. Documentation

- [ ] Add P1-06 entry in `docs/DEVLOG.md`

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
| Tiered model routing | R1-Q4 | Flash for drafts + triage. Pro only for borderline (5.5-7.0). Below 5.5 discarded cheap; above 7.0 passes cheap. 40-60% token reduction. |
| Token attribution | R1-Q7 | Every API call tagged with model, stage, ad_id. Marginal analysis: quality gain per regen attempt. |
| Checkpoint-resume | R3-Q2 | Routing decisions are checkpointed — resume skips already-routed ads. |

### Files to Create

| File | Why |
|------|-----|
| `generate/model_router.py` | Routing logic, decision dataclass, stats |
| `tests/test_pipeline/test_model_router.py` | Routing + stats tests |

### Files You Should READ for Context

| File | Why |
|------|-----|
| `evaluate/evaluator.py` | EvaluationResult structure you consume |
| `data/config.yaml` | `improvable_range` and model config |
| `iterate/ledger.py` | How to log routing decisions |
| `.cursor/rules/pipeline-patterns.mdc` | Pipeline architecture spec |
| `docs/reference/prd.md` (R1-Q4) | Full rationale for tiered routing |

---

## Definition of Done

- [ ] `route_ad()` correctly triages into discard / escalate / publish based on `improvable_range`
- [ ] Every routing decision logged to ledger with model, score, and reason
- [ ] `get_routing_stats()` shows token concentration on improvable range
- [ ] Boundary values handled correctly (5.5 and 7.0)
- [ ] Config-driven thresholds — no hardcoded magic numbers
- [ ] Tests pass
- [ ] Lint clean
- [ ] DEVLOG updated
- [ ] Committed on `develop`

---

## Estimated Time: 30-45 minutes

---

## After This Ticket: What Comes Next

**Next P1 tickets:**
- **P1-07** (Pareto-optimal regeneration) — Uses routing decisions to determine which ads enter the regeneration loop
- **P1-08** (Brief mutation + escalation) — Handles ads that fail even after Pro escalation
- **P1-11** (Token attribution engine) — Builds on routing stats for full cost-per-publishable-ad tracking

The router is the economic gatekeeper: every downstream ticket (regeneration, mutation, attribution) depends on routing decisions being logged and queryable.
