# Phase P4: Autonomous Engine

## Context

P4 transforms the pipeline from a batch-processing tool into a self-healing autonomous engine. Agents replace the monolithic pipeline, SPC drift detection triggers automatic recalibration, and the system learns from its own output patterns. This is v3 scope — the ceiling, not the floor.

## Tickets (7)

### P4-01: Agentic Orchestration Layer
- Replace monolithic pipeline with 4 bounded agents: Researcher → Writer → Editor → Evaluator
- Error boundaries: failure in one agent doesn't cascade
- **AC:** Failures contained, diagnostics logged

### P4-02: Self-Healing Feedback Loop
- Wire: SPC drift detection + brief mutation + quality ratchet + explore trigger
- Simulated quality drop → detected → diagnosed → recovered automatically
- **AC:** Simulated drop detected, diagnosed, recovered

### P4-03: Competitive Intelligence — Automated Refresh + Trends
- Monthly refresh workflow, temporal trend tracking, seasonal analysis
- Strategy shift alerts when competitor patterns change
- **AC:** Trends visible in dashboard, strategy shift alerts fire

### P4-04: Cross-Campaign Transfer
- Tag patterns as universal (structural) vs. campaign-specific (content)
- Enable transferring proven patterns across campaigns
- **AC:** Insights transferable via campaign_scope tags

### P4-05: Performance-Decay Exploration Trigger
- Detect quality plateau (<0.1 improvement over 3 batches)
- Exploit by default, explore on plateau (try new atom combinations)
- **AC:** Exploration triggers, successful patterns promoted

### P4-06: Full Marginal Analysis Engine
- Quality gain per regen attempt, per model, per dimension
- Auto-cap regeneration when marginal gain < 0.2
- **AC:** System caps low-marginal-return regeneration

### P4-07: Narrated Pipeline Replay
- Chronological walkthrough reconstructed from decision ledger
- Every decision explained with reasoning, failures highlighted
- **AC:** Full walkthrough with reasoning

## Dependency Graph

```
P4-01 (Agents) → P4-02 (Self-Healing) → P4-05 (Explore/Exploit)
                       │
P4-03 (Comp Trends) ──┘
P4-04 (Transfer) ── standalone
P4-06 (Marginal Analysis) ── standalone
P4-07 (Narrated Replay) ── standalone (reads ledger)
```

## Rubric Impact

- **Bonus points:** +7 for self-healing/auto quality improvement, +3 for multi-model orchestration
- **Not required** — impressive but doesn't affect core scoring categories
- **Best ROI ticket:** P4-07 (narrated replay) — low effort, high demo value, reads existing ledger

## Status: ⏳ NOT STARTED
