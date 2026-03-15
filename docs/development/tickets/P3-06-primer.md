# P3-06 Primer: Multi-Aspect-Ratio Batch Generation

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** P1-14 (image generator), P1-15 (image evaluator), P1-18 (ad assembly + export), P3-01 (cost-tier model) must be complete. See `docs/DEVLOG.md`.

---

## What Is This Ticket?

P3-06 generates **three aspect-ratio variants (1:1, 4:5, 9:16)** for every published ad's winning image. This ensures each ad is Meta-ready for Feed (1:1), Feed-tall (4:5), and Stories/Reels (9:16) placements. All variants must pass the attribute checklist.

### Why It Matters

- Meta requires different aspect ratios for different placements — without this, ads can only run on one placement type
- Generating ratios only for winners (not all variants) is cost-efficient: ~76 extra images instead of ~450
- Each ratio variant must independently pass the attribute checklist — a 1:1 pass doesn't guarantee 9:16 will
- Section 4.6.9 of the PRD defines Meta-ready output specs

---

## What Was Already Done

- P1-14: Image generator (`generate/image_generator.py`) — generates images with aspect ratio parameter
- P1-15: Image evaluator (`evaluate/image_evaluator.py`) — 5-attribute checklist
- P1-18: Ad assembly + export (`output/assembler.py`, `output/exporter.py`) — assembles copy + winning image
- P3-01: Cost-tier model routing — NB2 for volume generation

---

## What This Ticket Must Accomplish

### Goal

For each published ad, generate its winning image in all three Meta aspect ratios, evaluate each, and include all passing variants in the export package.

### Deliverables Checklist

#### A. Aspect Ratio Generator (`generate/aspect_ratio_batch.py` — new)

- [ ] `META_ASPECT_RATIOS` — the three required ratios:

  | Placement | Aspect Ratio | Min Resolution |
  |-----------|-------------|----------------|
  | Feed | 1:1 | 1080×1080 |
  | Feed (tall) | 4:5 | 1080×1350 |
  | Stories/Reels | 9:16 | 1080×1920 |

- [ ] `AspectRatioResult` dataclass:
  - `ad_id: str`
  - `aspect_ratio: str`
  - `image_path: str`
  - `passes_checklist: bool`
  - `attribute_pass_pct: float`
  - `model_used: str`
- [ ] `AspectRatioBatchResult` dataclass:
  - `ad_id: str`
  - `results: dict[str, AspectRatioResult]` (ratio → result)
  - `all_pass: bool`
  - `failed_ratios: list[str]`
- [ ] `generate_aspect_ratios(ad_id: str, visual_spec: dict, seed: int, ratios: list[str] | None = None) -> AspectRatioBatchResult`
  - Generates winning image in each ratio using the same visual spec + seed
  - Defaults to all three ratios if not specified
  - Uses cost-tier model (NB2) for ratio variants (anchor already generated in Pro)
  - Evaluates each via attribute checklist
  - Logs results to ledger as `AspectRatioGenerated` events
- [ ] `skip_existing_ratios(ad_id: str, ledger_path: str) -> list[str]`
  - Returns ratios already generated (for checkpoint-resume)

#### B. Export Integration (`output/exporter.py` — extend)

- [ ] Update `export_ad()` to include multi-ratio images in export package:
  - `{ad_id}/images/1_1.png`
  - `{ad_id}/images/4_5.png`
  - `{ad_id}/images/9_16.png`
- [ ] Update `metadata.json` to include aspect ratio info:
  - `aspect_ratios: {ratio: {path, passes_checklist, attribute_pass_pct}}`
- [ ] Only include ratios that pass the attribute checklist
- [ ] Original winning image (from P1-15 selection) always included regardless

#### C. Batch Orchestration (`generate/aspect_ratio_batch.py`)

- [ ] `generate_batch_aspect_ratios(ad_ids: list[str], ledger_path: str, output_dir: str) -> dict[str, AspectRatioBatchResult]`
  - Processes only published ads (checks `is_publishable()`)
  - Skips ratios already generated (checkpoint-resume)
  - Logs progress to ledger
  - Returns results keyed by ad_id
- [ ] Cost tracking: all ratio generations logged with model_used and tokens_consumed

#### D. Tests (`tests/test_pipeline/test_aspect_ratio_batch.py`)

- [ ] TDD first
- [ ] Test all three ratios generated for a published ad
- [ ] Test failing ratio excluded from export but others included
- [ ] Test `skip_existing_ratios()` correctly identifies already-generated
- [ ] Test batch only processes published ads
- [ ] Test export directory structure includes ratio subdirectory
- [ ] Test metadata.json includes aspect ratio info
- [ ] Test cost-tier model used for ratio variants
- [ ] Test `all_pass` flag correct when all/some/none pass
- [ ] Minimum: 8+ tests

#### E. Documentation

- [ ] Add P3-06 entry in `docs/DEVLOG.md`

---

## Branch & Merge Workflow

Work on `develop` branch per project convention.

---

## Important Context

### Architectural Decisions

| Decision | Reference | Summary |
|----------|-----------|---------|
| Winners-only expansion | Section 4.6.8 | Generate ratios only for winning images, not all variants (~76 vs ~450 images) |
| Cost-tier for ratios | P3-01 | NB2 for ratio variants — anchor already validated in Pro |
| Independent evaluation | P1-15 | Each ratio must independently pass checklist — 1:1 pass ≠ 9:16 pass |
| Graceful inclusion | — | If one ratio fails, others still included in export |

### Cost Economics

| Scenario | Extra Images | NB2 Cost |
|----------|-------------|----------|
| 38 published ads × 2 extra ratios | 76 | ~$1.52–3.80 |
| + regen for failed ratios (~10%) | ~8 | ~$0.16–0.40 |
| **Total** | **~84** | **~$1.68–4.20** |

### Meta-Ready Output Structure

```
output/
  ad_001/
    copy.json
    metadata.json          # includes aspect_ratio section
    images/
      winner.png           # original winning image
      1_1.png              # 1:1 Feed variant
      4_5.png              # 4:5 Feed-tall variant
      9_16.png             # 9:16 Stories/Reels variant
```

### Files to Create

| File | Why |
|------|-----|
| `generate/aspect_ratio_batch.py` | Ratio generation + batch orchestration |
| `tests/test_pipeline/test_aspect_ratio_batch.py` | Tests |

### Files to Modify

| File | Why |
|------|-----|
| `output/exporter.py` | Include ratio images in export |

### Files You Should READ for Context

| File | Why |
|------|-----|
| `generate/image_generator.py` | Image generation with aspect_ratio param |
| `evaluate/image_evaluator.py` | Attribute checklist evaluation |
| `output/exporter.py` | Current export structure to extend |
| `output/assembler.py` | How winning image is selected |
| `docs/reference/prd.md` (Section 4.6.9) | Meta-ready output specs |

---

## Definition of Done

- [ ] Three aspect ratios generated for each published ad's winning image
- [ ] Each ratio independently evaluated via attribute checklist
- [ ] Export package includes all passing ratio variants
- [ ] Metadata.json includes aspect ratio info
- [ ] Checkpoint-resume skips already-generated ratios
- [ ] Cost-tier model used for ratio variants
- [ ] Tests pass (8+)
- [ ] Lint clean
- [ ] DEVLOG updated

---

## Estimated Time: 45–60 minutes

---

## After This Ticket: What Comes Next

**P3-07 (Veo integration + video spec extraction)** adds video as the third creative format, building on the multi-format infrastructure established in P3-06.
