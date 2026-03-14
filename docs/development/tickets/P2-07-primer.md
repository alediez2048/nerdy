# P2-07 Primer: End-to-End Integration Test

**Project:** Ad-Ops-Autopilot  
**Phase:** 2 — Testing & Validation

## Description

Full pipeline with checkpoint-resume (R3-Q2): start pipeline, kill mid-batch, resume. Verify resumed run produces identical output to clean run. No duplicated work, no lost work.

**Acceptance:** Resumed run = identical output to clean run; no duplicate ad_ids in ledger.
