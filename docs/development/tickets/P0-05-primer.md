# P0-05 Primer: Reference Ad Collection

**For:** New Cursor Agent session  
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG  
**Date:** March 2026  
**Previous work:** P0-04 (brand knowledge base) should be complete. See `docs/DEVLOG.md`.

---

## What Is This Ticket?

P0-05 collects and labels **reference ads** — both Varsity Tutors ads (from Slack) and competitor ads (from Meta Ad Library). These serve three purposes: calibrating the evaluator (P0-06), seeding the generator with structural patterns (R2-Q1), and establishing golden set test data (P0-07).

### Why It Matters

- **Cold-start calibration** (R1-Q8): The evaluator must be calibrated against real ads before it can be trusted
- **Reference-decompose-recombine** (R2-Q1): The generator needs structural atoms from proven ads
- **Competitive intelligence** (+10 bonus points): Structured pattern extraction from Meta Ad Library
- Without labeled reference data, the evaluator has no taste and the generator has no patterns to learn from

---

## What Was Already Done

- P0-04: Brand knowledge base with verified facts
- Assignment spec references "reference ads provided via Gauntlet/Nerdy Slack channel"
- Competitor list defined: Princeton Review, Kaplan, Khan Academy, Chegg

---

## What This Ticket Must Accomplish

### Goal

Collect 20–30 Varsity Tutors + 20–30 competitor ads. Label 5–10 as "excellent" and 5–10 as "poor." Decompose top ads into structural atoms.

### Deliverables Checklist

#### A. Reference Ad Collection (`data/reference_ads.json`)

- [ ] 20–30 Varsity Tutors ads (from Slack reference material or public sources)
- [ ] 20–30 competitor ads from Meta Ad Library (Princeton Review, Kaplan, Khan Academy, Chegg)
- [ ] Each ad includes: primary_text, headline, description, cta_button, source, brand, audience_guess

#### B. Quality Labels

- [ ] 5–10 ads labeled "excellent" with dimension-level scores (human-assigned)
- [ ] 5–10 ads labeled "poor" with dimension-level scores (human-assigned)
- [ ] Labels include rationale for each dimension score

#### C. Structural Atom Decomposition (`data/pattern_database.json`)

- [ ] Top 10–15 reference ads decomposed into:
  - Hook type (question, stat, story, fear)
  - Body pattern (problem-agitate-solution, testimonial-benefit, stat-context-offer)
  - CTA style (free-trial, sign-up, learn-more)
  - Tone register
  - Audience
- [ ] Stored as queryable pattern records for the generator

**Note:** This pattern database focuses on structural atoms from *reference ads* for the generator (R2-Q1). P0-09 creates a separate competitive pattern database (`data/competitive/patterns.json`) for broader competitive intelligence from Meta Ad Library.

#### D. Documentation

- [ ] Add P0-05 entry in `docs/DEVLOG.md`
- [ ] Document collection methodology and sources

---

## Branch & Merge Workflow

All work is done directly on `develop`. No feature branches.

```bash
git switch develop && git pull
```

---

## Important Context

### Architectural Decisions

| Decision | Reference | Summary |
|----------|-----------|---------|
| Cold-start | R1-Q8 | Calibrate evaluator with labeled competitor ads before generating |
| Competitive intel | R2-Q2 | Structured pattern extraction — queryable patterns, not raw ads |
| Generation | R2-Q1 | Decompose reference ads into structural atoms for recombination |

### Files to Create

| File | Why |
|------|-----|
| `data/reference_ads.json` | Raw reference ad collection with labels |
| `data/pattern_database.json` | Decomposed structural atoms |

### Files You Should READ for Context

| File | Why |
|------|-----|
| `docs/reference/prd.md` (lines 43–61) | What works on Meta, ad anatomy |
| `.claude/skills/adops-generation/references/meta-ad-patterns.md` | Hook types, body patterns, CTA patterns |
| `.cursor/rules/brand-context.mdc` | Competitor list and ad structure |

---

## Definition of Done

- [ ] 40–60 reference ads collected (mix of Varsity Tutors and competitors)
- [ ] 5–10 labeled excellent, 5–10 labeled poor, with per-dimension human scores
- [ ] Top ads decomposed into structural atoms in pattern database
- [ ] DEVLOG updated
- [ ] Committed on `develop`

---

## Estimated Time: 60–90 minutes

---

## After This Ticket: What Comes Next

- **P0-06** (Evaluator cold-start calibration) — uses labeled ads to calibrate the evaluator
- **P0-07** (Golden set regression tests) — uses labeled ads as test data
- **P1-02** (Ad copy generator) — queries pattern database for structural atoms
