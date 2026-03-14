# P3-13 Primer: 10-Ad Video Pilot Run

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** P3-07 through P3-12 (full video pipeline) must be complete. See `docs/DEVLOG.md`.

---

## What Is This Ticket?

P3-13 is the **video integration test** — run the full pipeline with video enabled for 10 ads, generating 2 video variants each. This validates the entire video sub-pipeline end-to-end: spec extraction, Veo generation, attribute evaluation, coherence checking, Pareto selection, regen loop, graceful degradation, three-format assembly, and cost tracking.

### Why It Matters

- **Visible Reasoning Is a First-Class Output** (Pillar 7): The pilot run produces concrete evidence that the video pipeline works — scores, costs, pass rates, and degradation handling
- 10 ads is a controlled scale: enough to surface real failures, small enough to cap costs (~$18–$27 for video alone)
- The pilot validates graceful degradation before scaling to 50+ ads
- Results inform whether to enable video by default or keep it opt-in

---

## What Was Already Done

- P3-07: Veo integration + video spec extraction
- P3-08: Video attribute evaluator (10-attribute checklist)
- P3-09: Script-video coherence checker (4-dimension scoring)
- P3-10: Video Pareto selection + regen loop + graceful degradation
- P3-11: Three-format ad assembly
- P3-12: Video cost tracking
- P1-20: 50+ full ad generation run (copy + image baseline — pattern to follow)

---

## What This Ticket Must Accomplish

### Goal

Execute a full pipeline run with video enabled for 10 ads, verifying that all video sub-systems work correctly and failures degrade gracefully.

### Deliverables Checklist

#### A. Pilot Run Configuration

- [ ] Configure pipeline for 10 ads with video enabled
- [ ] Video toggle: ON (default is OFF — this pilot explicitly enables it)
- [ ] Budget cap: $20/ad (to catch runaway costs)
- [ ] Mix of audience segments: ~5 parent-facing, ~5 student-facing
- [ ] Mix of campaign goals: ~5 awareness, ~5 conversion

#### B. Execution & Monitoring

- [ ] Run full pipeline: brief expansion → copy generation → image generation → **video generation** → evaluation → selection → assembly
- [ ] Monitor for:
  - Veo API rate limit handling (429 errors + backoff)
  - Video attribute pass rates across 10 ads
  - Coherence scores across 10 ads
  - Regen triggers and outcomes
  - Graceful degradation events
  - Total video cost vs. budget

#### C. Validation Checklist

- [ ] **Video generation:** All 10 ads attempted video generation (20 initial variants)
- [ ] **Attribute evaluation:** All variants scored against 10-attribute checklist
- [ ] **Coherence checking:** All copy + video pairs scored on 4 dimensions
- [ ] **Selection:** Best variant selected per ad by composite score
- [ ] **Regen loop:** At least 1 regen triggered (if any failures — verify it works)
- [ ] **Graceful degradation:** Any video-blocked ads published with copy + image only
- [ ] **Three-format assembly:** Published ads contain copy + image + video (or copy + image for degraded)
- [ ] **Cost tracking:** Dashboard shows text + image + video cost breakdown
- [ ] **Checkpoint-resume:** Pipeline can be interrupted and resumed without duplicating video work

#### D. Results Analysis

- [ ] Video attribute pass rate (target: document baseline, no hard target for pilot)
- [ ] Average coherence score across 4 dimensions
- [ ] Number of ads with successful video vs. degraded to image-only
- [ ] Total video cost and cost-per-ad with video
- [ ] Regen success rate (did diagnostic-targeted regen improve the variant?)
- [ ] Comparison: cost-per-ad with video vs. without video (from P1-20 baseline)

#### E. Pilot Report

- [ ] Summary of results in DEVLOG entry:
  - Pass rates, coherence scores, degradation count
  - Total cost breakdown (text + image + video)
  - Issues encountered and resolutions
  - Recommendation: enable video by default or keep opt-in

#### F. Documentation

- [ ] Add P3-13 entry in `docs/DEVLOG.md` with pilot results

---

## Branch & Merge Workflow

```bash
git switch main && git pull
git switch -c feature/P3-13-video-pilot-run
```

---

## Important Context

### Architectural Decisions

| Decision | Reference | Summary |
|----------|-----------|---------|
| 10-ad pilot before scaling | Section 4.9, Risk Register | Validate video pipeline at small scale before enabling for 50+ ads |
| Video toggle defaults to OFF | Risk Register | Video is expensive — opt-in by default, enabled explicitly for pilot |
| Graceful degradation | Section 4.9 | Video failures must not block ad delivery |
| Budget cap | Risk Register | Default $20/ad prevents runaway costs during pilot |

### Expected Cost Envelope

| Scenario | Video Cost | Total (with text + image) |
|----------|-----------|--------------------------|
| Best case (no regen) | 10 ads * $1.80 = $18.00 | ~$25–$30 |
| Worst case (all regen) | 10 ads * $2.70 = $27.00 | ~$35–$40 |
| With degradation | Lower (failed videos = $0) | Varies |

### Files You Should READ for Context

| File | Why |
|------|-----|
| P1-20 (50+ ad run) | Pattern for large-scale pipeline execution |
| P3-07 through P3-12 modules | All video sub-systems being exercised |
| `config.yaml` | Pipeline configuration (video toggle, budget cap) |
| `docs/DEVLOG.md` | Previous ticket results for context |

---

## Definition of Done

- [ ] 10 ads with video generated (or gracefully degraded)
- [ ] Video attribute scores logged for all variants
- [ ] Coherence scores logged for all copy + video pairs
- [ ] Failures degrade to image-only (no pipeline crashes)
- [ ] Three-format assembly produces complete output
- [ ] Cost dashboard shows text + image + video breakdown
- [ ] Pilot results documented in DEVLOG
- [ ] Feature branch pushed

---

## Estimated Time: 60–90 minutes

---

## After This Ticket: What Comes Next

**Phase 3 is now complete.** The v2 pipeline supports:
- A/B copy variants (P3-02) and image variants (P3-03)
- Multi-model image orchestration (P3-01, P3-05)
- UGC video generation via Veo (P3-07 through P3-13)

**Phase 4 begins:** P4-01 (Agentic orchestration layer) adds autonomous agents with error boundaries.
