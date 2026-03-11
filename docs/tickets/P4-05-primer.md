# P4-05 Primer: Performance-Decay Exploration Trigger

**Project:** Ad-Ops-Autopilot  
**Phase:** 4 — Autonomous Engine (v3)

## Description

Explore-exploit logic (R2-Q9): exploit by default. When rolling average plateaus (<0.1 improvement over 3 batches), increase exploration rate until new pattern breaks plateau. Successful explorations promoted to proven library.

**Acceptance:** Exploration triggers on plateau; successful patterns promoted; token-efficient (explore only when needed).
