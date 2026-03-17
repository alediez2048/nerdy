# PB-14 Primer: Integration Test + Validation Run

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** PB-10 through PB-13 complete. Full persona flow, creative direction, Nerdy messaging, calibrated evaluator.

---

## What Is This Ticket?

PB-14 validates the full PB extension end-to-end: create a session with a specific persona, verify the pipeline produces persona-aware ads with Nerdy-compliant messaging, images reflecting the persona's visual direction, and evaluator scores reflecting Nerdy quality signals.

### Why It Matters

- Integration testing catches issues that unit tests miss (data format mismatches, config not flowing through, prompt injection errors)
- The validation run produces the "before/after" comparison: generic ads vs persona-driven ads
- This is the proof that the PB extension works as intended

---

## What This Ticket Must Accomplish

### Goal

Run a validation session for each persona type and verify the output quality.

### Deliverables

#### A. Integration Tests

- [ ] Test: session with persona=athlete_recruit produces ads mentioning scholarship/recruiting
- [ ] Test: session with persona=suburban_optimizer produces ads with GPA/SAT mismatch angle
- [ ] Test: session with persona=system_optimizer produces data-driven copy and clean imagery
- [ ] Test: session with creative_brief=gap_report produces McKinsey-style visual spec
- [ ] Test: session with copy_on_image=true appends headline to image prompt
- [ ] Test: session with persona=auto produces generic ads (backward compatible)
- [ ] Test: no ads contain "your student" or "SAT Prep" (Nerdy compliance)
- [ ] Test: conversion ads reference real pricing or score improvement data
- [ ] 10+ integration tests

#### B. Validation Run

- [ ] Run 3 sessions: athlete_recruit (5 ads), suburban_optimizer (5 ads), auto (5 ads)
- [ ] Compare: do persona sessions produce visibly different ads?
- [ ] Compare: do persona sessions use persona-specific CTAs?
- [ ] Compare: do images reflect persona visual direction?
- [ ] Document results in DEVLOG

#### C. Quality Comparison

- [ ] Measure: Nerdy compliance rate (% of ads with zero messaging violations)
- [ ] Measure: persona CTA accuracy (% of ads using the persona's preferred CTA)
- [ ] Measure: visual spec differentiation (do different personas produce different image prompts?)

---

## Definition of Done

- [ ] All integration tests pass
- [ ] 3 validation sessions completed with documented results
- [ ] Nerdy compliance rate >90%
- [ ] Different personas produce visibly different ads and images
- [ ] DEVLOG updated with before/after comparison
- [ ] Tests pass, lint clean
