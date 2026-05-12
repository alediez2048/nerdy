# PH Phase — Manual Test Runbook

**Purpose:** Manually exercise the app end-to-end after the PH phase
refactor (PH-01 through PH-06, excluding deferred PH-05) to confirm
nothing broke before the production deploy.

**Branch under test:** `final-submission` (at `9f733c5` or later)
**Baseline for comparison:** `main` (at `6327c77` — pre-PH code)

**Estimated time:** ~60 minutes for the full pass.

---

## How to Use This Runbook

Run from top to bottom. Tick each `[ ]` once verified. If something
fails: stop, capture the symptom in the **Findings** section at the
bottom, and decide whether it blocks the deploy.

The phase touched **internals only** — every section below is
verifying that user-visible behavior is unchanged from `main`. Most
items should match what you saw last week.

---

## 0 — Local Environment Up

Confirm the local stack is running before any UI checks.

- [ ] `docker compose ps` — `nerdy-db-1` and `nerdy-redis-1` both
      report `healthy`
- [ ] API responds: `curl -fsS http://localhost:8000/health` returns
      `{"status":"ok"}`
- [ ] Worker is connected: `tail -5 logs/worker.log` shows
      `celery@... ready` and `Connected to redis://localhost:6380/0`
- [ ] Frontend responds: `curl -fsS -o /dev/null -w "%{http_code}\n"
      http://localhost:5173/` → `200`
- [ ] Browser opens `http://localhost:5173/` without console errors

If any of these fail, fix the environment before continuing. The runbook
won't work without all four services up.

---

## 1 — Authentication (Clerk)

Confirm PH didn't break the auth wall that PG-01..PG-07 installed.

- [ ] Open the app in an **incognito window** — you should see the
      Clerk sign-in card, centered on both desktop and mobile widths
- [ ] Sign in with a known account
- [ ] After sign-in, you land on the campaigns / sessions view (NOT a
      404 or blank page)
- [ ] Hit `http://localhost:8000/api/sessions` directly in the browser
      (no auth header) → expect a **401**, not 200. (If 200, the auth
      wall is open — DO NOT deploy.)

---

## 2 — Campaign & Session UI

PH didn't touch campaign / session CRUD, but they're the main
navigation surface — confirm nothing broke.

- [ ] Click into an existing campaign — page renders with its
      session list
- [ ] Roll-up stats on the campaign card show non-zero values for
      a campaign that has completed sessions
- [ ] Create a **new campaign** — the form submits, shows up in the
      list immediately
- [ ] Open the new campaign — "create session" CTA is visible
- [ ] Pre-fill behavior: when you start a new session from a
      campaign with defaults, fields are pre-populated (persona,
      audience, etc.)

---

## 3 — Pipeline Run (Copy-Only, Smallest Path)

This is the cheapest end-to-end test — no images, no videos, ~3 ads.
Verifies the orchestrator (PH-03) + composite evaluator (PH-04) work
in production-like flow.

- [ ] Create a new session: **copy-only**, **3 ads**, persona of your
      choice, real API keys in `.env`
- [ ] Click run / submit
- [ ] **Watch the live progress view** — you should see:
  - `batch_start` event appear immediately
  - Progress messages mention `ads_generated`, `ads_published`,
    `current_score_avg`, `cost_so_far`
  - `batch_complete` then `pipeline_complete`
  - **No JavaScript console errors** in the browser
- [ ] Session shows as **complete** in the session list within ~2
      minutes
- [ ] Cost-so-far value is a positive USD number; matches roughly
      what a 3-ad text run usually costs ($0.01–$0.10 range)

If the progress view is blank or shows JSON parse errors, the SSE
payload has drifted from what the frontend expects. STOP — investigate
before deploying.

---

## 4 — Pipeline Run (Full Image)

More expensive, but exercises the image pipeline and PH-06's model
router.

- [ ] Create a new session: **image-enabled**, **3 ads**, default
      persona
- [ ] Run it
- [ ] In the live progress view, confirm at least one ad reaches
      `ads_published` status (not all discarded)
- [ ] Open the session detail page when complete — Ad Library tab
      shows actual generated images, not broken placeholders
- [ ] Click into one published ad — image preview renders; copy
      text + headline + description + CTA are all populated
- [ ] No browser-console errors when scrolling the Ad Library

---

## 5 — Pipeline Run (Video) — OPTIONAL

Only if you want a deeper check. Video pipeline was NOT migrated to
PH-03's orchestrator (different orchestration shape), so this is
verifying it still works alongside.

- [ ] Create a video session: 1 ad, persona of your choice
- [ ] Run it
- [ ] Progress view shows video-specific events
      (`video_pipeline_start`, `video_generating`, `video_evaluating`,
      `video_pipeline_complete`)
- [ ] When done, Ad Library shows a playable video clip
- [ ] Cost for the session is non-zero and shows in the dashboard

---

## 6 — Dashboard Panels

PH-02 added new fields to the dashboard's JSON response. Frontend
doesn't read them yet, but old fields must still be there.

- [ ] **Hero KPIs:** total ads, publish rate, avg score, cost —
      all render with numbers (no `NaN`, no blanks)
- [ ] **Iteration Cycles:** the before/after cards render for at
      least one regenerated ad
- [ ] **Quality Trends:** chart loads, doesn't show an empty axis
- [ ] **Dimension Deep-Dive:** all 5 dimensions appear; correlation
      heatmap renders
- [ ] **Ad Library:** filter by status / persona works; scores
      render; clicking an ad expands its rationales
- [ ] **Token Economics:** total cost matches the Hero KPI cost;
      per-model breakdown renders
- [ ] **System Health:** SPC chart renders without errors
- [ ] **Competitive Intel:** hook distribution chart loads

If any panel shows JSON parse errors or `undefined` fields, the API
response shape changed unexpectedly. Capture the panel name + the
response in Findings.

---

## 7 — Cost Numbers (Specific to PH-02)

The cost displayed should be IDENTICAL to what it was before PH-02.

- [ ] Pick a session that completed BEFORE the PH phase started
- [ ] Note the cost shown on its dashboard summary (e.g. `$7.12`)
- [ ] Reload the page — same number
- [ ] In a terminal: `curl -fsS http://localhost:8000/api/sessions/<id>/summary -H "Authorization: Bearer ..."`
- [ ] Confirm the JSON response includes both the legacy fields
      AND the new PH-02 fields:
  - `total_cost_usd` ✅ (was there before)
  - `cost_source` ✅ (was there before)
  - `cost_confidence` 🆕 (new — high/medium/low)
  - `cost_breakdown.text_usd`, `image_usd`, `video_usd` 🆕 (new)
- [ ] **Sanity check:** `text_usd + image_usd + video_usd` should be
      ≤ `total_cost_usd` (breakdown sums to total when source is
      `ledger`; less when source is `manifest_estimate`)

---

## 8 — Ledger Integrity (Specific to PH-01)

The ledger JSONL file format must be unchanged.

- [ ] `wc -l data/ledger.jsonl` — non-zero number
- [ ] `tail -1 data/ledger.jsonl | python3 -m json.tool` — last
      entry parses as valid JSON
- [ ] Run this one-liner — should print `OK`:
      ```
      python3 -c "
      from iterate.ledger_reader import read_typed_events
      from iterate.ledger_events import LedgerEvent
      evs = read_typed_events('data/ledger.jsonl')
      unknown = sum(1 for e in evs if type(e) is LedgerEvent)
      assert unknown == 0, f'{unknown} unknown event types'
      print(f'OK — {len(evs)} events parsed, 0 unknown')
      "
      ```
- [ ] After Step 3's copy-only run, the new ledger entries (the last
      ~10 lines) have the same top-level keys as older entries
      (`event_type`, `ad_id`, `brief_id`, `cycle_number`, `action`,
      `tokens_consumed`, `model_used`, `seed`, `inputs`, `outputs`,
      `timestamp`, `checkpoint_id`)

---

## 9 — Curation Flow

Verifies the curation routes that touch the cost attributor (PH-02).

- [ ] Open a completed session's Ad Library
- [ ] Curate an ad (the favourite / star action)
- [ ] Curated set updates immediately
- [ ] Reorder a curated ad (drag-and-drop or controls)
- [ ] Export the curated set as CSV — download starts; the file has
      a `total_cost_usd` column with non-zero values

---

## 10 — Share Link

Lightweight regression check — share tokens were touched by PG-02.

- [ ] Generate a share link for a session
- [ ] Open the share link in an **incognito window** (no auth)
- [ ] Public read view renders the session's curated ads
- [ ] Logged-out users **cannot** edit or curate

---

## 11 — Performance Smoke

PH-03 absorbed cost-so-far / avg-score computation per batch. These
add a few extra ledger reads per batch boundary. Verify it doesn't
balloon batch time.

- [ ] Time a 3-ad copy-only run (Step 3): from "create session" to
      "session complete" should be **under 60 seconds** with a warm
      cache
- [ ] If it's over 2 minutes, investigate before deploying — the
      added cost-so-far / avg-score reads might be slower than
      expected on large session ledgers

---

## 12 — Rollback Drill (Optional but Recommended)

Confirm we can roll back if something goes wrong post-deploy.

- [ ] `git log --oneline -1 main` → shows `6327c77` (pre-PH baseline)
- [ ] If problems appear after deploy:
      `git checkout main && git reset --hard 6327c77 && git push origin main --force`
      would revert. (Don't do it — just confirm the SHA is right.)
- [ ] Suggest: tag the rollback target now —
      `git tag pre-PH 6327c77 && git push origin pre-PH`

---

## Findings

Use this section to capture anything that didn't pass cleanly.

| # | Section | Symptom | Severity | Notes |
|---|---------|---------|----------|-------|
|   |         |         |          |       |

**Severity guide:**
- **Blocker** — must fix before merging to `main`
- **Watch** — won't block deploy but track post-deploy
- **Cosmetic** — file a follow-up ticket, deploy anyway

---

## Sign-off

- [ ] All `[ ]` checkboxes ticked
- [ ] No Blocker-severity items in Findings
- [ ] Secrets rotated (5 keys flagged from 2026-05-01 prod recovery)
- [ ] `VITE_CLERK_PUBLISHABLE_KEY` confirmed on Vercel
- [ ] `pre-PH` tag pushed to origin

**Ready to deploy:** `_____________` (your name + date)

After sign-off:
```
git checkout main
git merge --no-ff final-submission -m "Merge PH phase (PH-01..PH-04, PH-06, PH-07) into main"
git push origin main
```

Then watch Railway + Vercel auto-redeploys; smoke-check production
`/health` and the sign-in flow.
