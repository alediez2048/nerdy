# P1-18 Primer: Full Ad Assembly + Export

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** P1-15 (visual attribute evaluator), P1-16 (coherence checker), P1-17 (image targeted regen loop) must be complete. See `docs/DEVLOG.md`.

---

## What Is This Ticket?

P1-18 implements the **full ad assembly and export** system. Published ads are assembled as complete units: copy JSON + winning image + all variant metadata (scores, rationales, selection reasoning). Each ad gets its own export folder with Meta-ready file naming. This is the final output stage — everything upstream converges here.

### Why It Matters

- **State Is Sacred** (Pillar 5): The assembled output preserves the full decision trail — not just the winner, but why it won
- Without structured assembly, the pipeline produces scattered files that require manual collection
- Meta-ready file naming enables direct upload to Facebook Ads Manager
- Variant metadata in the export enables post-hoc analysis of what visual strategies work
- This is what the stakeholder sees — the tangible deliverable of the entire pipeline

---

## What Was Already Done

- P1-15: Pareto image selection picks the winning variant with composite score
- P1-16: Coherence scores for all variants
- P1-17: Regen loop ensures best possible image; image-blocked ads flagged
- P1-02: Ad copy generator produces primary text, headline, description, CTA
- P1-14: Aspect ratio routing (1:1 default, 4:5 + 9:16 for published winners)
- P0-02: Decision ledger with full ad lifecycle events

---

## What This Ticket Must Accomplish

### Goal

Build the assembly and export system that packages each published ad into a self-contained folder with copy, images, and metadata ready for Meta upload.

### Deliverables Checklist

#### A. Ad Assembler (`output/assembler.py`)

- [ ] `assemble_ad(ad_id: str, ledger_path: str) -> AssembledAd`
  - Collects from ledger:
    - Copy JSON (primary text, headline, description, CTA button)
    - Winning image path + selection rationale
    - All variant metadata (attribute scores, coherence scores, composite scores)
    - Text evaluation scores (5 dimensions + weighted average)
    - Generation metadata (cycle, batch, seed, model used)
  - Returns structured `AssembledAd` object
- [ ] `is_publishable(ad_id: str, ledger_path: str) -> bool`
  - True if ad passed text threshold (7.0+) AND has a selected winning image
  - False for image-blocked ads (they go to human review, not export)

#### B. Export Writer (`output/exporter.py`)

- [ ] `export_ad(assembled: AssembledAd, output_dir: str) -> str`
  - Creates folder: `output/{ad_id}/`
  - Writes:
    - `copy.json` — Ad copy fields (primary_text, headline, description, cta)
    - `image_winner.{ext}` — The winning image file (copied, not moved)
    - `metadata.json` — Full metadata: text scores, image attribute scores, coherence scores, composite score, variant selection rationale, generation params
    - `variants/` subfolder with all variant images + per-variant score files
  - Meta-ready naming: `{audience}_{goal}_{ad_id}_1x1.{ext}`
  - Returns path to export folder
- [ ] `export_batch(ad_ids: list[str], ledger_path: str, output_dir: str) -> ExportSummary`
  - Assembles and exports all publishable ads in a batch
  - Returns summary: total exported, skipped (image-blocked), failed

#### C. Tests (`tests/test_pipeline/test_assembler.py`)

- [ ] TDD first
- [ ] Test assembly collects correct copy, image, and metadata from ledger
- [ ] Test `is_publishable` returns True for ads with passing text + winning image
- [ ] Test `is_publishable` returns False for image-blocked ads
- [ ] Test export creates correct folder structure
- [ ] Test export writes copy.json with all required fields
- [ ] Test export writes metadata.json with variant scores
- [ ] Test Meta-ready file naming convention
- [ ] Test batch export skips image-blocked ads with correct summary
- [ ] Minimum: 8+ tests

#### D. Documentation

- [ ] Add P1-18 entry in `docs/DEVLOG.md`

---

## Branch & Merge Workflow

```bash
git switch main && git pull
git switch -c feature/P1-18-full-ad-assembly
```

---

## Important Context

### Architectural Decisions

| Decision | Reference | Summary |
|----------|-----------|---------|
| Append-only ledger as source of truth | R2-Q8 | Assembly reads from ledger — never from transient state |
| Visible reasoning | Pillar 7 | Export includes rationales and variant comparison, not just the winner |
| Meta-ready outputs | Section 4.6 | File naming and structure designed for direct Facebook Ads Manager upload |

### Files to Create

| File | Why |
|------|-----|
| `output/assembler.py` | Collects ad components from ledger into structured object |
| `output/exporter.py` | Writes assembled ads to export folders |
| `tests/test_pipeline/test_assembler.py` | Assembly + export tests |

### Files You Should READ for Context

| File | Why |
|------|-----|
| P0-02 ledger module | How to query ad lifecycle events |
| P1-15 image selector | How winning variant is determined |
| P1-02 copy generator | Copy JSON structure |
| `output/` existing modules | Any existing output patterns |

---

## Definition of Done

- [ ] Each published ad assembled with copy + winning image + full metadata
- [ ] Export folder per ad with correct structure (`copy.json`, `image_winner`, `metadata.json`, `variants/`)
- [ ] Meta-ready file naming applied
- [ ] Image-blocked ads excluded from export (flagged for human review)
- [ ] Batch export produces correct summary
- [ ] Tests pass
- [ ] Lint clean
- [ ] DEVLOG updated
- [ ] Feature branch pushed

---

## Estimated Time: 45–60 minutes

---

## After This Ticket: What Comes Next

**P1-19 (Image cost tracking)** extends the token attribution engine to cover image generation costs — per-image, per-variant, per-regen, per-aspect-ratio. With assembly complete, the pipeline has a tangible output; P1-19 ensures we know exactly what each ad cost to produce. Then **P1-20** runs the full 50+ ad generation.
