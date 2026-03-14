# P3-12 Primer: Video Cost Tracking

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** P3-10 (video Pareto selection + regen loop), P1-11 (token attribution engine), P1-19 (image cost tracking — pattern to follow) must be complete. See `docs/DEVLOG.md`.

---

## What Is This Ticket?

P3-12 extends the **token attribution engine** (P1-11) and **image cost tracking** (P1-19) to include video generation costs. The system tracks costs per-video, per-variant, per-regen, and by audio mode (audio vs. silent). The unified cost-per-publishable-ad metric now spans all 3 formats: text + image + video.

### Why It Matters

- **Every Token Is an Investment** (Pillar 3): Video is the most expensive format (~$0.90/6-sec clip) — granular cost tracking is essential for budget management
- At 2 variants + potential regen, video can cost $1.80–$2.70 per ad — this must be visible
- Silent mode saves ~33% — tracking audio vs. silent costs validates this optimization
- The unified cost-per-publishable-ad metric lets operators compare ROI across formats
- P4-06 (full marginal analysis engine) depends on this data

---

## What Was Already Done

- P1-11: Token attribution engine (text cost tracking — per-call, per-stage)
- P1-19: Image cost tracking (per-image, per-variant, per-regen, per-aspect-ratio)
- P3-07: Veo integration (video generation with cost metadata)
- P3-10: Video regen loop (regen costs need tracking)

---

## What This Ticket Must Accomplish

### Goal

Extend cost tracking to cover video generation, producing a unified cost-per-publishable-ad across text, image, and video.

### Deliverables Checklist

#### A. Video Cost Tracker (`iterate/video_cost.py`)

- [ ] `track_video_cost(ad_id: str, variant_id: str, generation_metadata: dict) -> VideoCostEntry`
  - Records: ad_id, variant_id, duration, audio_mode, generation_cost, is_regen
  - Cost calculation: duration_seconds * cost_per_second ($0.15/sec for Veo 3.1 Fast)
  - Audio vs. silent flag for cost differential analysis
- [ ] `get_video_costs_by_ad(ad_id: str) -> list[VideoCostEntry]`
  - Returns all video costs for an ad (initial variants + regen)
- [ ] `get_video_cost_summary(ledger_path: str) -> VideoCostSummary`
  - Total video spend, avg cost per ad, regen cost overhead, audio vs. silent breakdown

#### B. Unified Cost Aggregator (`iterate/cost_aggregator.py` — extend existing)

- [ ] `compute_unified_cost_per_ad(ad_id: str) -> UnifiedCost`
  - Aggregates: text API costs + image generation costs + video generation costs
  - Breakdown by format: text_cost, image_cost, video_cost, total_cost
  - Handles video-blocked ads (video_cost = 0 for degraded ads)
- [ ] `compute_batch_cost_summary(ledger_path: str) -> BatchCostSummary`
  - Aggregate stats across all ads in batch
  - Per-format averages and totals
  - Regen overhead percentage per format

#### C. Dashboard Data Extension

- [ ] Extend `export_dashboard.py` data to include video cost panels:
  - Per-ad text + image + video cost stacked bars
  - Video variant strategy stats (anchor vs. alternative win rates)
  - Regen cost overhead for video
  - Audio vs. silent cost comparison
  - Projected cost at scale (10, 50, 100 ads) across all 3 formats

#### D. Tests (`tests/test_pipeline/test_video_cost.py`)

- [ ] TDD first
- [ ] Test video cost calculation (duration * rate)
- [ ] Test audio vs. silent cost differential
- [ ] Test regen costs tracked separately from initial variants
- [ ] Test unified cost aggregation across all 3 formats
- [ ] Test video-blocked ads have video_cost = 0
- [ ] Test batch summary computes correct averages
- [ ] Test cost summary includes regen overhead percentage
- [ ] Minimum: 7+ tests

#### E. Documentation

- [ ] Add P3-12 entry in `docs/DEVLOG.md`

---

## Branch & Merge Workflow

```bash
git switch main && git pull
git switch -c feature/P3-12-video-cost-tracking
```

---

## Important Context

### Architectural Decisions

| Decision | Reference | Summary |
|----------|-----------|---------|
| Full token attribution | R1-Q7 | Every API call tagged with ad_id, stage, model, cost |
| Per-format cost breakdown | P1-11, P1-19 | Text, image, and video costs tracked independently but aggregated per ad |
| Silent mode optimization | Section 4.9 | Silent video saves ~33% — track to validate |
| Budget cap | Section 4.9 | Default $20/ad across all formats — video cost tracking enforces this |

### Cost Reference

| Item | Cost |
|------|------|
| Veo 3.1 Fast | ~$0.15/sec (~$0.90/6-sec video) |
| 2 variants per ad | ~$1.80 |
| Max with 1 regen | ~$2.70 |
| Silent mode savings | ~33% reduction |

### Files to Create

| File | Why |
|------|-----|
| `iterate/video_cost.py` | Video-specific cost tracking |
| `tests/test_pipeline/test_video_cost.py` | Video cost tracking tests |

### Files to Modify

| File | Why |
|------|-----|
| `iterate/cost_aggregator.py` (or equivalent) | Add video costs to unified aggregation |
| Dashboard export script | Include video cost panels |

### Files You Should READ for Context

| File | Why |
|------|-----|
| P1-11 token attribution engine | Text cost tracking pattern |
| P1-19 image cost tracking | Image cost tracking pattern (direct extension) |
| P3-07 Veo client | Video generation cost metadata |
| P3-10 video regen loop | Regen cost events |

---

## Definition of Done

- [ ] Video costs tracked per-video, per-variant, per-regen
- [ ] Audio vs. silent cost breakdown available
- [ ] Unified cost-per-publishable-ad spans text + image + video
- [ ] Video-blocked ads correctly show video_cost = 0
- [ ] Dashboard data includes video cost panels
- [ ] Tests pass
- [ ] Lint clean
- [ ] DEVLOG updated
- [ ] Feature branch pushed

---

## Estimated Time: 45–60 minutes

---

## After This Ticket: What Comes Next

**P3-13 (10-ad video pilot run)** is the integration test — run the full pipeline with video enabled for 10 ads and verify everything works end-to-end.
