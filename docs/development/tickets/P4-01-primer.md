# P4-01 Primer: Agentic Orchestration Layer

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** P0–P3 complete. See `docs/development/DEVLOG.md`.

---

## What Is This Ticket?

P4-01 introduces an **agentic orchestration layer** — four specialized agents (Researcher → Writer → Editor → Evaluator) that replace the monolithic `process_batch()` function. Each agent has bounded contracts, error boundaries, and diagnostic logging.

### Why It Matters

- **Pillar 1: Decomposition Is the Architecture** — Each agent owns one stage of the pipeline with clear input/output contracts
- **R3-Q1:** Linear pipeline with error boundaries gives 90% of agentic value at 20% of complexity
- Error containment: a Writer failure doesn't crash the Evaluator
- Diagnostic logging: every agent logs its decisions, enabling narrated replay (P4-07)
- Parallelism happens **across briefs** (multiple ads processed simultaneously), not within a single ad's pipeline

---

## What Was Already Done

- `iterate/batch_processor.py` — Current monolithic batch processing: expand → generate → evaluate → route → regenerate → finalize
- `run_pipeline.py` — CLI entry point calling `process_batch()` sequentially
- `iterate/ledger.py` — Append-only event logging with `log_event()`, `read_events()`, `read_events_filtered()`, `get_ad_lifecycle()`
- `iterate/checkpoint.py` — `PipelineState` reconstruction from ledger, `should_skip_ad()` for resume
- `evaluate/evaluator.py` — `evaluate_ad()` with 5-step CoT, confidence flags, contrastive rationales, returns `EvaluationResult`
- `generate/brief_expansion.py` — `expand_brief()` with grounding constraints, returns `ExpandedBrief`
- `generate/ad_generator.py` — `generate_ad()` with reference-decompose-recombine, returns `GeneratedAd`
- `generate/compliance.py` — Three-layer compliance filtering

---

## What This Ticket Must Accomplish

### Goal

Refactor the pipeline into four agents with bounded contracts and error boundaries, so failures are contained and each stage is independently testable.

### Deliverables Checklist

#### A. Agent Definitions

Create `iterate/agents.py`:

- [ ] `AgentResult` dataclass — standardized output: `success: bool`, `output: dict`, `error: str | None`, `diagnostics: dict`
- [ ] `ResearcherAgent` — Takes brief → calls `expand_brief()` → returns `ExpandedBrief` + competitive context
- [ ] `WriterAgent` — Takes `ExpandedBrief` → calls `generate_ad()` → returns `GeneratedAd`
- [ ] `EditorAgent` — Takes `GeneratedAd` + `EvaluationResult` → decides: publish / regenerate / discard. Applies compliance check
- [ ] `EvaluatorAgent` — Takes `GeneratedAd` → calls `evaluate_ad()` → returns `EvaluationResult`
- [ ] Each agent has `execute(input) -> AgentResult` with try/except error boundary

#### B. Error Boundaries

- [ ] Each agent wraps its work in try/except, catching all exceptions
- [ ] On failure: returns `AgentResult(success=False, error=str(e), diagnostics={...})`
- [ ] Failure in one agent does NOT propagate to other agents
- [ ] Failed ads skip downstream agents (not discarded — logged as "AgentFailed" for retry)

#### C. Agent Pipeline Orchestrator

Create or refactor `iterate/orchestrator.py`:

- [ ] `run_agent_pipeline(brief, config) -> AgentResult` — sequential: Researcher → Writer → Evaluator → Editor
- [ ] Diagnostic logging at each handoff (input/output size, duration, success/fail)
- [ ] Ledger events: `AgentStarted`, `AgentCompleted`, `AgentFailed` with agent_name + diagnostics

#### D. Parallel Brief Processing

- [ ] Process multiple briefs concurrently (each brief gets its own agent pipeline)
- [ ] Use sequential processing by default (parallel is opt-in via config)
- [ ] Concurrency limit configurable in `config.yaml`

### Files to Create/Modify

| File | Action |
|------|--------|
| `iterate/agents.py` | **Create** — Agent definitions + AgentResult |
| `iterate/orchestrator.py` | **Create** — Agent pipeline coordinator |
| `tests/test_pipeline/test_agents.py` | **Create** — Agent tests |
| `data/config.yaml` | **Modify** — Add agent config section |

### Files to READ for Context

| File | Why |
|------|-----|
| `iterate/batch_processor.py` | Current orchestration — understand what agents replace |
| `iterate/ledger.py` | Event logging interface agents will use |
| `iterate/checkpoint.py` | State reconstruction agents will query |
| `evaluate/evaluator.py` | EvaluatorAgent wraps this |
| `generate/brief_expansion.py` | ResearcherAgent wraps this |
| `generate/ad_generator.py` | WriterAgent wraps this |
| `generate/compliance.py` | EditorAgent uses compliance filtering |

---

## Important Context

### Architectural Decisions

| Decision | Reference | Summary |
|----------|-----------|---------|
| Linear pipeline, not DAG | R3-Q1 | Sequential agents, not complex graph — 90% value at 20% complexity |
| Error boundaries per agent | R3-Q1 | Failures contained; diagnostics logged |
| Parallelism across briefs | R3-Q1 | Multiple ads in parallel, NOT multiple agents within one ad |
| Append-only ledger | R2-Q8 | All agent events logged for replay |

### Agent Contract

```
Input: typed dict/dataclass
Output: AgentResult(success, output, error, diagnostics)
Side effects: ledger writes only
```

---

## Definition of Done

- [ ] Four agents defined with bounded contracts
- [ ] Error boundaries prevent cascading failures
- [ ] Agent pipeline processes a brief end-to-end
- [ ] Diagnostic logging at every handoff
- [ ] Tests verify: success path, failure containment, diagnostic output
- [ ] Existing pipeline behavior preserved (agents produce same results)

---

## Estimated Time: 45–60 minutes
