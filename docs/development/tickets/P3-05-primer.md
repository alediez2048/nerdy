# P3-05 Primer: Multi-Model Orchestration Doc

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** P3-01 (cost-tier model), P3-04 (style experiments), P1-19 (image cost tracking) must be complete. See `docs/DEVLOG.md`.

---

## What Is This Ticket?

P3-05 creates a **multi-model orchestration architecture document** that explains which model handles which task and why, with per-model cost attribution across all three creative formats (text, image, video). This is both a deliverable document and a cost-tracking implementation.

### Why It Matters

- **Every Token Is an Investment** (Pillar 3): Explicit rationale for model routing enables informed cost optimization
- Bonus weight: +3 points (alongside P1-06, P1-14, P3-07)
- R1-Q4 specifically asks for documented multi-model orchestration rationale
- Per-model cost attribution enables ROI analysis per generation stage

---

## What Was Already Done

- P0-04: Model router (`generate/model_router.py`) — text model routing (Flash vs Pro)
- P1-06: Ad generator — text generation
- P1-14: Image generator — Nano Banana Pro integration
- P1-19: Image cost tracker — per-variant, per-regen cost breakdown
- P3-01: Nano Banana 2 — cost-tier image model
- `iterate/token_tracker.py` — token counting per API call

---

## What This Ticket Must Accomplish

### Goal

1. Create an architecture document explaining model routing rationale across text, image, and video.
2. Implement unified cross-format cost attribution that tracks tokens and estimated cost per model.

### Deliverables Checklist

#### A. Architecture Document (`docs/deliverables/model_orchestration.md` — new)

- [ ] **Model Inventory** — table of all models used, their purpose, and cost per unit:

  | Task | Model | API Name | Cost | Rationale |
  |------|-------|----------|------|-----------|
  | First-draft text generation | Gemini Flash | gemini-2.0-flash | ~$0.01/1K tokens | 80% of text work at lowest cost |
  | Text regeneration (improvable) | Gemini Pro | gemini-2.0-pro | ~$0.05/1K tokens | Quality tokens on borderline ads (5.5–7.0) |
  | Text evaluation (CoT scorer) | Gemini Flash | gemini-2.0-flash | ~$0.01/1K tokens | Structured evaluation doesn't need Pro |
  | Image generation (quality tier) | Nano Banana Pro | gemini-3-pro-image | ~$0.13/image | 4K output, text rendering for anchors |
  | Image generation (cost tier) | Nano Banana 2 | gemini-3.1-flash-image | ~$0.02–0.05/image | Volume variants, experiments |
  | Image evaluation | Gemini Flash | gemini-2.0-flash (multimodal) | ~$0.01/1K tokens | Cheap multimodal for attribute + coherence |
  | Video generation | Veo 3.1 Fast | veo-3.1-fast | ~$0.15/sec | Native audio, 1080p 9:16 |
  | Video evaluation | Gemini Flash | gemini-2.0-flash (multimodal) | ~$0.01/1K tokens | Frame sampling + attribute check |

- [ ] **Routing Logic** — flowchart/prose describing routing decisions:
  - Text: Flash for first draft → evaluate → Pro only for improvable (5.5–7.0)
  - Image: Pro for anchors → NB2 for variant volume → Flash for evaluation
  - Video: Veo for generation → Flash for evaluation → graceful degradation on failure
- [ ] **Cost Optimization Strategies** — document strategies applied:
  - Tiered routing (cheap-first, upgrade selectively)
  - Result caching (`iterate/cache.py`)
  - Budget caps per ad and per session
  - Early termination for failing ads
  - Cost-tier model for experiments and variants
- [ ] **Cost Economics Summary** — 50-ad batch projected costs across formats

#### B. Cross-Format Cost Reporter (`evaluate/cost_reporter.py` — new)

- [ ] `ModelCostEntry` dataclass:
  - `model_name: str`
  - `task: str` (generation, evaluation, regen, etc.)
  - `format: str` (text, image, video)
  - `total_tokens: int`
  - `call_count: int`
  - `estimated_cost_usd: float`
- [ ] `CrossFormatCostReport` dataclass:
  - `entries: list[ModelCostEntry]`
  - `total_cost_usd: float`
  - `cost_by_format: dict[str, float]` (text, image, video)
  - `cost_by_model: dict[str, float]`
  - `cost_by_task: dict[str, float]`
- [ ] `generate_cost_report(ledger_path: str) -> CrossFormatCostReport`
  - Reads all ledger events
  - Groups by model_used, format (derived from event_type), and action
  - Applies per-model cost rates to estimate USD cost
  - Returns full breakdown
- [ ] `MODEL_COST_RATES: dict[str, float]` — token-to-USD conversion per model
- [ ] `format_cost_report(report: CrossFormatCostReport) -> str`
  - Returns human-readable cost summary (for dashboard/logging)

#### C. Tests (`tests/test_pipeline/test_cost_reporter.py`)

- [ ] TDD first
- [ ] Test cost report with text-only events
- [ ] Test cost report with text + image events
- [ ] Test cost report with all three formats
- [ ] Test cost grouping by model is accurate
- [ ] Test cost grouping by format is accurate
- [ ] Test cost grouping by task is accurate
- [ ] Test estimated USD cost calculation
- [ ] Test empty ledger returns zero-cost report
- [ ] Test `format_cost_report()` produces readable output
- [ ] Minimum: 8+ tests

#### D. Documentation

- [ ] Add P3-05 entry in `docs/DEVLOG.md`
- [ ] The architecture doc IS the primary deliverable (see section A)

---

## Branch & Merge Workflow

Work on `develop` branch per project convention.

---

## Important Context

### Architectural Decisions

| Decision | Reference | Summary |
|----------|-----------|---------|
| Tiered routing | R1-Q4 | Flash for volume, Pro for quality — cost-proportional quality |
| Full attribution | Pillar 3 | Every token tagged with purpose, model, format |
| Cost-tier for images | P3-01 | NB2 for variants, Pro for anchors |
| Graceful degradation | Section 4.9 | Video failure → image-only, no wasted video eval cost |

### Files to Create

| File | Why |
|------|-----|
| `docs/deliverables/model_orchestration.md` | Architecture doc (primary deliverable) |
| `evaluate/cost_reporter.py` | Cross-format cost reporting |
| `tests/test_pipeline/test_cost_reporter.py` | Tests |

### Files You Should READ for Context

| File | Why |
|------|-----|
| `generate/model_router.py` | Text model routing logic |
| `generate/image_generator.py` | Image model routing |
| `evaluate/image_cost_tracker.py` | Image cost tracking pattern |
| `iterate/token_tracker.py` | Token counting |
| `docs/reference/prd.md` (Section 4.3) | Model routing architecture |

---

## Definition of Done

- [ ] Architecture doc covers all models across text, image, video
- [ ] Routing rationale documented with cost justification
- [ ] Cross-format cost reporter implemented
- [ ] Cost breakdown by model, format, and task
- [ ] Estimated USD costs computed
- [ ] Tests pass (8+)
- [ ] Lint clean
- [ ] DEVLOG updated

---

## Estimated Time: 45–60 minutes

---

## After This Ticket: What Comes Next

**P3-06 (Multi-aspect-ratio batch generation)** generates 1:1, 4:5, and 9:16 variants for published ads. The cost reporter from P3-05 tracks the additional image generation costs.
