# P2-05 Primer: Confidence-Gated Autonomy

**Project:** Ad-Ops-Autopilot  
**Phase:** 2 — Testing & Validation

## Description

Route ads based on evaluator confidence (R2-Q5): >7 autonomous; 5–7 flagged for optional human review; <5 human required. Concentrates human attention on the gray zone where the evaluator is uncertain.

**Acceptance:** Correct routing per confidence level; brand safety trigger (score <4.0 on any dimension) = hard stop.
