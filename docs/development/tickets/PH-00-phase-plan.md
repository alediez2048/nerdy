# PH Phase Plan: Architectural Deepening — Seams, Locality & Leverage

**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** May 2026
**Previous work:** P0–P5, PA, PB, PC, PD, PF, PG complete. See `docs/development/DEVLOG.md`.
**Branch at handoff:** `feature/PH-00-phase-plan` (phase plan + primers) → per-ticket branches `feature/PH-NN-...`

---

## Problem Statement

The system shipped end-to-end (PG complete, production deployed) but accumulated architectural friction along the way. Five tightly-related symptoms recur in the DEVLOG and were independently re-surfaced by a Matt-Pocock-style "improve-codebase-architecture" audit (verified against the GitNexus knowledge graph, 8048 symbols / 15467 edges):

1. **Ledger writes are scattered.** 22 direct callers of `log_event`, 7 affected processes, 9 modules. Every schema change is a 22-file change.
2. **Cost attribution is split and divergent.** Two near-duplicate entry points (`compute_session_cost_usd`, `sum_session_display_cost_usd`) feed 8–9 different campaign + dashboard routes. The DEVLOG documents recurring cost bugs (hardcoded $0.20/ad, `tokens_consumed: 0`, video rates 3× off, display vs. true cost divergence).
3. **Pipeline orchestration is duplicated.** `iterate/batch_processor.process_batch` is called from both `run_pipeline.py` (CLI) and `app/workers/tasks/pipeline_task.py` (Celery), each reconstructing config normalization, batch counting, progress reporting.
4. **Evaluation is fragmented across 22 files.** No composite "evaluate this ad" surface — `evaluate_ad` is called directly by 14+ tests. Pure-function islands that real bugs slip between.
5. **Stage ordering is implicit.** `process_batch` is ~150 lines of linear code with hidden preconditions (expand → generate → evaluate → route → image, etc.). No type guard prevents reorder.
6. **Image-model routing is repeated.** `_call_image_api` has 4 sibling callers in `generate/image_generator.py`, each redoing budget/persona routing.

Together these violate the project's architectural pillar **"Decomposition Is the Architecture"** (systemsdesign.md §2) — but at the level of pipeline plumbing rather than ad structure.

---

## Audit Findings (GitNexus-verified)

| Symbol / area | Risk | Direct callers (d=1) | Processes affected |
|---|---|---|---|
| `iterate/ledger.py:log_event` | **CRITICAL** | 22 | 7 |
| `evaluate/cost_reporter.py:compute_session_cost_usd` | **CRITICAL** | 4 | 9 |
| `evaluate/cost_reporter.py:sum_session_display_cost_usd` | **CRITICAL** | 4 | 8 |
| `iterate/batch_processor.py:process_batch` (two entry points) | High | 2 | 2 (cross-cutting) |
| `evaluate/` directory | Fragmentation | 22 files | n/a |
| `generate/image_generator.py:_call_image_api` (4 wrappers) | Low | 4 (sibling) | 1 |

The full audit notes are in this commit; the conversation that produced them is in the agent transcript.

---

## Tickets (7)

| Ticket | Title | Priority | Dependencies | Branch |
|--------|-------|----------|--------------|--------|
| PH-01 | LedgerWriter + LedgerReader seam | Critical | None | `feature/PH-01-ledger-seam` |
| PH-02 | CostAttributor module | Critical | PH-01 | `feature/PH-02-cost-attributor` |
| PH-03 | PipelineOrchestrator — CLI ↔ Celery convergence | High | PH-01 | `feature/PH-03-orchestrator` |
| PH-04 | EvaluationPipeline composite | High | PH-01 | `feature/PH-04-eval-pipeline` |
| PH-05 | AdProcessingStage state machine | Medium | PH-04 | `feature/PH-05-stage-machine` |
| PH-06 | ImageModelRouter extraction | Low | None | `feature/PH-06-image-router` |
| PH-07 | Post-implementation verification | Gate | PH-01..PH-06 | `feature/PH-07-verification` |

**Order of implementation:** PH-01 → PH-02 → PH-03 → PH-04 → PH-05 → PH-06 → PH-07.

PH-06 is independent and can be picked off in parallel by a second agent if useful; everything else is dependency-ordered. PH-07 is the verification gate before merging anything to `main`.

---

## Architecture Decisions

These are the load-bearing decisions for the phase. Re-litigate only with explicit reason.

1. **The append-only JSONL ledger is preserved.** PH-01 refactors the *write path* and *read path* — it does NOT change the on-disk format. Decisionlog §9 ("State Is Sacred — append-only, immutable, identity-derived seeds") remains intact. The Reader produces typed views over the same JSONL bytes.
2. **No new database tables.** Cost, evaluation, and orchestration state continue to derive from the ledger. PH-02's `CostAttributor` is a pure transformer over `LedgerReader` output, not a persistence layer.
3. **Backwards compatibility for old ledgers.** Any session ledger written before PH-01 must remain readable. The Reader handles missing/optional fields gracefully (returns `None` or defaulted values).
4. **One adapter is allowed before two.** Where the audit found "shallow seam with one adapter" (e.g. VideoProvider already has `video_client.py` as a base), we do not force a second adapter. Real seam = real need.
5. **Interfaces are designed per-ticket, in a grilling session immediately before implementation.** The primers state goals, dependencies, and acceptance criteria — not interfaces. This prevents over-design and keeps the design tied to the latest state of the code.
6. **Each ticket lands behind the PH-07 verification gate before merging to `main`.** Branches merge to `final-submission`; `main` receives a single integration merge at the end of the phase (matching the PG production-deploy pattern from 2026-05-01).

---

## Risk Assessment

| Risk | Mitigation |
|------|-----------|
| Production breakage from changing 22 ledger call sites | PH-01 refactor is mechanical (each call site swaps `log_event({...dict...})` for a typed `writer.record_X(...)`). Full test suite + PH-07 e2e run. |
| Cost numbers shift visibly in the dashboard | PH-02 includes a "before/after cost diff" check on a known fixture session. Any user-visible delta is investigated, not papered over. |
| Hidden invariant broken in `process_batch` reorganization | PH-03 + PH-05 preserve the exact stage sequence; only the *call shape* changes. Golden-set tests detect score regressions. |
| Evaluator behavior subtly changes during PH-04 consolidation | All `evaluate/` modules become private *implementations* behind a composite — public behavior of `EvaluationPipeline.evaluate()` must match the existing batch_processor sequence byte-for-byte against fixture inputs. |
| Multi-day phase, partial progress on `final-submission` | Each ticket is independently shippable. If we stop after PH-02, ledger + cost are improved with no other regression. |
| Tests assume direct access to private internals | Some tests (14+ on `evaluate_ad`) bypass the planned composite. PH-04 includes a test-migration sub-task: rewrite via the public surface where possible, mark `# private-internal` where genuinely necessary. |
| GitNexus index goes stale during phase | Re-run `npx gitnexus analyze` after each merge (per CLAUDE.md). PostToolUse hook handles this automatically in Claude Code sessions. |

---

## Verification Gate Strategy

Every ticket completes the following before merging to `final-submission`:

1. `npx gitnexus impact <changed_symbol>` for every symbol touched (CLAUDE.md mandate). No HIGH/CRITICAL warnings ignored.
2. `python -m pytest tests/ -v` — full suite green (allowing the one known API-dependent failure, but no new failures).
3. `python run_pipeline.py --dry-run --max-ads 3` — CLI entry point still works.
4. `ruff check .` clean.
5. DEVLOG entry written.
6. `npx gitnexus detect_changes` (when available; otherwise `git diff --stat` review) confirms scope matches the primer's "Key Files" table.

PH-07 adds the *integration* gate before merging the phase to `main` (full multi-ad live run, dashboard render, cost reconciliation).

---

## Out of Scope

- **VideoProvider abstraction** — downgraded by the audit (`generate_video/video_client.py` already exists as a base; only one orchestrator consumer). Worth a 1-hour cleanup in a future phase, not in PH.
- **Ledger format migration** (JSONL → Parquet/Postgres) — explicitly preserved as JSONL per decision (1) above. Future phase if/when justified.
- **New features** — this phase is structural debt only. No new dimensions, providers, or evaluator types.
- **Front-end changes** — none. Dashboard reads via the same API surface; cost numbers must be unchanged.

---

## Self-Check

- All seven candidates from the architecture audit are accounted for (one downgraded, six implemented, one verification gate).
- Each ticket has a clear dependency chain and shippable scope.
- The "ledger is sacred" invariant is named and protected.
- No interface details are committed to docs — design happens in grilling, immediately before implementation.
- Test plan (PH-07) covers all surface area touched by PH-01..PH-06.
