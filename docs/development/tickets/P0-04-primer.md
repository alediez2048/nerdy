# P0-04 Primer: Brand Knowledge Base

**For:** New Cursor Agent session  
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG  
**Date:** March 2026  
**Previous work:** P0-01 (scaffolding) must be complete. See `docs/DEVLOG.md`.

---

## What Is This Ticket?

P0-04 creates the **verified brand knowledge base** — a structured JSON file containing only confirmed facts about Varsity Tutors. This file is the single source of truth for the brief expansion engine (P1-01): the LLM can frame and rewrite these facts creatively, but it cannot invent new ones.

### Why It Matters

- **Prevention over detection** (Pillar 2): Grounding constraints prevent hallucinated product claims at the source
- Brief expansion (R3-Q5) explicitly requires "use ONLY verified facts from the knowledge base"
- The compliance filter (R3-Q3) checks generated ads against this file
- Without verified facts, the generator will invent pricing, statistics, and testimonials

---

## What Was Already Done

- P0-01: `data/` directory exists
- Brand context defined in `requirements.md` and `prd.md` (brand voice, audience, competitors)
- `.claude/skills/adops-generation/SKILL.md` specifies grounding constraint pattern
- `.cursor/rules/brand-context.mdc` defines audience profiles and compliance guardrails

---

## What This Ticket Must Accomplish

### Goal

Build a structured, verified-facts-only JSON file that the brief expansion engine can reference without risk of hallucination.

### Deliverables Checklist

#### A. Knowledge Base (`data/brand_knowledge.json`)

- [ ] **Brand identity:** Name, parent company, brand voice descriptors, positioning
- [ ] **Products:** SAT prep tutoring (verified offerings only — 1-on-1 tutoring, online platform)
- [ ] **Audience segments:** Parent profile, student profile (from assignment spec)
- [ ] **Proof points:** Only statistics/claims that appear in the assignment spec or reference ads
  - Example: "10,000+ students" (if from reference ads)
  - Do NOT invent: pricing, specific score guarantees, testimonials
- [ ] **Competitors:** Princeton Review, Kaplan, Khan Academy, Chegg (names only — no claims about them)
- [ ] **CTAs by funnel stage:** Awareness CTAs, conversion CTAs (from assignment spec)
- [ ] **Compliance boundaries:** What can and cannot be claimed
- [ ] **Source citations:** Every fact tagged with its source (`assignment_spec`, `reference_ad`, `public_website`)

#### B. Schema

```json
{
  "brand": {
    "name": "Varsity Tutors",
    "parent": "Nerdy",
    "voice": ["empowering", "knowledgeable", "approachable", "results-focused"],
    "positioning": "Lead with outcomes, not features"
  },
  "products": {
    "sat_prep": {
      "type": "1-on-1 tutoring",
      "format": "online",
      "verified_claims": [
        {"claim": "description", "source": "assignment_spec|reference_ad|public_website"}
      ]
    }
  },
  "audiences": {
    "parent": {
      "pain_points": [...],
      "emotional_drivers": [...],
      "tone_register": "authoritative, reassuring, outcome-focused"
    },
    "student": {
      "pain_points": [...],
      "emotional_drivers": [...],
      "tone_register": "relatable, motivating, peer-like"
    }
  },
  "proof_points": [],
  "competitors": ["Princeton Review", "Kaplan", "Khan Academy", "Chegg"],
  "ctas": {
    "awareness": [...],
    "conversion": [...]
  },
  "compliance": {
    "never_claim": [...],
    "always_include": [...]
  }
}
```

#### C. Validation Script (optional but recommended)

- [ ] Simple script or test that validates the JSON schema
- [ ] Checks every claim has a `source` field
- [ ] Checks no claim uses words from the compliance blacklist

#### D. Documentation

- [ ] Add P0-04 entry in `docs/DEVLOG.md`
- [ ] Document how to add new verified facts (process for future updates)

---

## Branch & Merge Workflow

```bash
git switch main && git pull
git switch -c feature/P0-04-brand-knowledge-base
```

---

## Important Context

### Architectural Decisions

| Decision | Reference | Summary |
|----------|-----------|---------|
| Brief expansion | R3-Q5 | LLM expands using ONLY verified facts; flags unverified claims |
| Compliance | R3-Q3 | Three-layer filter checks against this knowledge base |

### Files to Create

| File | Why |
|------|-----|
| `data/brand_knowledge.json` | Verified facts for grounded generation |

### Files You Should READ for Context

| File | Why |
|------|-----|
| `requirements.md` (lines 103–117) | Brand context from assignment |
| `prd.md` (lines 41–43) | Brand voice and audience |
| `.cursor/rules/brand-context.mdc` | Audience profiles and compliance guardrails |
| `.claude/skills/adops-generation/SKILL.md` | Grounding constraint pattern |

---

## Definition of Done

- [ ] `data/brand_knowledge.json` created with verified facts only
- [ ] Every fact has a source citation
- [ ] Covers: brand identity, products, audiences, proof points, competitors, CTAs, compliance
- [ ] No invented statistics, pricing, or testimonials
- [ ] DEVLOG updated
- [ ] Feature branch pushed

---

## Estimated Time: 30–45 minutes

---

## After This Ticket: What Comes Next

- **P0-05** (Reference ad collection) — supplements the knowledge base with real ad examples
- **P1-01** (Brief expansion engine) — consumes this file directly
- **P2-06** (Tiered compliance filter) — validates ads against this file
