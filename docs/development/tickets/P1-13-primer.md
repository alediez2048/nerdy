# P1-13 Primer: Batch-Sequential Processor

**Project:** Ad-Ops-Autopilot  
**Phase:** 1 — Core Pipeline (v1)

## Description

Process ads in batches of 10 (R3-Q9). Within batch: all generation in parallel → all evaluation in parallel → regeneration decisions → all regeneration in parallel. Shared state updated between batches only. Batch boundaries = natural checkpoints.

**Acceptance:** 50+ ads processed; batch boundaries create checkpoints; parallel within stage, sequential across stages.
