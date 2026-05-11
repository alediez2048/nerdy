# PH-07 Primer: Post-Implementation Verification

**For:** New Agent session
**Project:** Ad-Ops-Autopilot
**Date:** May 2026
**Phase plan:** [`PH-00-phase-plan.md`](PH-00-phase-plan.md)
**Depends on:** PH-01..PH-06 complete on `final-submission`
**Branch:** `feature/PH-07-verification`

---

## What Is This Ticket?

PH-07 is the **integration verification gate** that must pass before merging the phase into `main`. Each prior ticket has its own per-merge gate (lint, unit tests, `--dry-run`, DEVLOG). PH-07 confirms the phases compose correctly end-to-end against real services.

This ticket does NOT change code. It runs the system and confirms behavior.

---

## Verification Plan

### 1. Static Checks
- [ ] `ruff check .` — clean
- [ ] `mypy iterate/ evaluate/ generate/ app/api/ app/workers/ 2>&1 | tee logs/ph07-mypy.log` — no NEW errors (compare against a baseline taken at start of phase)
- [ ] `npx gitnexus analyze` — index up to date
- [ ] `npx gitnexus impact LedgerWriter --repo Nerdy`, `attribute_session_cost`, `PipelineOrchestrator`, `EvaluationPipeline`, `image_model_router.choose_model` — none CRITICAL outside expected modules

### 2. Test Suite
- [ ] `python -m pytest tests/ -v 2>&1 | tee logs/ph07-pytest.log`
  - All tests that passed pre-PH still pass post-PH
  - Known pre-PH failures (1 API-dependent per README) unchanged
  - No new failures of any kind
- [ ] Test count not regressed: `grep "passed\|failed" logs/ph07-pytest.log`
- [ ] Golden-set scores byte-identical: `python -m pytest tests/test_evaluation/test_golden_set.py -v`

### 3. CLI End-to-End
- [ ] `python run_pipeline.py --dry-run --max-ads 5` — exits 0, produces ledger entries, no errors
- [ ] `python run_pipeline.py --max-ads 3` (live API) — produces 3 evaluated ads, ledger valid JSONL
- [ ] `python run_pipeline.py --resume` — picks up from checkpoint without re-spending

### 4. Web Stack End-to-End
Prerequisites: `docker compose up -d db redis`, API + worker running, frontend on `:5173`.
- [ ] Create a new copy-only session via `POST /api/sessions` (curl or UI)
- [ ] Observe SSE progress events at `/api/sessions/{id}/progress` — events match prior schema
- [ ] Session completes successfully; ad library populated; ledger entries match CLI run for an equivalent brief
- [ ] Open `/global-dashboard` — all 8 panels render
- [ ] Cost numbers in dashboard match `CostAttributor.attribute_session_cost(session_id).total_usd` for the session

### 5. Cost Regression Check
- [ ] Pick a known historical session ID (pre-PH)
- [ ] Run `python -c "from evaluate.cost_attributor import attribute_session_cost; print(attribute_session_cost('<sid>'))"`
- [ ] Cross-reference against the pre-PH cost shown in `data/cost_manifest.json` or a prior dashboard screenshot
- [ ] Any discrepancy must be **explained** (legitimate bug fix) — not papered over

### 6. Ledger Format Compatibility
- [ ] Save a snapshot of an existing pre-PH ledger: `cp data/ledger.jsonl /tmp/ledger-pre-PH.jsonl`
- [ ] After PH-01 lands, parse the snapshot with the new LedgerReader: every event reads cleanly
- [ ] Generate a fresh ledger from a fixture brief pre- and post-PH; diff: byte-identical (modulo timestamps and UUIDs)

### 7. Performance Smoke
- [ ] Baseline timing for a 3-ad batch on `main` (before phase): record in `logs/ph07-baseline.txt`
- [ ] Timing after PH-01..PH-06: must be within ±10% of baseline (no batch-time regression)
- [ ] If regression > 10%: investigate before merging

### 8. Manual UI Walkthrough
- [ ] Sign in with Clerk
- [ ] Create a campaign
- [ ] Create a session under the campaign
- [ ] Trigger the pipeline
- [ ] Watch progress in the SSE-driven view
- [ ] Confirm Ad Library renders with images
- [ ] Confirm Global Dashboard shows cost / ad count / score trends
- [ ] Curate an ad; share token works; CSV export works

### 9. Rollback Drill
- [ ] Confirm: reverting `feature/PH-07-verification` and `feature/PH-NN-*` branches in reverse order restores pre-phase state
- [ ] Document the merge SHAs so a future incident has a clear rollback target

---

## Deliverables

- [ ] `logs/ph07-pytest.log`, `logs/ph07-mypy.log`, `logs/ph07-baseline.txt` committed (or summarized in DEVLOG; logs/ is gitignored)
- [ ] DEVLOG entry with:
  - Final test count (pre-PH vs post-PH)
  - Cost reconciliation result for a sampled session
  - Performance delta (timing comparison)
  - Any deferred follow-ups discovered during verification
- [ ] Merge `feature/PH-07-verification` → `final-submission` → `main` (with `--no-ff`, matching the PG production-deploy pattern)
- [ ] After merge to `main`: monitor Railway + Vercel auto-redeploys; smoke-check production `/health` and `/api/sessions` (requires auth)

---

## Acceptance Criteria

- [ ] All 9 verification sections pass
- [ ] Production redeploy completes without errors
- [ ] `gitnexus_detect_changes({scope: "compare", base_ref: "main"})` after merge shows expected scope only
- [ ] DEVLOG entry committed and pushed

---

## Out of Scope for PH-07

- Bug fixes discovered during verification — those become PH-08+ tickets
- New tests beyond what's needed to verify PH-01..PH-06 behavior
- Migrating any of the deferred follow-ups (e.g. VideoProvider full abstraction)

---

## Notes for the Implementing Agent

This is a verification ticket, not a coding ticket. Don't refactor anything found "in passing." Capture findings in the DEVLOG and let the team prioritize follow-up tickets.
