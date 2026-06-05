# PI-10 Primer

**Source plan:** [`PI-PLAN.md`](PI-PLAN.md) — sliced from the ticket section below.
**Phase plan:** [`PI-00-phase-plan.md`](PI-00-phase-plan.md)

**Status:** ⏳ Not started

---

# Ticket PI-10: Retire 6 legacy modules + their tests

**Goal:** Delete the six legacy evaluator modules and their dedicated test files now that nothing imports them. Update any remaining test files that still imported retired symbols.

**Files:**
- Delete: `evaluate/image_evaluator.py`
- Delete: `evaluate/coherence_checker.py`
- Delete: `evaluate/image_scorer.py`
- Delete: `evaluate/video_evaluator.py`
- Delete: `evaluate/video_attributes.py`
- Delete: `evaluate/video_coherence.py`
- Delete: `evaluate/video_scorer.py`
- Delete: `tests/test_pipeline/test_image_evaluator.py`
- Delete: `tests/test_pipeline/test_coherence_checker.py`
- Delete: `tests/test_pipeline/test_image_scorer.py`
- Delete: any `tests/test_pipeline/test_video_*.py` that targeted only retired modules
- Modify (probably): `iterate/batch_processor.py` if any stale imports linger
- Modify (probably): `generate_video/*.py` if any stale imports linger

- [ ] **Step 1: Verify no live imports of the retired modules remain**

```
grep -rn "from evaluate.image_evaluator\|from evaluate.coherence_checker\|from evaluate.image_scorer\|from evaluate.video_evaluator\|from evaluate.video_attributes\|from evaluate.video_coherence\|from evaluate.video_scorer" --include="*.py" .
```

Expected: ZERO matches in production code (matches only inside tests that are about to be deleted). If anything remains in production, go back to PI-04 / PI-06 and finish the migration before this ticket.

- [ ] **Step 2: Delete the seven `evaluate/` modules and their tests**

```
git rm evaluate/image_evaluator.py evaluate/coherence_checker.py evaluate/image_scorer.py
git rm evaluate/video_evaluator.py evaluate/video_attributes.py evaluate/video_coherence.py evaluate/video_scorer.py
git rm tests/test_pipeline/test_image_evaluator.py tests/test_pipeline/test_coherence_checker.py tests/test_pipeline/test_image_scorer.py
git rm tests/test_pipeline/test_video_evaluator.py tests/test_pipeline/test_video_attributes.py tests/test_pipeline/test_video_coherence.py tests/test_pipeline/test_video_scorer.py 2>/dev/null || true
```

(Adjust the video test files based on what's actually in the tree.)

- [ ] **Step 3: Run the full test suite**

```
.venv/bin/python -m pytest tests/ --tb=line -q
```

Expected: all pass except the known PH-baseline failures (5 Clerk env-dep + 1 LLM flake). Any new failures point to a test file that still imports a retired module — fix or delete those imports.

- [ ] **Step 4: Run ruff**

```
.venv/bin/python -m ruff check .
```

Expected: clean.

- [ ] **Step 5: Run GitNexus impact + detect_changes** (per CLAUDE.md mandate)

```
npx gitnexus analyze
npx gitnexus detect_changes
```

Confirm: only the expected files in the expected scope.

- [ ] **Step 6: Commit**

```
git commit -m "chore(PI-10): retire 6 legacy evaluators + their tests"
```

---
