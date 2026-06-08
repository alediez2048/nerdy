# PJ-13 Primer

**Source plan:** [`PJ-00-phase-plan.md`](PJ-00-phase-plan.md) — §15 (Success criteria) and §13 (PJ-13 row).
**For:** New Cursor Agent session
**Date:** 2026-06-08
**Previous work:** PJ-01..PJ-12 all merged. See `docs/development/DEVLOG.md`.
**Status:** ⏳ Not started

---

# Ticket PJ-13: Verification gate

## What Is This Ticket?

The phase isn't done until somebody confirms it works end-to-end on a real stack with real users. PJ-13 mirrors PI-11 and PH-07: lint clean, full pytest, `npm run build` clean, plus a **manual runbook** that walks the full PJ flow on a fresh Clerk account: sign-in → onboarding → first session → post-session reflection → pre-session prep → next session.

This ticket produces:

1. The runbook itself (`docs/development/PJ-MANUAL-TEST-RUNBOOK.md`).
2. A DEVLOG entry showing the runbook executed cleanly.
3. The "two industries diverge" verification from success criterion §15.2.
4. The cross-tenant isolation test from §15.4 / risk §14.5.
5. The merge-to-main checklist (gated by the production deploy gate in CLAUDE.md Project State).

No code changes (other than fixing anything the runbook surfaces).

### Why It Matters

- It's the gate between "we wrote a phase" and "we shipped a phase."
- Documents the manual procedure future agents use to verify prod deploys.
- Captures the "two industries produce materially different conversations" success criterion as a concrete artifact (transcripts saved).

---

## What Was Already Done

- **PJ-01..PJ-12** — all implementation and docs.
- `docs/development/PI-MANUAL-TEST-RUNBOOK.md` and `PH-MANUAL-TEST-RUNBOOK.md` — format precedents to mirror.
- CLAUDE.md Project State "Production deploy gate" — the secrets-rotation + Clerk env vars block that must precede `final-submission → main`.

---

## What This Ticket Must Accomplish

### Goal

Manual end-to-end runbook executed cleanly, automated checks green, two-industry divergence captured, cross-tenant isolation proven. DEVLOG entry summarizes results.

### Deliverables Checklist

#### A. Automated check baseline

- [ ] **Step A1** — Lint clean:
  ```
  .venv/bin/python -m ruff check .
  ```
- [ ] **Step A2** — Full pytest:
  ```
  .venv/bin/python -m pytest tests/ --tb=short -q
  ```
  Record pass/fail counts; confirm no PJ regressions vs. pre-PJ baseline.
- [ ] **Step A3** — Frontend build:
  ```
  cd app/frontend && npm run build 2>&1 | tail -20
  ```
- [ ] **Step A4** — Frontend type check:
  ```
  cd app/frontend && npx tsc --noEmit
  ```
- [ ] **Step A5** — Playwright suite:
  ```
  cd app/frontend && npm run test:e2e
  ```
  Confirm `onboarding.spec.ts`, `settings_brand_profile.spec.ts`, `post_session_reflection.spec.ts`, `pre_session_prep.spec.ts` all pass.

#### B. Manual runbook (write + execute)

- [ ] **Write** `docs/development/PJ-MANUAL-TEST-RUNBOOK.md` mirroring `PI-MANUAL-TEST-RUNBOOK.md`. Sections below.
- [ ] **Execute** every step against the local docker-compose stack with a freshly created Clerk test user.

Runbook sections:

1. **Stack startup** — `docker compose up -d`, `cd app/frontend && npm run dev`, confirm 4 containers + vite up.
2. **Onboarding wall** — sign in as fresh test user; verify auto-redirect to `/onboarding`.
3. **Phase 1 — Identify** — type business name + industry; confirm `save_field` writes; phase advances.
4. **Phase 2 — Core** — fill audience/mission/value_props/tone; confirm gate validation on `mark_good_enough` rejects early attempts.
5. **Phase 3 — Extras (industry divergence)** — run TWO accounts in parallel (or sequentially), one set to `tutoring`, one to `restaurant`. Capture both Phase 3 transcripts and diff. Expected: distinctly different question content (subjects_taught vs. cuisine_style etc.). Save both transcripts as artifacts in `docs/development/PJ-13-evidence/`.
6. **Phase 4 — Assets** — drop a real logo PNG; wait for vision pass; confirm palette + fonts surface; accept them.
7. **Phase 5 — Good-enough** — confirm summary, `mark_good_enough` succeeds; redirected to `/sessions`.
8. **Session create gate (negative)** — manually `UPDATE brand_profile SET good_enough_at = NULL WHERE user_id = ...` in Postgres; attempt `POST /api/sessions`; confirm 403 `brand_profile_not_ready`; UI redirects to `/onboarding`. Restore `good_enough_at`.
9. **Pre-session prep** — click Create Session; confirm modal opens with brief draft anchored in profile; accept; confirm form pre-fills.
10. **Pipeline run** — submit form; pipeline runs to completion. Manual inspection: at least one generated ad references the user's mission or a value prop verbatim or near-verbatim.
11. **Post-session reflection** — auto-open modal on completion; accept a suggestion; confirm DB write to `extras`.
12. **Next-session feedback loop** — create a second session; confirm brief expansion incorporates the new `extras` key (inspect ledger or expanded brief log).
13. **Cross-tenant isolation** — sign in as user B; confirm impossible to GET user A's `brand_profile` (`/api/me/brand-profile` returns only user B's row); confirm impossible to GET user A's `brand_asset` (404). Attempted Postgres query to confirm `user_id` scoping in every relevant query.
14. **Settings refine** — click Refine your brand; modal opens; update a typed field; close; card reflects change.
15. **Two-industry divergence proof** — diff the saved Phase 3 transcripts side-by-side in the runbook artifact section.

#### C. DEVLOG entry

- [ ] Append `## 2026-XX-YY — PJ-13: Phase verification gate (✅)` to top of `docs/development/DEVLOG.md`. Include the result table below.

Result table format:

```markdown
| Check | Result |
|---|---|
| ruff | clean |
| pytest | <N> passed, zero PJ regressions |
| frontend build | clean |
| tsc --noEmit | clean |
| Playwright suite | <N>/<N> passing |
| Onboarding wall (fresh user) | redirect to /onboarding confirmed |
| Phase advance through 5 phases | all phases written, gates enforced |
| Industry divergence (tutoring vs restaurant) | <N>-char delta in Phase 3 transcripts (saved) |
| Asset vision pass | palette + fonts extracted, user-confirmed |
| Session gate (negative test) | 403 brand_profile_not_ready confirmed |
| Pre-session prep | brief draft → form pre-fill confirmed |
| Pipeline references brand profile | <ad excerpt> mentions <mission keyword> |
| Post-session reflection writes extras | extras["..."] = <value> written |
| Next-session brief picks up extras | <ledger excerpt> references new key |
| Cross-tenant isolation | user B cannot read user A's profile/assets |
```

#### D. Production deploy gate review

- [ ] Re-read CLAUDE.md "Production deploy gate" section.
- [ ] Confirm with the user that the secrets-rotation TODO and Clerk env-var TODO are satisfied before any `final-submission → main` merge. Refuse to merge if either is unconfirmed.
- [ ] Tag the pre-PJ SHA for rollback: `git tag pre-PJ-deploy <main-sha>`.
- [ ] If gates pass, document the merge command in the DEVLOG entry but do NOT execute without explicit user go-ahead.

---

## Branch & Merge Workflow

```bash
git switch final-submission && git pull
git switch -c feature/PJ-13-verification-gate
# write runbook, execute, capture artifacts, write DEVLOG
git add docs/development/PJ-MANUAL-TEST-RUNBOOK.md docs/development/PJ-13-evidence/ docs/development/DEVLOG.md
git commit -m "docs(PJ-13): phase verification gate — manual runbook + evidence"
git push -u origin feature/PJ-13-verification-gate
```

Production merge (only after deploy gate confirmed):

```bash
git switch final-submission && git merge --no-ff feature/PJ-13-verification-gate
git tag pre-PJ-deploy <prev-main-sha>
git switch main && git merge --no-ff final-submission
git push origin main
```

---

## Important Context

### Files to Create

| File | Why |
|------|-----|
| `docs/development/PJ-MANUAL-TEST-RUNBOOK.md` | Step-by-step end-to-end manual test |
| `docs/development/PJ-13-evidence/` | Phase 3 transcripts, screenshots, ledger excerpts |

### Files to Modify

| File | Action |
|------|--------|
| `docs/development/DEVLOG.md` | Prepend PJ-13 entry |

### Files to NOT Modify

- Any code under `app/`, `generate/`, `iterate/`, `evaluate/`, `tests/`. If the runbook surfaces a bug, file a follow-up; do not patch in this ticket.

### Files to READ for Context

| File | Why |
|------|-----|
| `docs/development/PI-MANUAL-TEST-RUNBOOK.md` | Format precedent |
| `docs/development/PH-MANUAL-TEST-RUNBOOK.md` | Older precedent — different but useful |
| `docs/development/tickets/PJ-00-phase-plan.md` §15 | Success criteria checklist |
| `CLAUDE.md` Project State "Production deploy gate" | Pre-merge requirements |

---

## Architectural Decisions

| Decision | Reference | Summary |
|----------|-----------|---------|
| Manual runbook is the gate | PJ-00 §15.8 | Automated tests + manual end-to-end together prove the phase |
| Evidence captured to docs/ | PJ-13 convention | Future verifications can diff against today's transcripts |
| Cross-tenant isolation explicitly tested | PJ-00 §14.5 risk | Risk #5 mitigation lives here |
| No code changes in PJ-13 | scope discipline | Bug → file follow-up ticket, not patch in the gate |

---

## Suggested Implementation Pattern

### Two-industry divergence capture

The cleanest way to capture is to run the same opening Phase 3 prompt under two different `brand_profile.industry` values and save both transcripts. Suggested:

```bash
# Create two test users via Clerk (or seed two BrandProfile rows manually).
# For each, advance to phase=extras.

# Then via the API directly (skipping UI for reproducibility):
curl -X POST http://localhost:8000/api/agent/converse \
  -H "Authorization: Bearer $TUTORING_USER_JWT" \
  -d '{"touchpoint":"onboarding","user_message":"ready for phase 3"}' \
  > docs/development/PJ-13-evidence/phase3_tutoring.json

curl -X POST http://localhost:8000/api/agent/converse \
  -H "Authorization: Bearer $RESTAURANT_USER_JWT" \
  -d '{"touchpoint":"onboarding","user_message":"ready for phase 3"}' \
  > docs/development/PJ-13-evidence/phase3_restaurant.json

# Diff the assistant_message + the next 2 turns:
diff <(jq -r '.assistant_message' docs/development/PJ-13-evidence/phase3_tutoring.json) \
     <(jq -r '.assistant_message' docs/development/PJ-13-evidence/phase3_restaurant.json)
```

Expected: substantial differences in question content (subjects vs. cuisine, grade levels vs. ambiance, etc.). The diff itself goes into the DEVLOG entry as evidence.

### Cross-tenant isolation script

```bash
# As user A, upload an asset:
curl -X POST -H "Authorization: Bearer $A_JWT" -F file=@logo.png -F asset_type=logo \
  http://localhost:8000/api/brand-assets
# Capture asset_id from response: $ASSET_A

# As user B, try to GET it:
curl -H "Authorization: Bearer $B_JWT" \
  http://localhost:8000/api/brand-assets/$ASSET_A
# Expected: 404

# As user B, try to converse referencing user A's asset:
curl -X POST -H "Authorization: Bearer $B_JWT" \
  -d "{\"touchpoint\":\"onboarding\",\"uploaded_asset_ids\":[\"$ASSET_A\"]}" \
  http://localhost:8000/api/agent/converse
# Expected: asset reference rejected by ingest_asset's user_id scope check.
```

### Next-session feedback-loop proof

After Phase 11 of the runbook (reflection writes an extras key), inspect the expanded brief during the next session run. Suggested:

```python
import json, glob
latest = max(glob.glob('data/sessions/sess_*/ledger.jsonl'))
events = [json.loads(l) for l in open(latest)]
brief_events = [e for e in events if e.get('event_type') == 'BriefExpanded']
assert brief_events
expanded = brief_events[-1]['outputs']
assert "<the key written by reflection>" in str(expanded), "feedback loop not closed"
```

---

## Edge Cases to Handle

1. Vision pass returns wrong palette — runbook still passes if user manually corrects via chat; document the user-fallback path worked.
2. Phase 3 industry divergence test inconclusive (LLM happens to ask similar generic questions) — re-run with explicit seed messages forcing the industry framing; document the seed.
3. Cross-tenant isolation test reveals a leak — STOP the gate, file a critical bug, do not merge to main until fixed.
4. Backfill migration not yet executed against the local dev DB — runbook should call it out and run it as Step 0.
5. Production deploy gate items unsatisfied — DEVLOG entry should explicitly note the merge is BLOCKED, not done.
6. Two test users on the same Clerk dev instance — confirm Clerk allows this; otherwise use the DEV_MODE bypass.

---

## Definition of Done

- [ ] All Step A automated checks green.
- [ ] Runbook executed end-to-end on a fresh Clerk user account.
- [ ] Two-industry divergence transcripts saved to `PJ-13-evidence/`.
- [ ] Cross-tenant isolation test confirmed.
- [ ] Next-session feedback loop confirmed via ledger inspection.
- [ ] All §15 success criteria from PJ-00 explicitly checked off in the DEVLOG entry.
- [ ] Production deploy gate items in CLAUDE.md re-verified with the user before any merge to main.
- [ ] DEVLOG entry prepended.
- [ ] Feature branch pushed.

---

## Estimated Time

| Task | Estimate |
|------|----------|
| Read PI-11 + PH-07 runbooks for format | 30 min |
| Write PJ-MANUAL-TEST-RUNBOOK.md skeleton | 90 min |
| Execute Steps A1–A5 (automated checks) | 30 min |
| Execute manual runbook (Steps 1–15) | 180 min |
| Capture artifacts (transcripts, screenshots, ledger excerpts) | 60 min |
| Two-industry divergence + cross-tenant test | 60 min |
| DEVLOG entry with full result table | 60 min |
| Review production deploy gate with user | 15 min |
| **Total** | **~1 day** |

---

## After This Ticket: What Comes Next

- Pending the production deploy gate items (CLAUDE.md), merge `final-submission → main` and tag.
- PJ phase officially closed on `main`.
- Next phase (PK or later) — competitive intel refresh, persistent chat widget, brand voice critic, etc. (PJ-00 §2 non-goals).
