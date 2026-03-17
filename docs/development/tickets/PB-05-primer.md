# PB-05 Primer: Update Ad Generator with Nerdy Messaging Rules

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** PB-01 (Brand KB), PB-04 (Brief Expansion) must be complete. See `docs/development/tickets/PB-00-phase-plan.md`.

---

## What Is This Ticket?

PB-05 updates `generate/ad_generator.py` and `generate/brand_voice.py` to enforce Nerdy messaging rules in the generation prompt — "your child" (never "your student"), Meta ad structure (Hook → Pattern interrupt → CTA), persona-specific CTAs, and conditional claim templates.

### Why It Matters

- The generator prompt is where language is actually produced — rules must be embedded here
- Current VALID_CTAS has 5 generic options; personas need specific micro-commitment CTAs
- Meta ad structure (Hook → Pattern interrupt → Micro-commitment CTA) is the proven conversion pattern
- Conditional claims ("200 points in 16 sessions") are more credible than bare promises

---

## What Was Already Done

- `generate/ad_generator.py`: `generate_ad()` uses reference-decompose-recombine, calls Gemini Flash, validates CTA against VALID_CTAS (5 options)
- `generate/brand_voice.py`: 2 voice profiles (parents/students) with tone, emotional_drivers, vocabulary, few-shot examples
- PB-01: brand_knowledge.json has messaging_rules, persona-specific CTAs, offer positioning
- PB-04: ExpandedBrief now includes persona, suggested_hooks, offer_context, messaging_rules

---

## What This Ticket Must Accomplish

### Deliverables Checklist

#### A. Update Generation Prompt (`generate/ad_generator.py`)

- [ ] Add explicit language rules to prompt:
  - "ALWAYS say 'your child' — NEVER 'your student'"
  - "ALWAYS say 'SAT Tutoring' — NEVER 'SAT Prep'"
  - "Use plain parent language, not corporate marketing speak"
  - "Include specific mechanisms (how the digital SAT works, diagnostic process, session structure)"
- [ ] Add Meta ad structure instruction:
  - "Structure: Hook (1 scroll-stopping sentence) → Pattern interrupt explanation (2–3 lines) → Micro-commitment CTA"
- [ ] Inject persona-specific hooks from ExpandedBrief.suggested_hooks as "inspiration patterns"
- [ ] Inject offer context from ExpandedBrief.offer_context for conversion goals
- [ ] Add conditional claim templates when score improvement is mentioned

#### B. Expand VALID_CTAS

- [ ] Add persona-specific CTAs from brand_knowledge.json:
  - "Book Diagnostic"
  - "Talk to an SAT specialist today"
  - "See what score range is realistic in 8–10 weeks"
  - "See how many scholarship dollars your score could unlock"
  - "See what 1-on-1 changes"
  - "Tell us about your child"
  - "Tell us what went wrong"
  - "See how we help students walk into the SAT feeling ready"
  - "Get a tutor who keeps your child accountable"
  - "See what real SAT tutoring looks like"
  - "Let's build the plan that works for this child"
- [ ] CTA validation: accept any CTA from the expanded list, not just the original 5

#### C. Update Brand Voice Profiles (`generate/brand_voice.py`)

- [ ] Add persona-aware voice variants (extend beyond parents/students):
  - `get_voice_for_persona(persona: str) -> VoiceProfile` — returns persona-specific tone and vocabulary
  - Athlete persona: urgent, scheduling-aware, recruiting-timeline language
  - System Optimizer: data-driven, process-oriented, ROI language
  - Neurodivergent: warm, specific, accommodation-aware language
  - Burned Returner: acknowledgment-first, accountability language
- [ ] Update vocabulary guidance with Nerdy-specific prefer/avoid lists
- [ ] Update few-shot examples with supplementary hook examples

#### D. Conditional Claim Templates

- [ ] When the generator mentions score improvement, inject templates:
  - "16 sessions → 200 points"
  - "100 points per month at 2 sessions/week + 20min/day practice"
  - "If your SAT is between 1100–1300, you can gain 200 points in 8 weeks"
- [ ] Instruct: "NEVER claim bare '200 points' without a condition"

#### E. Tests (`tests/test_generation/test_nerdy_generation.py`)

- [ ] TDD first
- [ ] Generated ad text contains "your child" (not "your student")
- [ ] Generated ad avoids "SAT Prep" (uses "SAT Tutoring" or neither)
- [ ] Generated CTA is in expanded VALID_CTAS list
- [ ] Generated ad for conversion includes specific mechanism or conditional claim
- [ ] Persona-specific voice applied (athlete → recruiting language, etc.)
- [ ] Minimum: 6 tests

#### F. Documentation

- [ ] Add PB-05 entry in `docs/DEVLOG.md`

---

## Files to Modify

| File | Action |
|------|--------|
| `generate/ad_generator.py` | Update prompt, expand VALID_CTAS, inject persona/hooks/offer |
| `generate/brand_voice.py` | Add persona-aware voice profiles, update vocabulary |
| `tests/test_generation/test_nerdy_generation.py` | Create — generation rule tests |

---

## Definition of Done

- [ ] Generation prompt enforces Nerdy language rules
- [ ] VALID_CTAS expanded with persona-specific options
- [ ] Meta ad structure (Hook → Pattern interrupt → CTA) in prompt
- [ ] Persona-aware voice profiles available
- [ ] Conditional claim templates injected
- [ ] Tests pass
- [ ] Lint clean
- [ ] DEVLOG updated

---

## Estimated Time: 60–90 minutes
