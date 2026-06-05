# PI-11 Primer

**Source plan:** [`PI-PLAN.md`](PI-PLAN.md) — sliced from the ticket section below.
**Phase plan:** [`PI-00-phase-plan.md`](PI-00-phase-plan.md)

**Status:** ⏳ Not started

---

# Ticket PI-11: Verification gate

**Goal:** End-to-end live run on a fresh staging session. Confirm the granularity target (≥ 8 distinct composites across 15 variants), the rationale UX, cost reconciliation, and ledger format compatibility on a real ledger.

**Files:**
- No code changes
- Modify: `docs/development/DEVLOG.md` — add a `PI-11` entry at the top with the verification results
- Create: `docs/development/PI-MANUAL-TEST-RUNBOOK.md` (similar to PH-MANUAL-TEST-RUNBOOK.md)

- [ ] **Step 1: Run lint + full pytest as the green baseline**

```
.venv/bin/python -m ruff check .
.venv/bin/python -m pytest tests/ --tb=no -q
```

Record the pass/fail counts. Confirm no new regressions vs. PH baseline.

- [ ] **Step 2: Run a fresh image pipeline session**

```
.venv/bin/python run_pipeline.py --max-ads 5
```

Then read the resulting ledger:

```
.venv/bin/python - <<'PY'
import json, glob
latest = max(glob.glob('data/sessions/sess_*/ledger.jsonl'))
events = [json.loads(l) for l in open(latest)]
me = [e for e in events if e.get('event_type') == 'MediaEvaluation']
print(f'session: {latest}')
print(f'MediaEvaluation events: {len(me)} (expected 15 for 5 ads x 3 variants)')
composites = sorted({e['outputs']['composite_score'] for e in me})
print(f'distinct composites: {len(composites)} -> {composites}')
assert len(composites) >= 8, f'GRANULARITY TARGET MISSED: {len(composites)} < 8'
PY
```

Expected: assertion passes — ≥8 distinct composites.

- [ ] **Step 3: Run a fresh video pipeline session**

```
.venv/bin/python run_pipeline.py --max-ads 3 --session-type video
```

Check the resulting ledger has `MediaEvaluation` events with `media_type: "video"` and no `VideoEvaluated` / `VideoCoherenceChecked` / `VideoScored`.

- [ ] **Step 4: Open the dashboard locally and exercise the UI**

```
docker compose up -d
cd app/frontend && npm run dev
```

Sign in, navigate to the new session, open an ad in the Ad Library, expand a variant card, verify:
- 8 dimensions visible in the Evidence expander (10 for video)
- Each dimension has a non-generic rationale (no "good composition" placeholders)
- Winner card shows the "Why this won:" line
- Loser cards show "Lost on …" with worst-dim rationale

- [ ] **Step 5: Cost reconciliation**

```
.venv/bin/python - <<'PY'
from evaluate.cost_reporter import compute_session_cost_usd
from iterate.ledger_reader import LedgerReader
import glob
latest = max(glob.glob('data/sessions/sess_*/ledger.jsonl'))
reader = LedgerReader(latest)
total = compute_session_cost_usd(latest)
print(f'total: ${total:.4f}')
# Spot-check sum of MediaEvaluation tokens × Gemini 2.5 Flash rate
PY
```

Confirm: cost numbers are sane and the PH-02 CostAttributor still produces a clean breakdown.

- [ ] **Step 6: Calibration test re-run** (locks in granularity claim)

```
.venv/bin/python -m pytest tests/test_evaluation/test_media_quality_calibration.py -m calibration -v
```

Expected: PASS.

- [ ] **Step 7: Write the PI manual test runbook**

`docs/development/PI-MANUAL-TEST-RUNBOOK.md` — mirror the PH-MANUAL-TEST-RUNBOOK.md structure. Cover: dev-server smoke, image pipeline run, video pipeline run, dashboard variant-rationale visual check, calibration spread check, cost reconciliation. This is the document the next agent uses to verify a prod deploy is sound.

- [ ] **Step 8: Write the DEVLOG entry**

Append to the TOP of `docs/development/DEVLOG.md`:

```markdown
## 2026-XX-YY — PI-11: Phase verification gate (✅)

### Summary
End-to-end verification of PI-01..PI-10. Granularity target met; rubric
discriminates; rationales surfaced in UI; cost reconciles.

### Results
| Check | Result |
|---|---|
| ruff | clean |
| pytest | <N> passed / 6 baseline failures, zero PI regressions |
| Image pipeline run (5 ads × 3 variants) | <N> distinct composites across 15 variants (target ≥ 8) |
| Video pipeline run | <N> MediaEvaluation events with media_type='video' |
| Calibration test | PASS |
| Dashboard variant card | Evidence panel renders 8 dims with rationales |
| Cost reconciliation | ledger-attributed total within ±$0.01 of CostAttributor |

(...remaining sections per PH-07 template — scope shipped, branch state,
next steps, files changed.)
```

- [ ] **Step 9: Commit**

```
git add docs/development/DEVLOG.md docs/development/PI-MANUAL-TEST-RUNBOOK.md
git commit -m "docs(PI-11): phase verification gate — granularity target met"
```

- [ ] **Step 10: Merge to main + tag**

```
git checkout final-submission
git merge --no-ff feature/PI-XX  # (whatever branch the PI work lived on)
git tag pre-PI-deploy <prev-main-sha>
git checkout main && git merge --no-ff final-submission
git push origin main
```

(Adjust the branch name to match how the work was actually shipped.)

---
