# P1-12 Primer: Result-Level Cache

**Project:** Ad-Ops-Autopilot  
**Phase:** 1 — Core Pipeline (v1)

## Description

Cache evaluation results keyed by hash(ad_text + evaluator_prompt_version) (R3-Q7). On evaluator recalibration, all cached scores for old prompt version invalidated. Version-based TTL, not time-based.

**Acceptance:** Cache hits on resume; recalibration clears all cached scores; no stale scores after prompt changes.
