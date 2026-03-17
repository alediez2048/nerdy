# PB-03 Primer: Nerdy Language Compliance Rules

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** PB-01 (Brand KB) must be complete. See `docs/development/tickets/PB-00-phase-plan.md`.

---

## What Is This Ticket?

PB-03 updates `generate/compliance.py` with Nerdy-specific language rules from the supplementary — "your student" → critical violation, "SAT Prep" → critical, fake urgency → critical, corporate jargon → warning. Also adjusts the competitor reference rule since the supplementary explicitly encourages competitor comparisons with real data.

### Why It Matters

- **Prevention Over Detection Over Correction** (Pillar 2): Catch bad language at the cheapest layer (regex) before it reaches the evaluator
- The supplementary doc has very specific do's/don'ts that are non-negotiable for the Nerdy brand
- Current compliance.py has 18 patterns but misses all Nerdy-specific language rules
- Competitor comparisons are now ALLOWED (with real data) — the current "critical" flag on competitor names needs adjustment

---

## What Was Already Done

- `generate/compliance.py` exists with:
  - `ComplianceViolation` and `ComplianceResult` dataclasses
  - `_COMPLIANCE_PATTERNS`: 18 regex patterns (guaranteed outcomes, absolute promises, unverified pricing, competitor names, fear language)
  - `check_compliance(text)` → scans text against all patterns
  - `check_evaluator_compliance(scores)` → Layer 2 brand safety floor (4.0)
  - Competitor names (Princeton Review, Kaplan, Khan Academy, Chegg, Sylvan) flagged as "critical"
- PB-01: brand_knowledge.json now has `messaging_rules.dos` and `messaging_rules.donts`

---

## What This Ticket Must Accomplish

### Goal

Add all Nerdy-specific language rules to the compliance filter and adjust the competitor reference rule.

### Deliverables Checklist

#### A. New Critical Violations (must block publication)

- [ ] `nerdy_wrong_address`: `\byour\s+student\b` → critical ("your child" required)
- [ ] `nerdy_wrong_product`: `\bSAT\s+[Pp]rep\b` → critical ("SAT Tutoring" required)
- [ ] `fake_urgency_spots`: `\bspots?\s+filling\s+fast\b` → critical
- [ ] `fake_urgency_limited`: `\blimited\s+enrollment\b` → critical
- [ ] `fake_urgency_secure`: `\bsecure\s+(their|your|a)\s+spot\b` → critical
- [ ] `fake_urgency_miss`: `\bdon'?t\s+miss\s+out\b` → critical
- [ ] `online_tutoring_frame`: `\bonline\s+tutoring\b` → critical (parents dismiss this framing)
- [ ] `score_guarantee_specific`: `\bguaranteed?\s+\d{3,4}\b` → critical (e.g., "guaranteed 1500")

#### B. New Warning Violations (flag but don't block)

- [ ] `corporate_jargon_unlock`: `\bunlock\s+(their\s+)?potential\b` → warning
- [ ] `corporate_jargon_maximize`: `\bmaximize\s+score\b` → warning
- [ ] `corporate_jargon_tailored`: `\btailored\s+support\b` → warning
- [ ] `corporate_jargon_custom`: `\bcustom\s+strategies\b` → warning
- [ ] `corporate_jargon_growth`: `\bgrowth\s+areas\b` → warning
- [ ] `corporate_jargon_concrete`: `\bconcrete\s+score\s+gains\b` → warning
- [ ] `corporate_jargon_dream`: `\bdream\s+college\s+within\s+reach\b` → warning
- [ ] `vague_claim`: `\bpersonalized\b` without specificity → warning (too vague alone)

#### C. Adjust Competitor Reference Rule

- [ ] Change competitor name patterns from "critical" to "info" (informational, not a violation)
- [ ] Add new rule: `competitor_disparagement` → critical — only triggers when competitor name + negative language without factual data (e.g., "Kaplan is terrible" vs. "Kaplan charges $252/hr for 1:1, we charge $349/month")
- [ ] Rationale: supplementary explicitly says "Compare us to competitors" with real data

#### D. Positive Validation Helper (optional but valuable)

- [ ] `check_nerdy_positives(text) -> list[str]` — returns list of approved patterns found:
  - Contains "your child" ✓
  - Contains "SAT Tutoring" ✓
  - Contains conditional claim (score + timeframe) ✓
  - Contains specific mechanism ✓
- [ ] This is informational, not blocking — used by evaluator and dashboard

#### E. Update `check_compliance()` Behavior

- [ ] Critical violations → `passes = False` (blocks publication)
- [ ] Warning violations → `passes = True` but violations still recorded (flagged for review)
- [ ] Add `has_critical` property to ComplianceResult for easy checking

#### F. Tests (`tests/test_generation/test_nerdy_compliance.py`)

- [ ] TDD first
- [ ] "Help your student succeed" → critical violation (nerdy_wrong_address)
- [ ] "Best SAT Prep in town" → critical violation (nerdy_wrong_product)
- [ ] "Spots filling fast!" → critical violation (fake_urgency_spots)
- [ ] "Limited enrollment available" → critical violation (fake_urgency_limited)
- [ ] "Don't miss out on this opportunity" → critical violation (fake_urgency_miss)
- [ ] "Unlock their potential with custom strategies" → 2 warnings (corporate_jargon)
- [ ] "Help your child raise their SAT score with tutoring" → passes clean (0 violations)
- [ ] "SAT Tutoring that works" → passes clean
- [ ] "Princeton Review charges $252/hr for 1:1. We charge $349/month." → passes (competitor comparison with data is allowed)
- [ ] "Kaplan is terrible" → critical (disparagement without data)
- [ ] "Guaranteed 1500+" → critical (still caught by existing rule)
- [ ] "Online tutoring available" → critical (nerdy framing rule)
- [ ] Minimum: 12 tests

#### G. Documentation

- [ ] Add PB-03 entry in `docs/DEVLOG.md`

---

## Important Context

### Nerdy Language Rules Summary

| Do | Don't |
|----|-------|
| "your child" | "your student" |
| "SAT Tutoring" | "SAT Prep" |
| Conditional claims ("200 points in 16 sessions") | Bare score promises ("gain 200 points") |
| Real competitor pricing | Competitor disparagement |
| Specific mechanisms (digital SAT tools, diagnostic) | Vague "personalized", "expert", "data-driven" |
| Calendar urgency (test dates, deadlines) | Fake scarcity ("spots filling fast") |
| Plain parent language ("raise your child's score") | Corporate jargon ("unlock potential") |

### Compliance Severity Model

```
Critical → blocks publication (passes = False)
  - "your student", "SAT Prep", fake urgency, score guarantees, online tutoring framing

Warning → flagged but doesn't block (passes = True, violations recorded)
  - Corporate jargon, vague claims

Info → informational only (not a violation)
  - Competitor names used with real data
```

### Files to Modify

| File | Action |
|------|--------|
| `generate/compliance.py` | Add ~20 new patterns, adjust competitor rule, add severity handling |
| `tests/test_generation/test_nerdy_compliance.py` | Create — Nerdy-specific compliance tests |

### Files You Should READ for Context

| File | Why |
|------|-----|
| `generate/compliance.py` | Current 18 patterns to extend |
| `data/brand_knowledge.json` | messaging_rules.dos and donts (from PB-01) |
| `/Users/jad/Downloads/C4_Automatic_Ad_Generator_Supplementary.md` | Source rules (lines 6–42 + 93–123) |

---

## Definition of Done

- [ ] All Nerdy do's/don'ts enforced as regex patterns
- [ ] "your student" and "SAT Prep" are critical violations
- [ ] Fake urgency patterns are critical violations
- [ ] Corporate jargon patterns are warnings
- [ ] Competitor comparisons with real data are allowed
- [ ] `check_compliance()` distinguishes critical vs. warning
- [ ] Tests pass
- [ ] Lint clean
- [ ] DEVLOG updated

---

## Estimated Time: 45–60 minutes

---

## After This Ticket: What Comes Next

**PB-06 (Evaluator)** will use these compliance rules to add scoring penalties — ads that violate Nerdy language rules get lower Brand Voice and Clarity scores.
