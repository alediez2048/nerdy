# Next Agent Session — Handoff Primer

**For:** New Cursor / Claude agent session  
**Project:** Ad-Ops-Autopilot (Nerdy)  
**Last updated:** March 20, 2026  
**Branch at handoff:** `final-submission` (pushed to `origin`)

---

## 1. What Happened Last Session

A large batch of work landed on **`final-submission`** (commit **`4e10bc8`** and prior), focused on:

| Area | Summary |
|------|--------|
| **Video session cost (UI)** | `compute_session_cost_usd` / **`sum_session_display_cost_usd`**: for video, Fal **`VideoGenerated`** cost counts only the **winning** variant per ad when **`VideoSelected`** + **`winner_variant`** exist (A/B alternate excluded from *display* total). Gemini / eval events still fully counted. |
| **Video “Video ads” count** | **`pipeline_summary.videos_in_library`** — count of Ad Library rows with **`video_url` or `video_path`** (matches playable clips in the library). Overview prefers this over DB `videos_generated`. |
| **Pipeline metrics** | **`videos_generated`** = ads with ≥1 variant; **`video_variants_generated`** = Fal API jobs (anchor+alt). |
| **Per-model pricing** | `data/config.yaml`: **`video_google_veo_cost_per_call_usd`**, **`video_fal_veo3_cost_per_call_usd`**, **`video_fal_model_costs_usd`** (map). See **`evaluate/cost_reporter.py`**. |
| **Expanded Brief tab** | `app/frontend/src/tabs/ExpandedBrief.tsx` + SessionDetail tab; API **`GET /api/sessions/{id}/brief-expansions`**; empty state falls back to **session config** brief. |
| **Cost manifest** | **`data/cost_manifest.json`** + **`scripts/backfill_session_costs.py`** for historical session cost when ledger is thin. |
| **Docs** | **`docs/development/COST_TRACKING_ISSUES.md`**, **`docs/development/DEVLOG.md`** (new entry at top). |

---

## 2. Files You Should Read First

1. **`docs/development/COST_TRACKING_ISSUES.md`** — root causes, what’s fixed vs still estimated.  
2. **`evaluate/cost_reporter.py`** — `sum_session_display_cost_usd`, `_winner_variant_by_ad`, `compute_session_cost_usd`, Fal overrides.  
3. **`output/export_dashboard.py`** — `build_dashboard_data_from_events`, `videos_in_library`, `ad_library` reuse.  
4. **`app/workers/tasks/pipeline_task.py`** — `_run_video_pipeline`, `cost_so_far`, `video_variants_generated`.  
5. **`.cursor/rules/*.mdc`** — scope, git (`develop` workflow in rules vs actual branch may differ; **current work is on `final-submission`**).

---

## 3. Known Issues / Follow-Ups

### 3.1 Test suite not fully green on branch

Running a **broad** pytest slice (e.g. `tests/test_pipeline/` + `tests/test_output/` + `tests/test_generation/`) previously showed **~28 failures**, mainly:

- **`ValueError: too many values to unpack (expected 2)`** in **`tests/test_generation/test_brief_expansion.py`** and **`test_ad_generator.py`** — likely **`expand_brief` / `generate_ad` return shape** vs test expectations.

**Recommended next step:** Fix **`generate/brief_expansion.py`** (and callers) so return values match tests, or update tests if the API intentionally changed — then run **`python -m pytest tests/ -v`** from repo root with **`.venv`**.

**Green subset** (use before commits touching cost/dashboard):

```bash
.venv/bin/python3 -m pytest tests/test_pipeline/test_cost_reporter.py \
  tests/test_output/test_export_dashboard.py \
  tests/test_pipeline/test_video_evaluator.py \
  tests/test_pipeline/test_video_spec.py \
  tests/test_pipeline/test_fal_client.py -v
```

### 3.2 Cost is still *estimated*

Fal does not return USD per job in our pipeline. Display costs are **config-calibrated**. Users must tune **`data/config.yaml`** to match Fal / Google Usage dashboards.

### 3.3 `Fal jobs` showing `—` on old sessions

**`video_variants_generated`** exists only in **new** `results_summary` after pipeline changes. Older DB rows won’t have it until re-run or backfill.

---

## 4. Verification Commands (Pre-Commit)

Per workspace rules:

```bash
ruff check . --fix
.venv/bin/python3 -m pytest tests/ -v   # aim for full green after fixing generation tests
```

If full suite blocked, at minimum run the **green subset** above plus any tests for files you touched.

---

## 5. Git Workflow Note

Rules say work on **`develop`**; this handoff used **`final-submission`** for capstone delivery. Confirm with the user whether to **merge `final-submission` → `develop`** or open a PR before more work.

---

## 6. Suggested Next Tasks (Pick One)

1. **Unblock `test_generation`:** Resolve `brief_expansion` / `ad_generator` unpack failures; run full **`pytest tests/`**.  
2. **QA pass:** PF-03-style checklist — session Overview vs Ad Library counts, Token Economics **`total_cost_usd`** vs expectations.  
3. **Optional:** Backfill **`video_variants_generated`** for old sessions (script or one-off DB patch) so “Fal jobs” never shows `—`.  
4. **Decision log:** If pricing defaults change again, append **`docs/deliverables/decisionlog.md`**.

---

## 7. Quick Reference — API / Frontend

| Concern | Location |
|--------|----------|
| Session dashboard summary | `GET /api/sessions/{id}/summary` → `pipeline_summary` includes **`videos_in_library`**, **`total_cost_usd`**. |
| Brief expansions | `GET /api/sessions/{id}/brief-expansions` (`app/api/routes/sessions.py`). |
| Overview metrics | `app/frontend/src/tabs/Overview.tsx`. |
| Expanded Brief UI | `app/frontend/src/tabs/ExpandedBrief.tsx`, tab wired in **`SessionDetail.tsx`**. |

---

## 8. Do Not (Unless Ticket Says So)

- Refactor unrelated modules.  
- Hardcode USD rates outside **`data/config.yaml`** / **`MODEL_COST_RATES`**.  
- Commit **`.env`**, API keys, or large generated ledgers not meant for git.

---

*End of primer — add to DEVLOG Ticket Index if this becomes a formal ticket.*
