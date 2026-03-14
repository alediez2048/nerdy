# P3-11 Primer: Three-Format Ad Assembly

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** P3-10 (video Pareto selection + regen loop), P1-18 (full ad assembly — module to extend) must be complete. See `docs/DEVLOG.md`.

---

## What Is This Ticket?

P3-11 extends the **full ad assembly** (P1-18) to include video as the third creative format. Published ads now contain copy + image + video (where video is enabled and passes evaluation). Output covers multiple Meta placements: feed image (1:1/4:5) + Stories/Reels video (9:16). Ads that failed video generation (graceful degradation) export with copy + image only.

### Why It Matters

- **Decomposition Is the Architecture** (Pillar 1): Assembly is a distinct stage — it combines outputs from text, image, and video pipelines into a unified deliverable
- Multi-format output maximizes Meta placement coverage (Feed, Stories, Reels)
- Section 4.9.7 of the PRD defines the three-format assembly spec
- The export must be Meta-ready: correct file naming, placement mapping, and metadata

---

## What Was Already Done

- P1-18: Full ad assembly (copy + image — this is the module being extended)
- P3-10: Video Pareto selection (provides winning video variant or degradation flag)
- P3-06: Multi-aspect-ratio batch generation (1:1, 4:5, 9:16 images already generated)
- P1-02: Ad copy generator (provides structured copy output)

---

## What This Ticket Must Accomplish

### Goal

Extend the ad assembly pipeline to produce three-format output (copy + image + video) with Meta placement mapping and graceful handling of video-blocked ads.

### Deliverables Checklist

#### A. Extended Ad Assembler (`pipeline/assembler.py` — extend existing)

- [ ] `assemble_full_ad(ad_id: str, copy: dict, image: ImageVariant, video: VideoVariant | None) -> AssembledAd`
  - Extends P1-18 assembly to accept optional video variant
  - When video is present: include video file + video metadata in assembled ad
  - When video is None (degradation): assemble with copy + image only, flag as "image-only"
- [ ] Meta placement mapping:
  - Feed: 1:1 or 4:5 image + copy
  - Stories: 9:16 image + 9:16 video (if available) + copy
  - Reels: 9:16 video (if available) + copy
- [ ] Output structure per ad:
  - `output/{ad_id}/copy.json` — structured copy (primary text, headline, description, CTA)
  - `output/{ad_id}/image_feed.{ext}` — feed image (1:1 or 4:5)
  - `output/{ad_id}/image_story.{ext}` — Stories image (9:16)
  - `output/{ad_id}/video_story.{ext}` — Stories/Reels video (9:16, if available)
  - `output/{ad_id}/metadata.json` — scores, variant info, placement map, format flags

#### B. Meta Placement Mapper (`pipeline/placement.py`)

- [ ] `map_placements(assembled_ad: AssembledAd) -> PlacementMap`
  - Maps each creative asset to its Meta placement(s)
  - Handles three-format (copy + image + video) and two-format (copy + image) ads
  - Returns structured placement map for export
- [ ] Placement types: Feed, Stories, Reels
- [ ] Format availability flags per placement

#### C. Tests (`tests/test_pipeline/test_assembly.py` — extend existing)

- [ ] TDD first
- [ ] Test three-format assembly produces all expected output files
- [ ] Test two-format assembly (video-blocked) produces copy + image only
- [ ] Test placement mapping for three-format ad covers Feed, Stories, Reels
- [ ] Test placement mapping for two-format ad covers Feed and Stories (image only)
- [ ] Test metadata.json includes video scores when video is present
- [ ] Test metadata.json flags "image-only" when video is absent
- [ ] Test output directory structure matches spec
- [ ] Minimum: 7+ tests

#### D. Documentation

- [ ] Add P3-11 entry in `docs/DEVLOG.md`

---

## Branch & Merge Workflow

```bash
git switch main && git pull
git switch -c feature/P3-11-three-format-assembly
```

---

## Important Context

### Architectural Decisions

| Decision | Reference | Summary |
|----------|-----------|---------|
| Three-format output | Section 4.9.7 | Copy + image + video as unified deliverable per ad |
| Meta placement mapping | Section 4.9.7 | Each asset maps to Feed, Stories, and/or Reels placement |
| Graceful degradation | Section 4.9 | Video-blocked ads export with copy + image only — no gaps in output |

### Files to Modify

| File | Why |
|------|-----|
| `pipeline/assembler.py` | Extend to accept optional video variant |
| `tests/test_pipeline/test_assembly.py` | Extend with three-format tests |

### Files to Create

| File | Why |
|------|-----|
| `pipeline/placement.py` | Meta placement mapping logic |

### Files You Should READ for Context

| File | Why |
|------|-----|
| P1-18 full ad assembly | Module being extended |
| P3-10 video selection | How winning video variant is provided |
| P3-06 multi-aspect-ratio generation | How image variants are mapped to placements |
| `docs/reference/prd.md` (Section 4.9.7) | Three-format assembly spec |

---

## Definition of Done

- [ ] Published ads contain copy + image + video (where video is enabled)
- [ ] Video-blocked ads export with copy + image only
- [ ] Meta placement mapping covers Feed, Stories, Reels
- [ ] Export includes all format files per ad
- [ ] Metadata includes scores, variant info, and format flags
- [ ] Tests pass
- [ ] Lint clean
- [ ] DEVLOG updated
- [ ] Feature branch pushed

---

## Estimated Time: 45–60 minutes

---

## After This Ticket: What Comes Next

**P3-12 (Video cost tracking)** extends token attribution to include video generation costs across all three formats.
