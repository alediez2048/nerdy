# P4-07 Primer: Narrated Pipeline Replay

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** P0–P3 complete, P4-01 through P4-06 should be done. See `docs/development/DEVLOG.md`.

---

## What Is This Ticket?

P4-07 builds a **narrated pipeline replay** — a chronological walkthrough of every decision the system made, reconstructed from the append-only ledger. Output reads like: "Batch 1: Generated 10 ads. 4 cleared threshold. 6 entered regeneration. Ad_003 failed on Brand Voice — system mutated brief — regenerated — score improved to 7.8."

### Why It Matters

- **Pillar 7: Visible Reasoning Is a First-Class Output** — The system's thinking must be legible to reviewers
- **R2-Q10:** Narrated Pipeline Replay maximizes the Documentation rubric (20% of grade)
- Failures are highlighted, not hidden — shows the system learning from mistakes
- Enables the reviewer (professor/TA) to understand decision-making without reading raw JSONL
- The replay is a key demo artifact for the project presentation (P5)

---

## What Was Already Done

- `iterate/ledger.py` — `read_events()`, `read_events_filtered()`, `get_ad_lifecycle()` for full event history
- `iterate/checkpoint.py` — `PipelineState` with `generated_ids`, `evaluated_pairs`, `published_ids`, `discarded_ids`
- `iterate/token_tracker.py` — `get_token_summary()` with `by_stage`, `by_model` breakdowns, `cost_per_publishable_ad()`
- `evaluate/evaluator.py` — `EvaluationResult` with per-dimension scores, rationales, confidence flags
- All pipeline events are timestamped (ISO-8601 UTC) and have `checkpoint_id`s
- `iterate/batch_processor.py` — `BatchCompleted` events with per-batch stats (generated, published, discarded counts)
- P4-01: `AgentStarted`, `AgentCompleted`, `AgentFailed` events (if implemented)
- P4-02: `SelfHealingTriggered`, `BriefMutated` events (if implemented)
- P4-05: `ExplorationTriggered`, `ExplorationCompleted`, `PatternPromoted` events (if implemented)

---

## What This Ticket Must Accomplish

### Goal

Build a replay engine that reads the ledger and produces a human-readable, chronological narrative of the entire pipeline run.

### Deliverables Checklist

#### A. Event Parser

Create `output/replay.py`:

- [ ] `ReplayEvent` dataclass — `timestamp: str`, `event_type: str`, `ad_id: str`, `narrative: str`, `details: dict`, `is_failure: bool`
- [ ] `parse_event(event: dict) -> ReplayEvent` — Convert raw ledger event to narrated event
- [ ] Event type narratives (cover all known event types):
  - `BriefExpanded` → "Brief {brief_id} expanded for {audience} audience ({campaign_goal} goal)"
  - `AdGenerated` → "Ad {ad_id} generated (cycle {cycle}), hook: {hook_type}, {tokens} tokens"
  - `AdEvaluated` → "Ad {ad_id} scored {score}/10 (clarity={c}, VP={vp}, CTA={cta}, BV={bv}, ER={er})"
  - `AdRegenerated` → "Ad {ad_id} regenerated (attempt {n}): {weakest_dim} was {old_score} → targeting improvement"
  - `AdPublished` → "Ad {ad_id} published with score {score}/10"
  - `AdDiscarded` → "Ad {ad_id} discarded after {cycles} attempts — {reason}"
  - `BatchCompleted` → "Batch {n} complete: {published} published, {discarded} discarded, {regenerated} regenerated"
  - `VideoGenerated` → "Video generated for ad {ad_id}: {variant_id}, {duration}s, ${cost}"
  - `VideoBlocked` → "[DEGRADED] Ad {ad_id} video blocked — falling back to image-only"
  - `AgentFailed` → "[FAILURE] {agent} failed on ad {ad_id}: {error}"
  - `SelfHealingTriggered` → "[HEALING] Quality drift detected — {action_taken}"
  - `ExplorationTriggered` → "[EXPLORE] Plateau detected after {n} batches — trying {strategy}"
  - `PatternPromoted` → "[LEARN] Pattern promoted: {pattern_type}={pattern_value} (win rate: {rate}%)"
  - Unknown events → generic fallback narrative with event_type and ad_id

#### B. Batch Grouping

- [ ] `BatchNarrative` dataclass — `batch_num: int`, `events: list[ReplayEvent]`, `summary: str`, `failures: list[ReplayEvent]`
- [ ] `group_events_by_batch(events: list[ReplayEvent]) -> list[BatchNarrative]` — Group events between `BatchCompleted` markers
- [ ] Each batch gets a summary: "Batch {n}: {generated} generated, {published} published ({rate}% publish rate), {tokens} tokens"

#### C. Full Replay

- [ ] `PipelineReplay` dataclass — `batches: list[BatchNarrative]`, `total_summary: str`, `failures: list[ReplayEvent]`, `token_summary: dict`
- [ ] `generate_replay(ledger_path: str) -> PipelineReplay` — Full replay from any ledger file
- [ ] Total summary: "Pipeline complete: {total_ads} ads across {batches} batches. {published} published ({rate}%). {failures} failures. {tokens} tokens (${cost} est.)"
- [ ] Failures section: all failure events collected and highlighted

#### D. Text Output Formatters

- [ ] `format_replay_text(replay: PipelineReplay) -> str` — Plain text (for console / DEVLOG)
- [ ] `format_replay_markdown(replay: PipelineReplay) -> str` — Markdown (for documentation / README)
- [ ] Failures marked with `[!]` prefix
- [ ] Healing/exploration events marked with special prefixes (`[HEALING]`, `[EXPLORE]`, `[LEARN]`)

### Files to Create/Modify

| File | Action |
|------|--------|
| `output/replay.py` | **Create** — Replay engine |
| `tests/test_pipeline/test_replay.py` | **Create** — Tests |

### Files to READ for Context

| File | Why |
|------|-----|
| `iterate/ledger.py` | Event reading interface (`read_events`, `read_events_filtered`) |
| `iterate/checkpoint.py` | `PipelineState` for summary stats |
| `iterate/token_tracker.py` | `get_token_summary()` for cost reporting |
| `iterate/batch_processor.py` | `BatchCompleted` event format |

---

## Important Context

### Architectural Decisions

| Decision | Reference | Summary |
|----------|-----------|---------|
| Append-only ledger enables replay | R2-Q8 | Every decision is recorded — nothing lost |
| Narrated replay | R2-Q10 | Chronological walkthrough with per-batch reasoning |
| Failures highlighted | R2-Q10 | System shows where it struggled, not just successes |
| Documentation rubric | Requirements | 20% of grade — replay maximizes this |

### Example Output

```
=== Pipeline Replay ===

--- Batch 1 ---
[00:01] Brief b001 expanded for parent audience (awareness goal)
[00:03] Ad ad_b001_c1_42 generated (cycle 1), hook: question, 1,240 tokens
[00:05] Ad ad_b001_c1_42 scored 6.2/10 (clarity=7.1, VP=5.8, CTA=6.0, BV=6.5, ER=5.9)
[00:05] Ad ad_b001_c1_42 regenerated (attempt 1): value_proposition was 5.8
[00:08] Ad ad_b001_c1_42 scored 7.4/10 after regen (VP improved to 7.2)
[00:08] Ad ad_b001_c1_42 published with score 7.4/10

Batch 1 summary: 10 generated, 6 published (60% rate), 24,500 tokens

--- Failures ---
[!] Ad ad_b003_c1_99 discarded after 3 attempts — brand_voice stuck at 4.8 (floor: 5.0)

=== Total: 50 ads, 5 batches, 32 published (64%), 128,000 tokens ($1.92) ===
```

---

## Definition of Done

- [ ] All known ledger event types parsed into narrative strings
- [ ] Events grouped by batch with per-batch summary
- [ ] Full pipeline replay generated from any ledger file
- [ ] Failures highlighted with context
- [ ] Text and Markdown output formatters working
- [ ] Tests verify: event parsing, batch grouping, summary stats, failure highlighting

---

## Estimated Time: 45–60 minutes
