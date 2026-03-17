# PB-06 Primer: Nerdy-Calibrated Evaluator

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** PB-01 (Brand KB), PB-03 (Compliance Rules) must be complete. See `docs/development/tickets/PB-00-phase-plan.md`.

---

## What Is This Ticket?

PB-06 updates `evaluate/evaluator.py` with Nerdy-specific scoring penalties (corporate jargon, wrong language), bonuses (specificity, persona match), and calibration anchors from the supplementary doc.

### Why It Matters

- The evaluator is the quality gate — if it doesn't penalize "your student" or reward specificity, the pipeline will keep producing generic ads
- Current calibration anchors are generic; supplementary provides real Nerdy-quality examples at each score level
- Persona-aware evaluation catches ads that are technically good but wrong for the target audience

---

## What Was Already Done

- `evaluate/evaluator.py`: 5-dimension CoT evaluator with calibration anchors, Gemini Flash, contrastive rationale
- Existing penalties: "Guaranteed 1500+" → BV capped at 3, competitor disparagement → BV capped at 3
- `generate/brand_voice.py`: `get_voice_for_evaluation(audience)` returns audience-specific rubric block
- PB-03: compliance.py now catches "your student", "SAT Prep", fake urgency, corporate jargon

---

## What This Ticket Must Accomplish

### Deliverables Checklist

#### A. Nerdy Language Penalties (in evaluator prompt)

- [ ] "your student" detected → Brand Voice capped at 4.0
- [ ] "SAT Prep" detected → Brand Voice score -1.0
- [ ] Corporate jargon ("unlock potential", "maximize score", "tailored support") → Clarity score -1.0
- [ ] Fake urgency ("spots filling fast", "limited enrollment") → Brand Voice score -1.5
- [ ] "online tutoring" framing → Brand Voice score -1.0

#### B. Specificity Bonuses (in evaluator prompt)

- [ ] Conditional claim present (score + timeframe/condition) → Value Proposition +0.5
- [ ] Specific mechanism described (digital SAT tools, diagnostic process, session structure) → Value Proposition +0.5
- [ ] Real competitor data used (pricing, results comparison) → Value Proposition +0.5
- [ ] Persona-specific emotional resonance → Emotional Resonance +0.5

#### C. Updated Calibration Anchors

- [ ] Score 9–10 example: "3.8 GPA. 1260 SAT. Something's off." + "Most mid-1200s students are 3–4 fixes away from a 1400+" + "See what score is realistic in 8–10 weeks" — crystal clear hook, specific mechanism, persona-matched CTA
- [ ] Score 7–8 example: Hook with conditional claim ("100 points per month at 2 sessions/week"), plain parent language, specific CTA
- [ ] Score 5–6 example: Generic "Struggling with SAT?" + "unlock your potential" + "Learn More" — vague, corporate, generic CTA
- [ ] Score 3–4 example: "SAT Prep available for your student" + "spots filling fast" + no mechanism — wrong language, fake urgency, no specificity

#### D. Persona-Aware Evaluation

- [ ] When persona is provided in evaluation context, check emotional register match:
  - Athlete persona → should reference recruiting, scholarship, scheduling
  - System Optimizer → should reference process, data, ROI, timeline
  - Neurodivergent → should reference accommodation, learning differences, tutor fit
- [ ] Persona mismatch → Emotional Resonance score -0.5
- [ ] Update `get_voice_for_evaluation()` to accept optional persona parameter

#### E. Tests (`tests/test_evaluation/test_nerdy_evaluator.py`)

- [ ] TDD first
- [ ] Ad with "your student" scores Brand Voice ≤ 4.0
- [ ] Ad with "your child" + specific mechanism scores VP higher than vague equivalent
- [ ] Ad with corporate jargon scores Clarity lower than plain language equivalent
- [ ] Ad with fake urgency scores Brand Voice lower
- [ ] Calibration anchor: score-9 example evaluates ≥ 8.0
- [ ] Calibration anchor: score-3 example evaluates ≤ 4.5
- [ ] Minimum: 6 tests

#### F. Documentation

- [ ] Add PB-06 entry in `docs/DEVLOG.md`

---

## Files to Modify

| File | Action |
|------|--------|
| `evaluate/evaluator.py` | Add penalty/bonus rules, update calibration anchors, add persona context |
| `generate/brand_voice.py` | Update `get_voice_for_evaluation()` with Nerdy rubric + persona support |
| `tests/test_evaluation/test_nerdy_evaluator.py` | Create — Nerdy evaluator tests |

---

## Definition of Done

- [ ] Nerdy language penalties reduce scores for "your student", corporate jargon, fake urgency
- [ ] Specificity bonuses reward conditional claims, mechanisms, competitor data
- [ ] Calibration anchors updated with Nerdy-specific examples
- [ ] Persona-aware evaluation checks emotional register match
- [ ] Tests pass
- [ ] Lint clean
- [ ] DEVLOG updated

---

## Estimated Time: 60–90 minutes
