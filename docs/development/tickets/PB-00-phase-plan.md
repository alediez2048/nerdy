# Phase PB: Nerdy Content Quality Integration

**Objective:** Integrate the Nerdy team's supplementary guidance (personas, language rules, hooks, competitive data, offer positioning) into the pipeline to produce ads that sound like a Nerdy marketer wrote them — not a generic AI.

**Source:** `C4_Automatic_Ad_Generator_Supplementary.md`

**Builds on:** PA (application layer complete), P0–P5 (full pipeline operational)

**North Star:** Generated ads pass the "would a Nerdy marketer approve this?" test — correct language, persona-aware hooks, specific mechanisms, conditional claims, real competitive positioning.

---

## What Changes and Why

### Current State (what we have)

| Area | Current | Problem |
|------|---------|---------|
| Audiences | 2 generic: "parents", "students" | Real parents are 7+ distinct personas with different psychology, urgency, hooks |
| Language | Generic brand voice: "empowering, knowledgeable, approachable" | Uses "your student" (wrong), "SAT Prep" (wrong), corporate jargon ("unlock potential") |
| Hooks | Generated from competitive patterns | No persona-specific hook library; misses proven hooks the Nerdy team tested |
| Compliance | 18 regex rules, no Nerdy-specific language checks | Doesn't catch "your student", "SAT Prep", fake urgency, vague score claims |
| Competitive data | 4 competitors, pattern-level only | Missing real pricing ($252/hr Princeton Review), comparison claims (10X, 2.6X), offer positioning |
| Evaluator | Generic rubric with calibration anchors | Doesn't penalize corporate language or reward persona-specific emotional resonance |
| CTA library | 5 generic CTAs | Missing persona-specific micro-commitment CTAs ("Book Diagnostic", "See what score is realistic") |
| Offer context | None | Generator doesn't know about membership model, pricing, results claims |

### Target State (what PB delivers)

| Area | After PB |
|------|----------|
| Audiences | 7 personas with psychology, funnel position, hook style, CTA preference |
| Language | "your child" always, "SAT Tutoring", conditional claims, specific mechanisms |
| Hooks | 80+ proven hooks organized by persona, injected into brief expansion |
| Compliance | Nerdy do's/don'ts as hard rules + warnings |
| Competitive data | Real pricing, result comparisons, offer positioning embedded in brand KB |
| Evaluator | Penalizes corporate language, rewards specificity, persona-aware rubric |
| CTAs | Persona-specific micro-commitment CTAs |
| Offer context | Membership model, pricing tiers, results claims available to generator |

---

## Tickets (9 tickets)

### PB-01: Ingest Supplementary into Brand Knowledge Base
**What:** Update `data/brand_knowledge.json` with all new content from the supplementary doc.
**Deliverables:**
- 7 persona profiles (athlete_recruit, suburban_optimizer, immigrant_navigator, cultural_investor, system_optimizer, neurodivergent_advocate, burned_returner) with psychology, funnel_position, trigger, conversion_likelihood
- Language rules: do's list, don'ts list (from "SAT Messaging Guidance")
- Updated competitor data with real pricing (Princeton Review $199–$252/hr, Kaplan $1500–$2500, Khan Academy free, etc.)
- Offer positioning: membership model, pricing tiers, results claims (10X self-study, 2.6X group, ~100pts/month)
- Updated CTA library: persona-specific CTAs (not just generic "Learn More")
- Updated compliance.never_claim with supplementary don'ts
- Tests: validate JSON schema, all personas present, all language rules loaded
**Depends on:** Nothing
**Estimated time:** 45–60 min

### PB-02: Persona-Specific Hook Library
**What:** Create a structured hook library (`data/hooks_library.json`) with all 80+ hooks from the supplementary, organized by persona and tagged with psychology/CTA.
**Deliverables:**
- `data/hooks_library.json`: array of hooks, each with `persona`, `hook_text`, `psychology`, `cta_text`, `cta_style`, `funnel_position`
- 12 hook categories: athlete, suburban_optimizer, scholarship, khan_failures, online_skeptic, urgency, immigrant, neurodivergent, test_anxiety, accountability, school_failed, education_investor, parent_relationship, sibling, burned_returner
- `generate/hooks.py`: `get_hooks_for_persona(persona, n=3)` — returns top hooks for a persona, seed-based selection for diversity
- Query function for brief expansion to inject relevant hooks
- Tests: all hooks loaded, persona filtering works, seed diversity verified
**Depends on:** PB-01
**Estimated time:** 45–60 min

### PB-03: Nerdy Language Compliance Rules
**What:** Update `generate/compliance.py` with Nerdy-specific language do's/don'ts as hard rules and warnings.
**Deliverables:**
- New critical violations: "your student" (must be "your child"), "SAT Prep" (must be "SAT Tutoring"), score improvement guarantees, "online tutoring" framing
- New warning violations: "unlock potential", "maximize score", "tailored support", "custom strategies", corporate jargon patterns
- New critical violations: fake urgency ("spots filling fast", "limited enrollment", "secure their spot", "don't miss out")
- Positive validation: check that conditional claims have specificity (e.g., "200 points" has a condition like "in 16 sessions")
- Update existing competitor name check — supplementary says comparing to competitors IS allowed (with real data), so adjust from "critical" to "warning" or remove
- Tests: each new rule has a test case (violation detected, clean copy passes)
**Depends on:** PB-01
**Estimated time:** 45–60 min

### PB-04: Persona-Aware Brief Expansion
**What:** Update `generate/brief_expansion.py` to inject persona-specific context when expanding briefs.
**Deliverables:**
- Accept optional `persona` field in brief input (default: auto-detect from audience)
- Load persona profile from brand_knowledge.json
- Inject persona psychology, trigger, funnel position into expansion prompt
- Inject 2–3 relevant hooks from hook library (PB-02) as "proven hook patterns for this persona"
- Inject persona-specific CTA guidance
- Inject offer positioning context (membership model, pricing comparison) when relevant
- Update ExpandedBrief dataclass: add `persona`, `suggested_hooks`, `offer_context` fields
- Tests: persona context appears in expanded brief, hooks injected, offer context present for conversion goals
**Depends on:** PB-01, PB-02
**Estimated time:** 60–90 min

### PB-05: Update Ad Generator with Nerdy Messaging Rules
**What:** Update `generate/ad_generator.py` and `generate/brand_voice.py` with Nerdy-specific generation rules.
**Deliverables:**
- Update generation prompt to enforce: "your child" (never "your student"), "SAT Tutoring" (never "SAT Prep"), Meta ad structure (Hook → Pattern interrupt → Micro-commitment CTA)
- Add persona-specific voice profiles to `brand_voice.py` (extend beyond just parents/students)
- Update VALID_CTAS with persona-specific CTAs: "Book Diagnostic", "See what score is realistic in 8–10 weeks", "Talk to an SAT specialist today", "Tell us about your child"
- Inject offer positioning into generation context when campaign_goal is "conversion"
- Add conditional claim templates: "16 sessions → 200 points", "100pts/month at 2x/week + 20min/day practice"
- Update structural variation rules to prefer specific mechanisms over vague promises
- Tests: generated ads use "your child", include specific mechanisms, CTAs match persona
**Depends on:** PB-01, PB-04
**Estimated time:** 60–90 min

### PB-06: Nerdy-Calibrated Evaluator
**What:** Update `evaluate/evaluator.py` with Nerdy-specific scoring rubric and penalty rules.
**Deliverables:**
- Add Nerdy language penalties: "your student" → Brand Voice capped at 4, "SAT Prep" → Brand Voice -1, corporate jargon → Clarity -1
- Add specificity bonuses: conditional claims (+0.5 VP), specific mechanisms (+0.5 VP), real competitor data used (+0.5 VP)
- Update calibration anchors with supplementary examples:
  - Score 9: "3.8 GPA. 1260 SAT. Something's off." + specific mechanism + persona CTA
  - Score 5: Generic "Struggling with SAT?" + "unlock potential" + "Learn More"
  - Score 3: "SAT Prep available" + "your student" + "spots filling fast"
- Add persona-awareness to evaluation: does the ad's emotional register match the target persona's psychology?
- Update `get_voice_for_evaluation()` in brand_voice.py to include Nerdy-specific rubric
- Tests: "your student" ads score lower, specific mechanism ads score higher, persona-matched ads score higher
**Depends on:** PB-01, PB-03
**Estimated time:** 60–90 min

### PB-07: Persona Selector in Session Config + Dashboard Updates
**What:** Add persona selection to the session configuration and minor dashboard updates.
**Deliverables:**
- Backend: Add `persona` field to SessionConfig schema (optional enum with 7 personas + "auto")
- Backend: Pass persona through to brief expansion in pipeline task
- Frontend: Add persona selector to NewSessionForm (dropdown with persona name + one-line description)
- Frontend: Add persona badge to SessionCard and SessionDetail header
- Frontend: Add persona filter to AdLibrary tab
- Frontend: Add persona breakdown to Overview tab (pass rate per persona if multi-persona run)
- Tests: persona flows through config → expansion → generation → dashboard
**Depends on:** PB-04, PB-05
**Estimated time:** 60–90 min

### PB-08: Integration Test Suite — Nerdy Content Quality
**What:** Comprehensive test suite verifying the entire PB integration works end-to-end — from brand KB ingestion through evaluation and compliance.
**Deliverables:**

#### A. Brand Knowledge Tests (`tests/test_pb/test_brand_kb.py`)
- [ ] All 7 personas loaded with required fields (psychology, funnel_position, trigger, conversion_likelihood)
- [ ] Language do's list contains "your child", "SAT Tutoring"
- [ ] Language don'ts list contains "your student", "SAT Prep"
- [ ] Competitor data includes real pricing for Princeton Review, Kaplan, Khan Academy
- [ ] Offer positioning includes membership model, pricing tiers, results claims
- [ ] CTA library has persona-specific CTAs (not just generic "Learn More")
- [ ] Minimum: 7 tests

#### B. Hook Library Tests (`tests/test_pb/test_hooks.py`)
- [ ] All 80+ hooks loaded from hooks_library.json
- [ ] Each hook has required fields: persona, hook_text, psychology, cta_text
- [ ] `get_hooks_for_persona()` returns hooks only for requested persona
- [ ] `get_hooks_for_persona()` with seed produces deterministic but diverse selection
- [ ] No duplicate hook texts across the library
- [ ] Every persona has at least 3 hooks
- [ ] Minimum: 6 tests

#### C. Compliance Rule Tests (`tests/test_pb/test_nerdy_compliance.py`)
- [ ] "your student" detected as critical violation
- [ ] "SAT Prep" detected as critical violation
- [ ] "spots filling fast" detected as critical (fake urgency)
- [ ] "limited enrollment" detected as critical (fake urgency)
- [ ] "unlock potential" detected as warning (corporate jargon)
- [ ] "maximize score potential" detected as warning
- [ ] "your child" passes clean (no violation)
- [ ] "SAT Tutoring" passes clean
- [ ] Clean ad copy with Nerdy-approved language passes all checks
- [ ] Ad with competitor comparison using real data passes (not a violation)
- [ ] Score guarantee ("guaranteed 1500+") still detected as critical
- [ ] Minimum: 11 tests

#### D. Brief Expansion Integration Tests (`tests/test_pb/test_persona_expansion.py`)
- [ ] Expanding brief with `persona="athlete_recruit"` injects athlete psychology into expanded brief
- [ ] Expanded brief contains `persona` field matching input
- [ ] Expanded brief contains `suggested_hooks` from hook library
- [ ] Expanded brief contains `offer_context` for conversion campaigns
- [ ] Expanding with `persona="auto"` selects persona based on audience
- [ ] Expanded brief constraints include Nerdy-specific language rules
- [ ] Minimum: 6 tests

#### E. Ad Generator Integration Tests (`tests/test_pb/test_nerdy_generation.py`)
- [ ] Generated ad uses "your child" (never "your student") — scan primary_text + headline + description
- [ ] Generated ad uses "SAT Tutoring" or avoids "SAT Prep"
- [ ] Generated CTA matches persona-specific options (not just generic "Learn More")
- [ ] Generated ad follows Meta structure: hook line + pattern interrupt + CTA
- [ ] Generated ad for conversion goal includes specific mechanism or conditional claim
- [ ] Generated ad for athlete persona references recruiting/scholarship context
- [ ] Minimum: 6 tests

#### F. Evaluator Calibration Tests (`tests/test_pb/test_nerdy_evaluator.py`)
- [ ] Ad with "your student" scores lower on Brand Voice than identical ad with "your child"
- [ ] Ad with specific mechanism ("16 sessions → 200 points") scores higher on Value Proposition than vague ("raise your score")
- [ ] Ad with corporate jargon ("unlock potential") scores lower on Clarity than plain language
- [ ] Ad with fake urgency ("spots filling fast") scores lower on Brand Voice
- [ ] Ad matching target persona psychology scores higher on Emotional Resonance
- [ ] Nerdy calibration anchor ads score within expected ranges (9-example ≥ 8.0, 5-example 4.5–6.5, 3-example ≤ 4.5)
- [ ] Minimum: 6 tests

#### G. End-to-End Pipeline Test (`tests/test_pb/test_pb_e2e.py`)
- [ ] Full pipeline: brief (with persona) → expand → generate → evaluate → compliance check
- [ ] Pipeline output passes all Nerdy compliance rules (0 critical violations)
- [ ] Pipeline output scores ≥ 7.0 on evaluator for at least 1 of 3 generated ads
- [ ] Pipeline output contains persona metadata in ledger events
- [ ] Pipeline output includes hook attribution (which hook was used)
- [ ] Minimum: 5 tests

#### H. Dashboard Data Tests (`tests/test_pb/test_persona_dashboard.py`)
- [ ] SessionConfig accepts persona field
- [ ] Dashboard summary endpoint includes persona in response when set
- [ ] Ad library endpoint returns ads with persona tags
- [ ] Persona filter on ad library works correctly
- [ ] Minimum: 4 tests

**Total minimum tests:** 51 across 8 test files
**Depends on:** PB-01 through PB-07
**Estimated time:** 90–120 min

### PB-09: Validation Run + Quality Comparison
**What:** Run the pipeline with the new Nerdy content, compare output quality to pre-PB baseline.
**Deliverables:**
- Generate 3 ads per persona (21 total) using the updated pipeline
- Evaluate all 21 ads with the updated evaluator
- Run PB-08 test suite — all 51+ tests must pass
- Compare scores to baseline (pre-PB ads from existing ledger)
- Document: which personas produce the best ads, which language rules triggered, which hooks were most effective
- Add PB results section to DEVLOG
- Update dashboard_data.json with PB output
- Fix any issues discovered during the run
**Depends on:** PB-01 through PB-08
**Estimated time:** 30–45 min

---

## Execution Order

```
PB-01 (Brand KB)
  ├── PB-02 (Hook Library)        ── can run in parallel ──  PB-03 (Compliance Rules)
  │       │                                                        │
  │       └──── PB-04 (Brief Expansion) ────────────── PB-06 (Evaluator)
  │                    │
  │                    └──── PB-05 (Ad Generator)
  │                              │
  └──────────────────── PB-07 (Persona Selector + Dashboard)
                                 │
                          PB-08 (Integration Test Suite — 51+ tests)
                                 │
                          PB-09 (Validation Run)
```

**Critical path:** PB-01 → PB-02 + PB-03 → PB-04 → PB-05 → PB-07 → PB-08 → PB-09

---

## What Does NOT Change

- Pipeline architecture (expand → generate → evaluate → route → publish)
- 5 quality dimensions (clarity, value_proposition, cta, brand_voice, emotional_resonance)
- 7.0 publish threshold + quality ratchet
- Dashboard 7-tab structure
- Pareto selection, SPC monitoring, brief mutation
- Session CRUD, auth, sharing, curation
- Docker deployment

---

## Success Criteria

1. Generated ads use "your child" (never "your student") — 100% compliance
2. Generated ads use "SAT Tutoring" (never "SAT Prep") — 100% compliance
3. No fake urgency in generated ads ("spots filling fast", etc.) — 0 violations
4. Persona-specific hooks appear in generated ads — at least 1 proven hook per ad
5. Conditional claims have specificity ("200 points in 16 sessions") — no bare "200 points"
6. Average evaluator score for persona-matched ads > 7.5 (vs. ~7.2 baseline)
7. Compliance check catches all Nerdy don'ts — 100% detection rate
8. **PB-08 integration test suite: 51+ tests all passing**
9. **PB-09 validation run: 21 ads generated, evaluated, and documented**
