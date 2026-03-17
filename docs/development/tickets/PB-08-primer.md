# PB-08 Primer: Integration Test Suite — Nerdy Content Quality

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** PB-01 through PB-07 must be complete. See `docs/development/tickets/PB-00-phase-plan.md`.

---

## What Is This Ticket?

PB-08 builds a comprehensive integration test suite (51+ tests across 8 files) verifying the entire Nerdy content quality integration works end-to-end — from brand KB ingestion through compliance, generation, evaluation, and dashboard.

### Why It Matters

- Each PB ticket has its own unit tests, but integration tests verify the pieces work together
- The test suite becomes the regression safety net — any future change that breaks Nerdy language rules will be caught
- 51+ tests across 8 files covers every layer: data, hooks, compliance, expansion, generation, evaluation, pipeline, dashboard

---

## What Was Already Done

- PB-01 through PB-07: all pipeline and frontend changes implemented with per-ticket unit tests
- Existing test infrastructure: pytest, in-memory SQLite for API tests, mock Gemini for generation/evaluation tests

---

## What This Ticket Must Accomplish

### Test Files and Coverage

#### A. `tests/test_pb/test_brand_kb.py` (7 tests)

| Test | What It Verifies |
|------|-----------------|
| test_all_personas_loaded | 7 personas in brand_knowledge.json with required fields |
| test_persona_required_fields | Each persona has psychology, funnel_position, trigger, conversion_likelihood |
| test_messaging_dos | dos list contains "your child", "SAT Tutoring" |
| test_messaging_donts | donts list contains "your student", "SAT Prep" |
| test_competitor_pricing | competitors_detailed has real pricing for Princeton Review, Kaplan, Khan |
| test_offer_positioning | offer section has membership model, pricing, results claims |
| test_persona_ctas | CTA library has persona-specific entries beyond generic "Learn More" |

#### B. `tests/test_pb/test_hooks.py` (6 tests)

| Test | What It Verifies |
|------|-----------------|
| test_hooks_count | 80+ hooks loaded from hooks_library.json |
| test_hook_required_fields | Each hook has hook_id, persona, hook_text, psychology, cta_text |
| test_persona_filtering | get_hooks_for_persona("athlete_recruit") returns only athlete hooks |
| test_seed_determinism | Same seed → same result |
| test_seed_diversity | Different seeds → different orderings |
| test_all_personas_have_hooks | Every persona in brand KB has ≥ 3 hooks |

#### C. `tests/test_pb/test_nerdy_compliance.py` (11 tests)

| Test | What It Verifies |
|------|-----------------|
| test_your_student_critical | "your student" → critical violation |
| test_sat_prep_critical | "SAT Prep" → critical violation |
| test_spots_filling_critical | "spots filling fast" → critical |
| test_limited_enrollment_critical | "limited enrollment" → critical |
| test_corporate_jargon_warning | "unlock potential" → warning (not critical) |
| test_maximize_score_warning | "maximize score potential" → warning |
| test_your_child_clean | "your child" passes with 0 violations |
| test_sat_tutoring_clean | "SAT Tutoring" passes clean |
| test_clean_nerdy_copy | Full Nerdy-approved ad copy passes all checks |
| test_competitor_with_data_allowed | "Princeton Review charges $252/hr" → not a violation |
| test_score_guarantee_still_critical | "guaranteed 1500+" → still caught |

#### D. `tests/test_pb/test_persona_expansion.py` (6 tests)

| Test | What It Verifies |
|------|-----------------|
| test_athlete_persona_injected | expand_brief with persona="athlete_recruit" includes athlete context |
| test_expanded_has_persona_field | ExpandedBrief.persona matches input |
| test_expanded_has_hooks | ExpandedBrief.suggested_hooks is non-empty list |
| test_conversion_has_offer | Conversion goal → offer_context is not None |
| test_awareness_no_offer | Awareness goal → offer_context is None |
| test_messaging_rules_in_constraints | ExpandedBrief.constraints includes Nerdy language rules |

#### E. `tests/test_pb/test_nerdy_generation.py` (6 tests)

| Test | What It Verifies |
|------|-----------------|
| test_uses_your_child | Generated ad contains "your child", never "your student" |
| test_avoids_sat_prep | Generated ad doesn't contain "SAT Prep" |
| test_persona_cta | Generated CTA is in expanded VALID_CTAS |
| test_meta_structure | Generated ad has hook line + body + CTA structure |
| test_conversion_has_mechanism | Conversion ad includes specific mechanism or conditional claim |
| test_athlete_references_recruiting | Athlete persona ad references recruiting/scholarship |

#### F. `tests/test_pb/test_nerdy_evaluator.py` (6 tests)

| Test | What It Verifies |
|------|-----------------|
| test_your_student_penalized | Ad with "your student" → Brand Voice ≤ 4.0 |
| test_specificity_rewarded | Specific mechanism ad scores higher VP than vague ad |
| test_corporate_jargon_penalized | "unlock potential" ad scores lower Clarity |
| test_fake_urgency_penalized | "spots filling fast" ad scores lower Brand Voice |
| test_calibration_9_example | Score-9 anchor evaluates ≥ 8.0 |
| test_calibration_3_example | Score-3 anchor evaluates ≤ 4.5 |

#### G. `tests/test_pb/test_pb_e2e.py` (5 tests)

| Test | What It Verifies |
|------|-----------------|
| test_full_pipeline_with_persona | brief → expand → generate → evaluate → compliance passes |
| test_pipeline_zero_critical_violations | Output has 0 critical compliance violations |
| test_pipeline_meets_threshold | At least 1 of 3 ads scores ≥ 7.0 |
| test_pipeline_has_persona_metadata | Ledger events contain persona field |
| test_pipeline_has_hook_attribution | Output references which hook was used |

#### H. `tests/test_pb/test_persona_dashboard.py` (4 tests)

| Test | What It Verifies |
|------|-----------------|
| test_config_accepts_persona | SessionConfig with persona field validates |
| test_summary_includes_persona | Dashboard summary endpoint includes persona |
| test_ads_have_persona_tags | Ad library returns ads with persona metadata |
| test_persona_filter_works | Persona filter on ad library returns correct subset |

---

### Implementation Notes

- [ ] Create `tests/test_pb/` directory with `__init__.py`
- [ ] Use existing test patterns: mock Gemini for LLM calls, in-memory SQLite for API tests
- [ ] For evaluator tests (F): either mock Gemini responses or use pre-scored test fixtures
- [ ] For e2e tests (G): mock all API calls, verify data flow through the pipeline
- [ ] Each test file should be independently runnable: `pytest tests/test_pb/test_brand_kb.py -v`

---

## Definition of Done

- [ ] 8 test files created in `tests/test_pb/`
- [ ] 51+ tests total, all passing
- [ ] Tests cover: data (A,B), compliance (C), expansion (D), generation (E), evaluation (F), e2e (G), dashboard (H)
- [ ] `pytest tests/test_pb/ -v` passes with 0 failures
- [ ] DEVLOG updated

---

## Estimated Time: 90–120 minutes
