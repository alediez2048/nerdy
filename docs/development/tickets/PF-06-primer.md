# PF-06 Primer: Test Coverage Audit & Gaps

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** PF-04 (frontend bugs), PF-05 (backend bugs). See `docs/DEVLOG.md`.

---

## What Is This Ticket?

PF-06 audits the full test suite, identifies coverage gaps for critical user-facing workflows, fixes any failing or flaky tests, and adds missing integration tests. The goal is a green, reliable test suite that covers all critical paths.

### Why It Matters

- Tests built across 80+ tickets by different agent sessions may have import errors, stale mocks, or broken assumptions
- Some tests may have been deleted or moved during refactoring
- Critical workflows (session creation → pipeline → results) may lack end-to-end coverage
- A passing, comprehensive test suite is the safety net for all future changes

---

## What This Ticket Must Accomplish

### Goal

Full test suite passes (`pytest tests/ -v`), no flaky tests, and critical paths have integration test coverage.

### Deliverables Checklist

#### A. Run Full Test Suite

- [ ] Execute `pytest tests/ -v --tb=long` and capture output
- [ ] Categorize failures:
  - **Import errors** — broken imports from moved/renamed modules
  - **Fixture errors** — missing or incompatible test fixtures
  - **Logic failures** — tests that fail because behavior changed
  - **Flaky tests** — tests that pass/fail inconsistently
  - **Collection errors** — tests that can't even be collected

#### B. Fix Broken Tests

- [ ] Fix import errors (update imports to match current module structure)
- [ ] Fix stale fixtures (update mocks to match current function signatures)
- [ ] Update logic tests where behavior intentionally changed
- [ ] Delete truly obsolete tests (with justification in commit message)
- [ ] Do NOT delete tests that expose real bugs — fix the bug in PF-04/05

#### C. Test Coverage Gaps — Add Missing Tests

- [ ] Session CRUD integration: create → list → get → update → delete
- [ ] Image pipeline integration: session creation triggers pipeline, ledger written
- [ ] Video pipeline integration: video session routes to video pipeline
- [ ] Ad preview API: correct preview returned for image and video sessions
- [ ] Dashboard data export: `export_dashboard.py` produces valid data
- [ ] Progress reporting: SSE events published in correct order

#### D. Verify Test Categories

- [ ] **Golden set tests** (`tests/test_evaluation/test_golden_set.py`) — still passing
- [ ] **Inversion tests** (`tests/test_evaluation/test_inversion.py`) — still passing
- [ ] **Adversarial tests** (`tests/test_evaluation/test_adversarial.py`) — still passing
- [ ] **Correlation tests** (`tests/test_evaluation/test_correlation.py`) — still passing
- [ ] **Pipeline tests** (`tests/test_pipeline/`) — all passing
- [ ] **App tests** (`tests/test_app/`) — all passing
- [ ] **PB tests** (`tests/test_pb/`) — all passing

#### E. Final Verification

- [ ] `pytest tests/ -v` — zero failures
- [ ] `ruff check .` — zero warnings
- [ ] No tests skipped without `@pytest.mark.skip(reason="...")` justification
- [ ] Total test count documented

---

## Branch & Merge Workflow

Work on `video-implementation-2.0` branch (current branch).

---

## Important Context

### Files to Modify

| File | Likely Issues |
|------|--------|
| `tests/test_generation/*.py` | Import errors from module changes |
| `tests/test_pipeline/*.py` | Stale mocks from pipeline refactoring |
| `tests/test_app/*.py` | Schema changes from PC tickets |
| `tests/test_pb/*.py` | Possible import issues |

### Files You Should READ for Context

| File | Why |
|------|-----|
| `tests/conftest.py` | Shared fixtures |
| Test directory structure | Understand test organization |

### Files You Should NOT Modify

- Production code (unless a test exposes a real bug — document and defer to PF-04/05)
- Test data files (`tests/test_data/`)

---

## Definition of Done

- [ ] `pytest tests/ -v` passes with zero failures
- [ ] `ruff check .` clean
- [ ] No flaky tests
- [ ] Critical path integration tests exist
- [ ] Total test count documented in DEVLOG
- [ ] DEVLOG updated

---

## Estimated Time

| Task | Estimate |
|------|----------|
| Run full suite + categorize failures | 10 min |
| Fix broken tests | 20–40 min |
| Add missing integration tests | 20–30 min |
| Verify all categories pass | 10 min |
| DEVLOG | 5 min |

---

## After This Ticket: What Comes Next

- **PF-07:** Documentation cleanup
- **PF-10:** Final verification
