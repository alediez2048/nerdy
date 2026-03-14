# P1-06 Primer: Tiered Model Routing

**Project:** Ad-Ops-Autopilot  
**Phase:** 1 — Core Pipeline (v1)

## Description

Triage logic (R1-Q4): ads scoring <5.5 discarded without expensive re-evaluation; ads >7.0 pass directly; ads in 5.5–7.0 "improvable" range escalate to Gemini Pro. Concentrates expensive tokens on borderline ads.

**Acceptance:** Token spend concentrated on improvable range; cheap model for triage, expensive for regeneration.
