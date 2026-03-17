# PB-09 Primer: Validation Run + Quality Comparison

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** PB-01 through PB-08 must be complete. See `docs/development/tickets/PB-00-phase-plan.md`.

---

## What Is This Ticket?

PB-09 is the final validation — run the pipeline with each of the 7 personas, compare output quality to the pre-PB baseline, verify all 51+ integration tests pass, and document findings.

### Why It Matters

- Theory vs. practice: PB-01 through PB-07 changed the pipeline; PB-08 wrote tests; PB-09 proves it works with real LLM output
- Quality comparison shows whether the Nerdy content actually improves ad scores
- Per-persona results reveal which personas produce the best ads and where the pipeline still struggles
- Documentation creates the audit trail for the Nerdy team review

---

## What Was Already Done

- PB-01–PB-07: Full pipeline integration (brand KB, hooks, compliance, expansion, generation, evaluation, dashboard)
- PB-08: 51+ integration tests across 8 files
- Existing baseline: ads in `data/ledger.jsonl` from pre-PB pipeline runs

---

## What This Ticket Must Accomplish

### Deliverables Checklist

#### A. Run PB-08 Test Suite

- [ ] `pytest tests/test_pb/ -v` — all 51+ tests pass
- [ ] Fix any failures before proceeding to pipeline run

#### B. Generate Ads — 3 Per Persona (21 total)

- [ ] Run the pipeline 7 times (once per persona), 3 ads each:
  ```bash
  python run_pipeline.py --max-ads 3 --persona athlete_recruit
  python run_pipeline.py --max-ads 3 --persona suburban_optimizer
  python run_pipeline.py --max-ads 3 --persona immigrant_navigator
  python run_pipeline.py --max-ads 3 --persona cultural_investor
  python run_pipeline.py --max-ads 3 --persona system_optimizer
  python run_pipeline.py --max-ads 3 --persona neurodivergent_advocate
  python run_pipeline.py --max-ads 3 --persona burned_returner
  ```
- [ ] Or create a validation script: `scripts/run_pb_validation.py`

#### C. Compliance Check All Output

- [ ] Run compliance check on all 21 generated ads
- [ ] Verify 0 critical violations:
  - No "your student"
  - No "SAT Prep"
  - No fake urgency
  - No corporate jargon in critical positions
- [ ] Count and document warnings (acceptable)

#### D. Evaluation Score Analysis

- [ ] Collect all 21 evaluation scores (5 dimensions + aggregate)
- [ ] Compare to baseline:
  - Pre-PB average aggregate score (from existing ledger)
  - Post-PB average aggregate score
  - Per-dimension comparison
- [ ] Per-persona breakdown:
  - Which persona produces the highest scores?
  - Which persona struggles the most?
  - Which dimensions are strongest/weakest per persona?

#### E. Hook Attribution Analysis

- [ ] For each generated ad, identify which hook (if any) from the library was used as inspiration
- [ ] Calculate: what % of generated ads used a persona-specific hook?
- [ ] Identify: did any persona's hooks consistently produce better scores?

#### F. Document Findings

Add to `docs/development/DEVLOG.md`:

- [ ] PB-09 entry with:
  - Test suite results (X/Y passing)
  - Per-persona score table (7 rows × 6 columns: persona, avg_score, clarity, VP, CTA, BV, ER)
  - Baseline comparison (pre-PB vs post-PB averages)
  - Compliance results (violations found, if any)
  - Top 3 best-performing ads (copy + scores + persona)
  - Observations: what worked, what didn't, what to improve next
  - Hook utilization stats

#### G. Update Dashboard Data

- [ ] Run `scripts/build_dashboard.py` to regenerate dashboard with PB output
- [ ] Verify dashboard shows persona tags in Ad Library
- [ ] Verify Overview metrics reflect PB run

#### H. Fix Issues

- [ ] If any test failures: fix and re-run
- [ ] If any compliance violations in generated ads: investigate root cause (prompt issue? compliance pattern too broad?)
- [ ] If scores are lower than baseline: investigate (over-constraining? hooks too prescriptive?)

---

## Success Criteria (from PB-00-phase-plan.md)

| Criterion | Target |
|-----------|--------|
| "your child" compliance | 100% (21/21 ads) |
| "SAT Tutoring" compliance | 100% |
| No fake urgency | 0 violations |
| Persona hooks used | ≥ 1 hook per ad |
| Conditional claims have specificity | No bare "200 points" |
| Average score (persona-matched) | > 7.5 (vs ~7.2 baseline) |
| Compliance detection rate | 100% on test inputs |
| PB-08 test suite | 51/51 passing |

---

## Files to Create/Modify

| File | Action |
|------|--------|
| `scripts/run_pb_validation.py` | Optional — validation script |
| `docs/development/DEVLOG.md` | PB-09 entry with full results |
| `output/dashboard_data.json` | Regenerated with PB output |
| `output/dashboard.html` | Regenerated with PB output |

---

## Definition of Done

- [ ] PB-08 test suite: 51+ tests all passing
- [ ] 21 ads generated (3 per persona)
- [ ] 0 critical compliance violations
- [ ] Average score > 7.5 for persona-matched ads
- [ ] DEVLOG updated with per-persona results table and baseline comparison
- [ ] Dashboard regenerated with PB output
- [ ] All issues found during validation are fixed

---

## Estimated Time: 30–45 minutes

---

## After This Ticket: What Comes Next

**Phase PB is complete.** The pipeline now generates Nerdy-approved, persona-specific, compliance-clean ads. Next potential work: PA-12 (production deployment) or further persona/hook refinement based on PB-09 findings.
