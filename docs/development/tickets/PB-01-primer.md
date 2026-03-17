# PB-01 Primer: Ingest Supplementary into Brand Knowledge Base

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** P0–P5 + PA complete. See `docs/development/tickets/PB-00-phase-plan.md`.

---

## What Is This Ticket?

PB-01 updates `data/brand_knowledge.json` with all content from the Nerdy supplementary guidance: 7 high-value personas, SAT messaging do's/don'ts, real competitor pricing, offer positioning, and persona-specific CTAs.

### Why It Matters

- The current brand KB has 2 generic audiences (parents/students) with thin profiles
- The supplementary doc provides 7 rich personas with distinct psychology, funnel position, and conversion patterns
- Real competitor pricing and results claims enable specific, credible ad copy
- Every downstream PB ticket depends on this data being structured and accessible

---

## What Was Already Done

- `data/brand_knowledge.json` exists with: brand voice, 2 audience profiles (parent/student), empty proof_points, 4 competitors (names only), generic CTAs, basic compliance rules
- `generate/brief_expansion.py` loads this file via `_gather_brand_facts_for_brief()`
- `generate/brand_voice.py` uses audience profiles for tone/vocabulary guidance
- `generate/compliance.py` references `compliance.never_claim` rules

---

## What This Ticket Must Accomplish

### Goal

Extend brand_knowledge.json with all supplementary content while preserving backward compatibility — existing code that loads the file must not break.

### Deliverables Checklist

#### A. Persona Profiles (`personas` key)

- [ ] Add `personas` object with 7 entries:

| Persona Key | Who | Funnel Position | Conversion |
|-------------|-----|-----------------|------------|
| `athlete_recruit` | Mother of 11th-grade student athlete | Late funnel, urgency-driven | Very high |
| `suburban_optimizer` | Upper-middle-class suburban mother, 11th grader | Mid-funnel, comparison shopping | Strong |
| `immigrant_navigator` | First/second-gen immigrant family | Early to mid-funnel | High when decision-maker engaged |
| `cultural_investor` | Dual-income STEM professionals, high father involvement | Mid-funnel, information-driven | High LTV, slow conversion |
| `system_optimizer` | Corporate father, tech-centric, 75%+ father calling | Late funnel, execution-focused | High when process is smooth |
| `neurodivergent_advocate` | Mother of student with ADHD/autism/dyslexia/etc. | Mid-funnel, evaluating fit | High with warmth + specificity |
| `burned_returner` | Mother after negative prior tutoring experience | Late funnel, conditional | Moderate, trust-dependent |

- [ ] Each persona has fields: `description`, `psychology`, `trigger`, `funnel_position`, `conversion_likelihood`, `key_needs`, `preferred_cta`

#### B. SAT Messaging Rules (`messaging_rules` key)

- [ ] `dos`: list of approved language patterns
  - "your child" (not "your student")
  - "SAT Tutoring" (not "SAT Prep")
  - Use avg/typical score gains
  - "100pts/mth" with conditions (2x/week, 1 practice test, 20min/day)
  - Mention SAT points → scholarship dollar value
  - Compare to competitors with real data
  - Compare results: 10X self-study, 2.6X group/local
  - Compare value: Princeton Review $199–$252/hr for 1:1, VT $349/mth
  - Digital SAT advantage: 60% of math via built-in tools

- [ ] `donts`: list of prohibited patterns
  - "your student"
  - "SAT Prep"
  - Score improvement guarantees
  - Vague score claims without specificity
  - Claiming to help get scholarships directly
  - Marketing as "online tutoring"

#### C. Competitor Data (`competitors_detailed` key)

- [ ] Real pricing for each competitor:
  - Self-study (Khan Academy, apps): $0–$99/mo
  - Self-paced courses: $599–$999
  - Princeton Review/Kaplan group: $1,500–$2,500 + $199–$252/hr for 1:1
  - Local tutors (Sylvan, Kumon, Mathnasium): $80–$200/hr
  - Varsity Tutors: $349–$1,099/mo

- [ ] Results comparison claims:
  - 10X score improvement vs self-study
  - 2.6X score improvement vs group/local/brand-name

#### D. Offer Positioning (`offer` key)

- [ ] Membership model description
- [ ] Recommended starting point: 2 sessions/week at $639/month
- [ ] What's included: 1:1 sessions, diagnostics, study plan, practice tests, progress reports, tutor matching
- [ ] Score improvement expectation: ~100 points/month
- [ ] Super score strategy reference

#### E. Updated CTA Library (`ctas` key — extend existing)

- [ ] Persona-specific CTAs:
  - Athlete: "Talk to an SAT specialist today. We'll call you in 60 seconds."
  - Suburban optimizer: "See what score range is realistic in 8–10 weeks."
  - Scholarship: "See how many scholarship dollars your score could unlock."
  - Khan failures: "See what 1-on-1 changes."
  - Immigrant: "Talk to an SAT specialist who will walk you through it step by step."
  - Neurodivergent: "Tell us about your child. We'll match them with a tutor who understands how they learn."
  - Burned returner: "Tell us what went wrong. We'll show you what's different."

#### F. Updated Compliance Rules (`compliance` key — extend existing)

- [ ] Add supplementary don'ts to `never_claim`
- [ ] Update competitor reference rule: comparing IS allowed with real data (remove "competitor disparagement by name" — replace with "competitor disparagement without factual basis")

#### G. Creative Brief Template (`creative_briefs` key)

- [ ] "The Gap Report" template for System Optimizer persona: dashboard-style layout, INPUT/OUTPUT table, no lifestyle imagery, McKinsey-like design direction

#### H. Tests (`tests/test_data/test_brand_kb_pb.py`)

- [ ] TDD first
- [ ] All 7 personas loaded with required fields
- [ ] `messaging_rules.dos` contains "your child", "SAT Tutoring"
- [ ] `messaging_rules.donts` contains "your student", "SAT Prep"
- [ ] `competitors_detailed` has pricing for Princeton Review, Kaplan, Khan Academy
- [ ] `offer` has membership model and pricing
- [ ] CTA library has persona-specific entries
- [ ] Backward compatibility: existing `audiences`, `brand`, `compliance` keys still present
- [ ] Minimum: 8 tests

#### I. Documentation

- [ ] Add PB-01 entry in `docs/DEVLOG.md`

---

## Important Context

### Source Document

`/Users/jad/Downloads/C4_Automatic_Ad_Generator_Supplementary.md` — sections:
- "High Value Personas" (lines 126–224)
- "SAT Messaging Guidance — Do's & Don'ts" (lines 93–123)
- "Cold Audience Hooks by Persona" (lines 226–467)
- "Varsity Tutors SAT — Offer Positioning & Messaging" (lines 492–672)
- "Creative Brief — Static Ad" (lines 43–89)

### Files to Modify

| File | Action |
|------|--------|
| `data/brand_knowledge.json` | Extend with personas, messaging rules, competitor data, offer, CTAs |
| `tests/test_data/test_brand_kb_pb.py` | Create — validation tests |

### Files You Should READ for Context

| File | Why |
|------|-----|
| `data/brand_knowledge.json` | Current structure to extend |
| `generate/brief_expansion.py` | Loads brand KB — must stay compatible |
| `generate/brand_voice.py` | Uses audience profiles — must stay compatible |
| `generate/compliance.py` | References compliance rules — must stay compatible |
| `/Users/jad/Downloads/C4_Automatic_Ad_Generator_Supplementary.md` | Source content |

---

## Definition of Done

- [ ] brand_knowledge.json has all 7 personas with full profiles
- [ ] Messaging do's/don'ts structured and accessible
- [ ] Real competitor pricing and results claims included
- [ ] Offer positioning with membership model
- [ ] Persona-specific CTAs in CTA library
- [ ] Backward compatible — existing code doesn't break
- [ ] Tests pass
- [ ] Lint clean
- [ ] DEVLOG updated

---

## Estimated Time: 45–60 minutes

---

## After This Ticket: What Comes Next

**PB-02 (Hook Library)** and **PB-03 (Compliance Rules)** can start in parallel — both depend only on PB-01.
