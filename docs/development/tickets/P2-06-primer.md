# P2-06 Primer: Tiered Compliance Filter

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** P1-02 (ad copy generator with compliance prompt layer), P1-04 (evaluator), P0-04 (brand KB with compliance rules) must be complete. See `docs/DEVLOG.md`.

---

## What Is This Ticket?

P2-06 implements the **three-layer tiered compliance architecture** (R3-Q3). Defense-in-depth: (1) generation prompts embed hard constraints, (2) evaluator includes binary compliance check, (3) regex/keyword filter catches literal violations. A violation must beat ALL three layers to reach production. This ticket builds layer 3 (regex filter) and validates all three layers work together.

### Why It Matters

- **Prevention Over Detection Over Correction** (Pillar 2): Layer 1 prevents violations at generation; Layer 2 detects them in evaluation; Layer 3 catches literal patterns that slip through
- R3-Q3 selected tiered compliance as the best approach — violations must beat all three systems
- Compliance failures are non-negotiable: guaranteed scores, competitor disparagement, absolute promises can cause legal/brand issues
- The regex layer is the cheapest and fastest — catches obvious violations without an API call
- Brand KB (`data/brand_knowledge.json`) already defines compliance rules; this ticket enforces them

---

## What Was Already Done

- P1-02: Generation prompt includes compliance constraints ("Never claim guaranteed scores...")
- P1-04: Evaluator produces quality scores but does NOT have a binary compliance check yet
- P0-04: Brand KB has `compliance_rules` section with prohibited patterns
- P0-09: Competitive pattern database identifies competitor names to watch for

---

## What This Ticket Must Accomplish

### Goal

Build the regex compliance filter (Layer 3), add binary compliance check to evaluation (Layer 2), and validate all three layers catch known violations with zero false negatives.

### Deliverables Checklist

#### A. Regex Compliance Filter (`generate/compliance.py`)

- [ ] `ComplianceResult` dataclass: `passes: bool`, `violations: list[ComplianceViolation]`
- [ ] `ComplianceViolation` dataclass: `rule_name: str`, `matched_text: str`, `pattern: str`, `severity: str`
- [ ] `check_compliance(text: str) -> ComplianceResult`
  - Pattern categories:
    - **Guaranteed outcomes:** `r"(?i)\bguarantee[ds]?\b"`, `r"(?i)\b100\s*%\b"`, `r"(?i)\balways\s+pass"`, `r"(?i)\bnever\s+fail"`
    - **Unverified pricing:** `r"\$\d+"` (dollar amounts without disclaimer context)
    - **Competitor disparagement:** `r"(?i)\b(Princeton\s+Review|Kaplan|Khan\s+Academy|Chegg)\b"` in negative context
    - **Absolute promises:** `r"(?i)\b(guaranteed|100%|always works|never fail|proven results)\b"`
    - **Fear-based language:** `r"(?i)\b(falling behind|left behind|fail(ing|ed)?|deficient)\b"` targeting the child
  - Returns all matched violations with rule name and matched text
- [ ] `is_compliant(text: str) -> bool`
  - Convenience function: True if no violations found

#### B. Evaluator Compliance Check (Layer 2)

- [ ] The evaluator (P1-04) already produces scores. This ticket does NOT modify the evaluator prompt — instead, compliance is checked separately and the result is combined.
- [ ] `check_evaluator_compliance(evaluation_result) -> bool`
  - Checks if any dimension scored below brand safety threshold (4.0)
  - Checks if confidence flags indicate compliance concerns
  - This is a lightweight check using existing evaluation data

#### C. Compliance Validation Test Suite (`tests/test_pipeline/test_compliance.py`)

- [ ] `test_guaranteed_score_caught`: "Guaranteed 1500+ SAT score" → violation
- [ ] `test_competitor_name_caught`: "Princeton Review is terrible" → violation
- [ ] `test_absolute_promise_caught`: "100% of students pass" → violation
- [ ] `test_dollar_amount_caught`: "Only $99/session" → violation (unverified pricing)
- [ ] `test_fear_language_caught`: "Your child is falling behind" → violation
- [ ] `test_clean_ad_passes`: A well-written compliant ad → no violations
- [ ] `test_multiple_violations_all_reported`: Ad with 3 violations → all 3 listed
- [ ] `test_case_insensitive_matching`: "GUARANTEED" and "guaranteed" both caught
- [ ] `test_three_layers_catch_all_violations`: Known-bad ads checked against all 3 layers; zero false negatives
- [ ] `test_compliance_result_structure`: Result has passes, violations list
- [ ] Minimum: 10+ tests

#### D. Known-Bad Test Ads

- [ ] Create set of known-bad ads in tests that violate specific rules:
  ```python
  KNOWN_BAD_ADS = [
      "Guaranteed 1500+ SAT score or your money back!",
      "Princeton Review is terrible — choose us instead",
      "100% of students pass with our program, always",
      "Your child is falling behind — don't let them fail",
      "Only $49.99 for unlimited tutoring sessions!",
  ]
  ```
- [ ] Each must be caught by the regex layer

#### E. Documentation

- [ ] Add P2-06 entry in `docs/DEVLOG.md`

---

## Important Context

### Architectural Decisions

| Decision | Reference | Summary |
|----------|-----------|---------|
| Tiered compliance | R3-Q3 (Option C) | Defense-in-depth: prompt + evaluator + regex |
| Compliance rules | Brand KB | `data/brand_knowledge.json` → `compliance_rules` section |
| Zero false negatives | R3-Q3 | Every known violation pattern must be caught; false positives acceptable |

### Three Compliance Layers

```
Layer 1: Generation Prompt (P1-02)
  → "Never claim guaranteed scores, never disparage competitors..."
  → Prevention: stops violations from being generated

Layer 2: Evaluator Check (P1-04 + P2-05)
  → Score-based: any dimension < 4.0 = brand safety stop
  → Detection: catches tone/quality violations

Layer 3: Regex Filter (P2-06) ← THIS TICKET
  → Pattern matching: guaranteed, 100%, competitor names, dollar amounts
  → Catchall: cheapest, fastest, most deterministic
```

### Files to Create

| File | Why |
|------|-----|
| `generate/compliance.py` | Regex compliance filter |
| `tests/test_pipeline/test_compliance.py` | Compliance validation tests |

### Files You Should READ for Context

| File | Why |
|------|-----|
| `data/brand_knowledge.json` | Compliance rules, competitor names |
| `generate/ad_generator.py` | Generation prompt with Layer 1 constraints |
| `evaluate/evaluator.py` | Evaluation structure for Layer 2 integration |
| `evaluate/confidence_router.py` | Brand safety trigger (P2-05) |

---

## Definition of Done

- [ ] Regex filter catches all known violation patterns
- [ ] Zero false negatives on test set of known-bad ads
- [ ] All three layers validated working together
- [ ] ComplianceResult provides actionable violation details
- [ ] 10+ tests passing
- [ ] Lint clean
- [ ] DEVLOG updated

---

## After This Ticket: What Comes Next

**P2-07 (End-to-End Integration Test)** validates the entire pipeline with checkpoint-resume: start, interrupt mid-batch, resume, and verify identical output. This is the final P2 ticket — after it, the testing & validation phase is complete.
