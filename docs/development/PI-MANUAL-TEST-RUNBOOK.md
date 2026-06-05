# PI Phase — Manual Test Runbook

**Purpose:** Exercise the unified MediaQuality evaluator end-to-end
before promoting `final-submission` to `main`. PI-01..PI-10 replace six
legacy evaluator modules with a single `evaluate/media_quality.py`
that emits rationale-bearing `MediaEvaluation` events for both image
and video.

**Branch under test:** `final-submission` (at `ce97d74` or later)
**Baseline for comparison:** the last PH SHA before the PI series.

**Estimated time:** ~45 minutes for the full pass.

---

## How to Use This Runbook

Run top to bottom. Tick each `[ ]` once verified. If something fails:
stop, capture the symptom under **Findings** at the bottom, and decide
whether it blocks the deploy.

The phase replaces evaluator internals AND the variant card UI. Most
items below assert that **the new path produces richer output, not
that the old path still works** (it has been removed).

---

## 0 — Local Environment Up

- [ ] `docker compose ps` — `nerdy-api-1`, `nerdy-worker-1`,
      `nerdy-db-1`, `nerdy-redis-1` all `Up`
- [ ] API docs: `curl -sfo /dev/null -w "%{http_code}\n"
      http://localhost:8000/docs` → `200`
- [ ] Frontend responds: `curl -sfo /dev/null -w "%{http_code}\n"
      http://localhost:5173/` → `200`
- [ ] Browser opens `http://localhost:5173/` without console errors

If any of these fail, fix the environment before continuing.

---

## 1 — Lint + Test Baseline

```
.venv/bin/python -m ruff check .
.venv/bin/python -m pytest tests/ --tb=no -q
```

- [ ] ruff: `All checks passed!`
- [ ] pytest: ~993 passed / 2 skipped. The only red items must be the
      known PH-baseline (5 Clerk env-dep auth tests + 1 LLM-flake
      progress test + adversarial / golden-set / inversion errors
      caused by the retired `gemini-2.0-flash` model). Zero new PI
      regressions.

---

## 2 — Image Pipeline Live Run

Requires a working `GEMINI_API_KEY` for a current model. With the new
model wired in:

```
.venv/bin/python run_pipeline.py --max-ads 5
```

Then inspect the most recent session ledger:

```
.venv/bin/python - <<'PY'
import json, glob
latest = max(glob.glob('data/sessions/sess_*/ledger.jsonl'))
events = [json.loads(line) for line in open(latest)]
me = [e for e in events if e.get('event_type') == 'MediaEvaluation']
print(f'session: {latest}')
print(f'MediaEvaluation events: {len(me)} (expected 15 for 5 ads x 3 variants)')
composites = sorted({e['outputs']['composite_score'] for e in me})
print(f'distinct composites: {len(composites)} -> {composites}')
assert len(composites) >= 8, f'GRANULARITY TARGET MISSED: {len(composites)} < 8'
PY
```

- [ ] 15 `MediaEvaluation` events written (5 ads × 3 variants)
- [ ] ≥ 8 distinct `composite_score` values (PI-00 granularity target)
- [ ] Zero `ImageEvaluated` or `ImageScored` events in the new session
      (`grep -c 'ImageEvaluated\|ImageScored' <ledger> = 0`)

---

## 3 — Video Pipeline Live Run

```
.venv/bin/python run_pipeline.py --max-ads 3 --session-type video
```

Inspect:

```
.venv/bin/python - <<'PY'
import json, glob
latest = max(glob.glob('data/sessions/sess_*/ledger.jsonl'))
events = [json.loads(line) for line in open(latest)]
me = [e for e in events if e.get('event_type') == 'MediaEvaluation']
print('video MediaEvaluation events:', len(me))
print('media types:', {e['outputs'].get('media_type') for e in me})
print('failed:', sum(1 for e in events if e.get('event_type') == 'MediaEvaluationFailed'))
PY
```

- [ ] Each surviving variant emits a `MediaEvaluation` with
      `outputs.media_type == "video"` and 10 entries in `outputs.dimensions`
- [ ] Missing files surface as `MediaEvaluationFailed` (not zero-score
      `VideoEvaluated` ghosts) — fixes the 82-event ghost issue from PI-00
- [ ] Zero `VideoEvaluated` / `VideoCoherenceChecked` / `VideoScored`
      events in the new session

---

## 4 — Dashboard Variant Card UX

1. Browser: open `http://localhost:5173/`, sign in (or flip `DEV_MODE=true`
   in `.env` + restart `api`/`worker` to bypass).
2. Navigate to **Ad Library**, open the v2 session from §2.
3. Expand any ad and confirm the variant grid renders.

For the **winner** card:
- [ ] Top-right shows a green `✓ Selected` badge
- [ ] "Why this won — `<dim_a> +X.X`, `<dim_b> +Y.Y`" appears below the
      headline
- [ ] Evidence expander reveals all 8 image dimensions (10 for video)
      with score / weight / rationale columns
- [ ] No rationale reads as a placeholder ("good composition", "fine") —
      each names a specific element

For each **loser** card:
- [ ] A composite score (numeric) replaces the Selected badge
- [ ] "Lost on `<dim>`: ..." line shows the worst-dim delta and the
      loser's rationale for that dimension
- [ ] Evidence expander renders the same shape as the winner

Legacy session (any pre-PI session):
- [ ] "Legacy scoring (pre-2026-05-15)" italic badge sits above the
      grid
- [ ] Cards show the old `attr / coh / composite` line — no Evidence
      expander

Video session (§3 output):
- [ ] VariantsPanel renders (the previous `!isVideo` guard is gone)
- [ ] The placeholder shows `🎬` when no thumbnail is available

---

## 5 — Cost Reconciliation

```
.venv/bin/python - <<'PY'
import glob
from evaluate.cost_reporter import compute_session_cost_usd
latest = max(glob.glob('data/sessions/sess_*/ledger.jsonl'))
print(f'total: ${compute_session_cost_usd(latest):.4f}')
PY
```

- [ ] Returned total is non-zero, matches the dashboard Token Economics
      panel within ±$0.01
- [ ] Per-ad Cost panel still renders (PH-02 CostAttributor unchanged)

---

## 6 — Calibration (optional, requires populated fixtures)

```
.venv/bin/python -m pytest tests/test_evaluation/test_media_quality_calibration.py -v
```

If `tests/test_evaluation/fixtures/media_quality/{images,videos}/` is
empty (the default), the API-bound tests skip and only the YAML sanity
test runs.

- [ ] `test_calibration_annotations_well_formed` PASSES (always)
- [ ] When fixtures are populated AND `GEMINI_API_KEY` is set:
      - [ ] `test_image_calibration_spread_and_tier_separation` PASSES
      - [ ] `test_video_calibration_spread_and_tier_separation` PASSES

---

## 7 — Rollback Plan

If §2/§3 produce fewer than 8 distinct composites OR the dashboard
fails to render rationales, revert the PI series:

```
git tag pre-PI-rollback HEAD
git revert ce97d74 0131427 d50b22c 55038f7 7959bec a896b7f c02c4ff eefbf33
```

The legacy event classes (`ImageEvaluated`, `VideoEvaluated`, …) were
deliberately preserved in `iterate/ledger_events.py` so old sessions
keep parsing across both the v2 dashboard and any reverted state.

---

## Findings

_Log anomalies, surprises, or deferred work here._

| Date | Step | Severity | Note |
|---|---|---|---|
|  |  |  |  |
