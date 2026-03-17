# PB-13 Primer: Nerdy-Calibrated Evaluator

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** PB-12 (ad generator with Nerdy rules). Evaluator currently scores generically — doesn't know Nerdy-specific quality signals.

---

## What Is This Ticket?

PB-13 calibrates the evaluator to recognize Nerdy-specific quality signals. The evaluator should reward ads that follow Nerdy messaging rules and penalize ads that violate them. Currently a confusing ad that uses "your student" and "SAT Prep" scores the same as one that correctly uses "your child" and "SAT Tutoring."

### Why It Matters

- The evaluator drives the feedback loop — if it doesn't penalize Nerdy violations, the generator keeps producing them
- Specific, conditional claims ("100 pts/month at 2 sessions/week") should score higher on Value Proposition than vague claims ("improve your score")
- Real competitor data ("2.6X more than Princeton Review") should boost scores vs generic differentiation

---

## What This Ticket Must Accomplish

### Goal

Add Nerdy-specific scoring adjustments to the evaluator and update calibration anchors.

### Deliverables

#### A. Evaluator Updates (`evaluate/evaluator.py`)

- [ ] Add Nerdy compliance check to evaluation prompt:
  - Instruct evaluator to check for "your student" (should be "your child") — penalize Brand Voice
  - Check for "SAT Prep" (should be "SAT Tutoring") — penalize Brand Voice
  - Check for fake urgency — penalize Emotional Resonance
  - Check for corporate jargon ("unlock potential", "maximize score") — penalize Brand Voice
- [ ] Add positive signals to evaluation prompt:
  - Conditional claims with specificity → boost Value Proposition
  - Real competitor comparisons → boost Value Proposition
  - Meta ad structure compliance (hook → body → CTA) → boost Clarity
  - Persona-appropriate tone → boost Brand Voice
- [ ] Update calibration anchors with Nerdy-specific examples:
  - 9.0 example: Uses "your child", specific score claim with conditions, persona-matched CTA
  - 3.0 example: Uses "your student", "SAT Prep", "unlock potential", vague promises

#### B. Tests

- [ ] Test ad with "your student" scores lower on Brand Voice than "your child" version
- [ ] Test ad with specific claim ("100 pts/month at 2x/week") scores higher on VP than vague claim
- [ ] Test ad with fake urgency scores lower on Emotional Resonance
- [ ] Test Nerdy-calibrated anchor ads score in expected ranges
- [ ] 8+ tests

---

## Definition of Done

- [ ] Evaluator penalizes Nerdy language violations
- [ ] Evaluator rewards specificity and competitor comparisons
- [ ] Calibration anchors include Nerdy-specific examples
- [ ] Tests pass, lint clean, DEVLOG updated
