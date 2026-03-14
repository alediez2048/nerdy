# P1-10 Primer: Quality Ratchet

**Project:** Ad-Ops-Autopilot  
**Phase:** 1 — Core Pipeline (v1)

## Description

Rolling high-water mark (R1-Q9): effective threshold = max(7.0, rolling_5batch_avg − 0.5). The quality bar only goes up. The 7.0 absolute floor is immutable.

**Acceptance:** Threshold only increases; plot shows monotonic bar; standards never regress.
