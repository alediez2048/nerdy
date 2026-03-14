# P1-20 Primer: 50+ Full Ad Generation Run

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** P1-01 through P1-19 (entire P1 phase) must be complete. See `docs/DEVLOG.md`.

---

## What Is This Ticket?

P1-20 is the **capstone execution run** for Phase 1. The full pipeline — brief expansion, copy generation, image generation (3 variants), visual attribute evaluation, coherence checking, Pareto selection, targeted regen, quality ratchet, and full ad assembly — runs end-to-end. 5+ batches, 3+ iteration cycles, producing 50+ evaluated full ads (copy + image) that meet both the text quality threshold (7.0+) and image evaluation criteria (80% attribute pass + coherence >= 6).

### Why It Matters

- **Learning Is Structural** (Pillar 6): 50+ ads across 3+ cycles generates enough data to show measurable quality improvement
- This is the primary quantitative target from the PRD success criteria: "50+ publishable full ads (copy + image) with evaluation scores"
- Quality trend across cycles proves the iteration system works — the ratchet only goes up
- The run validates every upstream component working together under real conditions
- All variant metadata, cost attribution, and quality scores are logged — feeding Phase 2 testing, Phase 5 dashboard, and the final submission

---

## What Was Already Done

- P1-01: Brief expansion engine with competitive context
- P1-02: Ad copy generator (reference-decompose-recombine)
- P1-03: Audience-specific brand voice profiles
- P1-04: Chain-of-thought evaluator (5 dimensions + contrastive rationales)
- P1-05: Campaign-goal-adaptive weighting with floor constraints
- P1-06: Tiered model routing (Flash default, Pro for 5.5-7.0 range)
- P1-07: Pareto-optimal regeneration (text)
- P1-08: Brief mutation + escalation after failures
- P1-09: Distilled context objects (compact per-cycle context)
- P1-10: Quality ratchet (rolling high-water mark)
- P1-11: Token attribution engine (text costs)
- P1-12: Result-level cache
- P1-13: Batch-sequential processor (batches of 10)
- P1-14: Nano Banana Pro integration + 3 image variants per ad
- P1-15: Visual attribute evaluator + Pareto image selection
- P1-16: Text-image coherence checker
- P1-17: Image targeted regen loop (max 5 images/ad)
- P1-18: Full ad assembly + export
- P1-19: Image cost tracking + variant win rates

---

## What This Ticket Must Accomplish

### Goal

Execute the full pipeline end-to-end: 5+ batches of 10 ads, 3+ iteration cycles, producing 50+ evaluated full ads with both text and image evaluation. Demonstrate measurable quality improvement across cycles.

### Deliverables Checklist

#### A. Pipeline Execution

- [ ] Run full pipeline with `--batches 5 --cycles 3` (minimum)
  - Each batch: 10 briefs expanded, copy generated, images generated (3 variants each)
  - Each cycle: evaluate, regen failed ads, re-evaluate
  - Checkpoint-resume active throughout (P0-08)
- [ ] 50+ ads evaluated with:
  - Text scores across 5 dimensions (Clarity, Value Proposition, CTA, Brand Voice, Emotional Resonance)
  - Image attribute scores (5-attribute binary checklist)
  - Coherence scores (4 dimensions)
  - Composite Pareto scores for image selection
- [ ] Published ads meet both thresholds:
  - Text weighted average >= 7.0 (with floor constraints: Clarity >= 6.0, Brand Voice >= 5.0)
  - Image: winning variant passes 80% attributes + coherence >= 6.0

#### B. Quality Trend Validation

- [ ] Quality ratchet demonstrates monotonic increase across cycles
  - Effective threshold = max(7.0, rolling_5batch_avg - 0.5)
- [ ] Per-dimension improvement visible across cycles
- [ ] Publishable rate improves from cycle 1 to cycle 3+
- [ ] Document any interventions and their impact on specific dimensions

#### C. Image Pipeline Validation

- [ ] All published ads have winning images selected by Pareto composite
- [ ] Variant metadata logged for all 3 variants per ad (including losers)
- [ ] Variant win rates calculated (anchor vs. tone shift vs. composition shift)
- [ ] Regen loop activations logged with diagnostics
- [ ] Image-blocked ads (if any) flagged for human review

#### D. Cost Attribution

- [ ] Unified cost-per-publishable-ad (text + image) computed
- [ ] Cost breakdown: generation vs. evaluation vs. regen
- [ ] Model routing distribution logged (Flash vs. Pro usage)

#### E. Output

- [ ] `output/` folder contains assembled ads (P1-18 format)
- [ ] Each published ad: `copy.json`, `image_winner`, `metadata.json`, `variants/`
- [ ] Decision ledger contains complete lifecycle for all 50+ ads
- [ ] Summary statistics logged:
  - Total ads generated, evaluated, published, discarded, image-blocked
  - Average text score, average coherence score, average composite score
  - Total cost, cost per publishable ad
  - Quality trend data points per cycle

#### F. Documentation

- [ ] Add P1-20 entry in `docs/DEVLOG.md`
- [ ] Log any pipeline failures, rate limit issues, or unexpected behaviors
- [ ] Document quality trend observations

---

## Branch & Merge Workflow

```bash
git switch main && git pull
git switch -c feature/P1-20-full-ad-generation-run
```

---

## Important Context

### Architectural Decisions

| Decision | Reference | Summary |
|----------|-----------|---------|
| Batch-sequential processing | R3-Q9 | Batches of 10, parallel within stage, sequential across stages. Batch boundaries = checkpoints. |
| Quality ratchet | R1-Q9 | Rolling high-water mark: max(7.0, rolling_5batch_avg - 0.5). Threshold only increases. |
| Checkpoint-resume | R3-Q2 | Every successful API call checkpointed. `--resume` picks up from last checkpoint. |
| Pareto selection | R1-Q5 | No dimension regresses; composite score balances attributes and coherence. |
| Multi-variant generation | Section 4.6 | 3 variants per ad (anchor, tone shift, composition shift) for Pareto selection. |

### Files to Create

| File | Why |
|------|-----|
| Run script or config for 50+ ad execution | Pipeline orchestration with correct parameters |

### Files You Should READ for Context

| File | Why |
|------|-----|
| `config.yaml` | Pipeline parameters (batch size, cycle count, thresholds) |
| P1-13 batch processor | How batches are orchestrated |
| P0-08 checkpoint module | How resume works |
| P1-10 quality ratchet | How threshold evolves |
| P1-18 assembler/exporter | How output is structured |

---

## Definition of Done

- [ ] 50+ full ads (copy + image) evaluated end-to-end
- [ ] Quality trend shows measurable improvement across 3+ cycles
- [ ] All published ads have winning images with variant metadata
- [ ] Unified cost-per-publishable-ad computed (text + image)
- [ ] Output folder contains assembled ads in Meta-ready format
- [ ] Decision ledger contains complete lifecycle for all ads
- [ ] No crashes — checkpoint-resume handles all interruptions
- [ ] DEVLOG updated with run observations
- [ ] Feature branch pushed

---

## Estimated Time: 90–120 minutes (includes pipeline execution time)

---

## After This Ticket: What Comes Next

**Phase 1 is now complete.** The full ad pipeline is validated:
- Brief expansion + copy generation (P1-01, P1-02) ✅
- Text evaluation + quality ratchet (P1-04, P1-05, P1-10) ✅
- Image generation + evaluation + selection (P1-14, P1-15, P1-16) ✅
- Targeted regen loops (P1-07, P1-08, P1-17) ✅
- Full ad assembly + export (P1-18) ✅
- Cost attribution (P1-11, P1-19) ✅
- 50+ ads produced (P1-20) ✅

**Phase 2 begins:** P2-01 (Inversion tests) validates that the 5 text evaluation dimensions are truly independent. Phase 2 proves the evaluation framework has substance.
