# PJ-12 Primer

**Source plan:** [`PJ-00-phase-plan.md`](PJ-00-phase-plan.md) — §12 (Documentation refresh).
**For:** New Cursor Agent session
**Date:** 2026-06-08
**Previous work:** PJ-01..PJ-11 (or as many as have landed). Doc refresh can run in parallel with late tickets. See `docs/development/DEVLOG.md`.
**Status:** ⏳ Not started

---

# Ticket PJ-12: Documentation refresh

## What Is This Ticket?

PJ meaningfully changes the platform's narrative — from single-tenant Varsity-flavored to multi-tenant brand-aware. Every reference doc, every deliverable, every onboarding-style file that today describes the platform-as-tutoring-tool has to be refreshed. Per PJ-00 §12 this is **acceptance criteria, not polish**: a doc still claiming the platform reads `brand_knowledge.json` after PJ ships is a regression.

This ticket is a single focused pass through the 12 documents in §12, structured as a parallelizable checklist. Some are major rewrites (prd.md, requirements.md, systemsdesign.md, demo-script.md), some are surgical edits (PRODUCTION.md, ENVIRONMENT.md), some are append-only (decisionlog.md, ai-tools.md, CLAUDE.md project state).

### Why It Matters

- Future agents (and humans) read these docs to understand the system. Stale docs cause architectural confusion at scale.
- demo-script.md is the public-facing storyline; restructuring it around onboarding is the user-visible payoff.
- Doc completeness is in §15.6 of the success criteria: "no doc references `brand_knowledge.json`."

---

## What Was Already Done

- **PJ-01..PJ-11** — all the substantive code; this ticket only documents what landed.
- DEVLOG entries already exist per ticket (each PJ ticket prepends one). PJ-12 doesn't re-DEVLOG individual tickets — it adds its own entry summarizing the doc pass.

---

## What This Ticket Must Accomplish

### Goal

Bring every document listed in PJ-00 §12 into alignment with the multi-tenant brand-aware architecture. Zero references to `brand_knowledge.json` remain. Demo script re-anchored on onboarding.

### Deliverables Checklist

#### A. Major rewrites

- [ ] **`docs/reference/prd.md`**:
  - Strip the "Varsity Tutors ad generator" framing.
  - Re-introduce as "multi-tenant brand-aware ad platform with an onboarding agent."
  - Add a "Multi-tenant brand context" section describing `brand_profile` + the 4 touchpoints.
  - Remove tutoring-specific personas and audiences from the user stories; rewrite as industry-agnostic.
  - Add the BYO API Keys + brand profile dual gate explicitly.

- [ ] **`docs/reference/requirements.md`**:
  - Drop Varsity-specific functional requirements.
  - Add functional requirements for: onboarding agent, brand profile (typed+extras), asset upload + vision pass, 4 touchpoints, per-user pipeline read.
  - Add non-functional requirements: agent turn p95 ≤ 8s; vision pass ≤ 25s async; cross-tenant data isolation.

- [ ] **`docs/deliverables/systemsdesign.md`**:
  - Update the systems diagram (or add a new "Agent + Brand Profile Layer" diagram).
  - Update narrative to describe the 4 touchpoints, the per-user pipeline read, asset storage on Railway volume.
  - Reference PJ-00 §4 for the architecture block.

- [ ] **`docs/deliverables/demo-script.md`**:
  - **Restructure entirely**: onboarding is now the front-door demo step.
  - New scene order:
    1. Sign-in (fresh user) → automatic `/onboarding` redirect.
    2. Walk through 5 phases live; drop a logo; show palette extraction.
    3. Land on `/sessions`; show the unlocked Create Session button.
    4. Pre-session prep modal proposes brief; accept; form pre-fills.
    5. Pipeline runs; show variants in dashboard.
    6. Session detail page → post-session reflection modal auto-opens; user accepts a suggestion.
    7. Next session: show the brief expansion picking up the new `extras` key.

#### B. Moderate edits

- [ ] **`docs/reference/PRODUCTION.md`**:
  - Add the 3 new tables to the schema section: `brand_profile`, `conversation_messages`, `brand_assets`.
  - Add the new endpoints: `/api/agent/converse`, `/api/brand-assets`, `/api/me/brand-profile`.
  - Add the new env var `AGENT_GEMINI_API_KEY`.
  - Add the new `/onboarding` Vite route to the Vercel deploy section.
  - Document the `output/brand_assets/` Railway volume path.

- [ ] **`docs/reference/ENVIRONMENT.md`**:
  - Add `AGENT_GEMINI_API_KEY` to required env vars (host-side, NOT BYO).
  - Mention the Gemini function-calling + multimodal model used (`gemini-2.5-flash`).
  - Note local dev needs the Celery worker running for vision pass (`docker compose up worker` or equivalent).
  - Add the backfill script command for migrating existing users (`python scripts/migrations/PJ_backfill_brand_profile.py`).

- [ ] **`docs/deliverables/model_orchestration.md`**:
  - Add a "Gemini function-calling loop" section alongside the existing brief/generation/eval orchestration patterns.
  - Document the `MAX_TOOL_ITERATIONS = 8` bound.
  - Document the AGENT key vs BYO key split.

- [ ] **`docs/deliverables/feedback_loop_architecture.md`**:
  - Add a section on the post-session reflection touchpoint alongside the quality ratchet (PI) and regen loop.
  - Diagram: session completes → ledger summary → reflection touchpoint → `extras` write → next-session brief expansion picks it up.

- [ ] **`docs/deliverables/writeup.md`**:
  - Reflect the multi-tenant + agent product story.
  - The "what does it do" section now includes "learns and remembers your brand."

#### C. Minor edits

- [ ] **`docs/deliverables/decisionlog.md`**:
  - Add a new dated entry capturing the 16 decisions from PJ-00 §3 (including the 6 GRILL decisions, with explicit Q-numbers).

- [ ] **`docs/deliverables/ai-tools.md`**:
  - Note the agent uses Gemini function-calling for tool dispatch.
  - Note the vision pass uses Gemini multimodal.
  - Mention the host-paid `AGENT_GEMINI_API_KEY` vs BYO model.

- [ ] **`CLAUDE.md` and `AGENTS.md` Project State section**:
  - Add PJ to the phase history.
  - Add a ticket status table (PJ-01..PJ-13) modeled after the PI table.
  - Mark phase as complete (assuming PJ-12 is the last-but-PJ-13 doc pass).
  - Both files are gitignored but hand-mirrored — update both identically.

#### D. Verification + DEVLOG

- [ ] `grep -r "brand_knowledge.json" docs/` returns no matches.
- [ ] `grep -r "Varsity" docs/` only matches in historical sections (e.g., DEVLOG entries, backfill discussion) — not in current-state prose.
- [ ] Add DEVLOG entry: `## 2026-XX-YY — PJ-12: Documentation refresh (✅)` with bullet list of docs touched and a one-line summary per major rewrite.

---

## Branch & Merge Workflow

```bash
git switch final-submission && git pull
git switch -c feature/PJ-12-doc-refresh
# edit docs
git add docs/ CLAUDE.md AGENTS.md
git commit -m "docs(PJ-12): refresh docs for multi-tenant brand profile + onboarding agent"
git push -u origin feature/PJ-12-doc-refresh
```

---

## Important Context

### Files to Modify

| Severity | File | Brief |
|---|---|---|
| Major | `docs/reference/prd.md` | Re-frame from single-tenant to multi-tenant |
| Major | `docs/reference/requirements.md` | New functional + non-functional requirements |
| Major | `docs/deliverables/systemsdesign.md` | Add agent layer + brand profile + asset storage |
| Major | `docs/deliverables/demo-script.md` | Restructure around onboarding |
| Moderate | `docs/reference/PRODUCTION.md` | New tables, endpoints, env vars, routes |
| Moderate | `docs/reference/ENVIRONMENT.md` | `AGENT_GEMINI_API_KEY`, Celery worker, backfill |
| Moderate | `docs/deliverables/model_orchestration.md` | Function-calling loop pattern |
| Moderate | `docs/deliverables/feedback_loop_architecture.md` | Post-session reflection loop |
| Moderate | `docs/deliverables/writeup.md` | Product story |
| Minor | `docs/deliverables/decisionlog.md` | 16 PJ decisions logged |
| Minor | `docs/deliverables/ai-tools.md` | Gemini function-calling + multimodal note |
| Minor | `CLAUDE.md`, `AGENTS.md` | Project State section (PJ phase + ticket table) |

### Files to NOT Modify

- `docs/development/tickets/PJ-*.md` — phase plan + primers are frozen.
- `docs/development/DEVLOG.md` — only append PJ-12's own entry; don't rewrite prior PJ entries.

### Files to READ for Context

| File | Why |
|------|-----|
| `docs/development/tickets/PJ-00-phase-plan.md` | The source of truth — copy concepts faithfully |
| All PJ-XX-primer.md | Per-ticket decisions to fold into the docs |
| Existing `docs/deliverables/demo-script.md` | Voice/format to preserve |
| Existing `docs/reference/prd.md` | Sections to keep vs. replace |

---

## Architectural Decisions

| Decision | Reference | Summary |
|----------|-----------|---------|
| Doc updates are acceptance criteria | PJ-00 §12 intro | Not optional; gates phase completion |
| `brand_knowledge.json` mentions must vanish | PJ-00 §15.6 | Success criterion |
| `CLAUDE.md`/`AGENTS.md` hand-mirrored | CLAUDE.md note | Both gitignored; both edited identically |
| Industries as prompt content, not docs | PJ-00 §3 decision 9 | Doc mentions industries by name only as examples |

---

## Suggested Implementation Pattern

This ticket is editing-heavy, not coding. Suggested workflow:

1. **Pass 1 — read every doc on the list.** Take notes on what each currently says about the platform's tenancy model.
2. **Pass 2 — major rewrites first.** prd.md and demo-script.md set the narrative; the rest borrows phrasing from them.
3. **Pass 3 — moderate edits.** Surgical: find the schema/endpoint/env-var sections, add the new entries. Don't rewrite surrounding prose.
4. **Pass 4 — minor edits and CLAUDE.md/AGENTS.md mirror update.**
5. **Pass 5 — grep verification.** `brand_knowledge.json` gone; `Varsity` only in historical context.
6. **Pass 6 — DEVLOG entry.**

For the decision log entry, suggested format:

```markdown
## 2026-06-XX — PJ phase decisions

Sixteen load-bearing decisions made during the PJ phase (multi-tenant brand profile + onboarding agent). Captured to prevent re-litigation.

1. Onboarding-finish model = "never done" + lightweight gate.
2. Schema = typed core + open extras (~10 columns + `extras JSONB`).
3. Touchpoints = triggered, not always-on (4 modes of one endpoint).
4. Pipeline integration = strict per-user replace; no fallback.
5. Question-selection = phased outer loop + LLM intra-phase (5 phases).
6. Assets captured in-chat with Gemini vision pass.
7. Conversation runtime = synchronous request/response.
8. Hermes Agent the framework — rejected; built in-house.
9. Industry hints = prompt content, not data files.
10. Tool whitelist enforcement is backend-side.
11. (GRILL Q1) Agent uses host-side `AGENT_GEMINI_API_KEY`; BYO still required for pipeline.
12. (GRILL Q2) `user_id` is closure-bound; never an LLM-visible argument.
13. (GRILL Q3) Existing users get a one-shot backfill, not an onboarding wall.
14. (GRILL Q4) Hybrid runtime — sync chat + async vision pass via Celery.
15. (GRILL Q5) Full 4-touchpoint scope; no MVP cut.
16. (GRILL Q6) Pre-session prep = chat THEN form; new `propose_brief` tool.
```

For the `CLAUDE.md` / `AGENTS.md` Project State update, follow the structure of the existing PI table — copy that table format, add PJ above it:

```markdown
## Active phase: PJ — Multi-Tenant Brand Profile + Onboarding Agent

Replaces `data/brand_knowledge.json` (Varsity single-tenant) with per-user
`brand_profile` rows. Adds a 5-phase onboarding agent + 3 ongoing touchpoints
that keep the profile growing as the system learns the user's brand.

**Spec:** `docs/development/tickets/PJ-00-phase-plan.md`
**Plan:** `docs/development/tickets/PJ-00-phase-plan.md` §13 (13 tickets, ~17.5d)
**Per-ticket primers:** `docs/development/tickets/PJ-NN-primer.md`

### Ticket status

| # | Ticket | State |
|---|---|---|
| PJ-01 | DB models + migration scaffold | ✅ merged |
| PJ-02 | Brand assets API + storage | ✅ merged |
| ...
| PJ-13 | Verification gate | ⏳ pending |
```

---

## Edge Cases to Handle

1. A doc references both Varsity AND multi-tenant — clarify the historical context vs. current state with explicit "(pre-PJ)" markers if needed.
2. demo-script.md may have screenshot references — note any that need re-capture in the DEVLOG; actual capture can happen in PJ-13.
3. Schema sections in PRODUCTION.md may use a specific column-list format — mimic it for the new tables to keep style consistent.
4. CLAUDE.md / AGENTS.md are gitignored — confirm both files are updated even if one git status surfaces neither.
5. ai-tools.md may already mention Gemini multimodal for the vision pipeline (PI) — add the agent usage as a distinct subsection so the two contexts aren't conflated.
6. The decision log entry should NOT duplicate the full PJ-00 §3 prose — just the one-liner per decision, with the §3 reference for full context.
7. Some doc files might not exist yet — if so, document the gap in DEVLOG and skip rather than fabricate.

---

## Definition of Done

- [ ] All 12 doc files updated per the checklist.
- [ ] `grep -r "brand_knowledge.json" docs/` returns 0 matches.
- [ ] `grep -r "Varsity" docs/` only matches in historical or migration contexts.
- [ ] CLAUDE.md and AGENTS.md Project State sections updated identically.
- [ ] decisionlog.md has the 16-decision entry.
- [ ] demo-script.md scene order matches the new onboarding-first flow.
- [ ] DEVLOG entry prepended summarizing the doc pass.
- [ ] Feature branch pushed.

---

## Estimated Time

| Task | Estimate |
|------|----------|
| Pass 1 — read every doc | 90 min |
| Major rewrite: prd.md | 90 min |
| Major rewrite: requirements.md | 60 min |
| Major rewrite: systemsdesign.md (incl. diagram) | 120 min |
| Major rewrite: demo-script.md | 120 min |
| Moderate edits (PRODUCTION, ENVIRONMENT, model_orch, feedback_loop, writeup) | 180 min |
| Minor edits (decisionlog, ai-tools) | 60 min |
| CLAUDE.md / AGENTS.md mirror | 30 min |
| Grep verification pass | 30 min |
| DEVLOG entry | 30 min |
| **Total** | **~2.5 days** |

---

## After This Ticket: What Comes Next

- **PJ-13** — Verification gate runs the demo-script against the live system to confirm docs match reality.
