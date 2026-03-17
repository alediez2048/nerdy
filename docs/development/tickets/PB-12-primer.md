# PB-12 Primer: Ad Generator with Nerdy Messaging Rules

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** PB-10 (persona flow), PB-11 (creative direction fields). brand_knowledge.json has messaging_rules (dos/donts), persona-specific CTAs, offer details, meta_ad_structure.

---

## What Is This Ticket?

PB-12 updates the ad copy generator to use Nerdy's real messaging rules, persona-specific CTAs, and offer context. Currently the generator produces generic SAT prep copy. After this ticket, it produces copy that follows Nerdy's actual guidelines: "your child" not "student", "SAT Tutoring" not "Prep", specific conditional claims, persona-matched CTAs.

### Why It Matters

- Current ads violate Nerdy's messaging rules (use "student" instead of "your child", use "SAT Prep" instead of "SAT Tutoring", use corporate jargon like "unlock potential")
- Persona-specific CTAs exist (11+ options) but only 5 generic CTAs are used
- Offer context ($639/mo, 100pts/month, 2.6X competitor comparison) is never referenced in ad copy
- The meta_ad_structure (Hook → Pattern interrupt → Micro-commitment CTA) isn't enforced

---

## What This Ticket Must Accomplish

### Goal

Update the ad generator prompt and CTA selection to follow Nerdy messaging rules, use persona-specific CTAs, and reference real offer data.

### Deliverables

#### A. Ad Generator (`generate/ad_generator.py`)

- [ ] Load messaging_rules from brand_knowledge.json
- [ ] Inject dos/donts into generation prompt as explicit constraints:
  - DO: Use "your child", "SAT Tutoring", specific score claims with conditions, competitor comparisons
  - DON'T: Use "your student", "SAT Prep", "unlock potential", fake urgency, score guarantees
- [ ] Expand VALID_CTAS with all persona-specific CTAs from brand_knowledge.json (11+ options)
- [ ] When persona is set, prefer persona's preferred_cta
- [ ] When campaign_goal is "conversion", inject offer context (pricing, score improvement, what's included)
- [ ] Use meta_ad_structure format: Hook (1 sentence) → Short pattern interrupt (2-3 lines) → Micro-commitment CTA

#### B. Compliance Pre-Check

- [ ] Before returning generated ad, scan for critical violations:
  - "your student" → reject, regenerate
  - "SAT prep" (lowercase) → reject, regenerate
  - Fake urgency phrases → reject, regenerate
- [ ] Log compliance violations to ledger

#### C. Tests

- [ ] Test generated ads use "your child" not "student"
- [ ] Test generated ads use "SAT Tutoring" not "SAT Prep"
- [ ] Test persona-specific CTA selected when persona is set
- [ ] Test offer context appears in conversion ads
- [ ] Test meta_ad_structure format (hook → body → CTA)
- [ ] Test compliance rejection on violations
- [ ] 8+ tests

---

## Definition of Done

- [ ] Generated ads follow Nerdy messaging dos/donts
- [ ] Persona-specific CTAs used when persona is set
- [ ] Conversion ads reference real offer data
- [ ] Critical violations caught before publishing
- [ ] Tests pass, lint clean, DEVLOG updated
