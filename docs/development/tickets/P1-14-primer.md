# P1-14 Primer: Nano Banana Pro Integration + Multi-Variant Image Generation

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** P0-02 (ledger), P0-03 (seeds), P0-08 (checkpoint-resume + retry), P1-01 (brief expansion), P1-13 (batch processor) must be complete. See `docs/DEVLOG.md`.

---

## What Is This Ticket?

P1-14 integrates **Nano Banana Pro** (Google's Gemini 3 Pro Image model) into the pipeline and implements **multi-variant image generation**. For every ad that passes text evaluation, the system extracts a structured visual spec from the expanded brief, then generates 3 image variants: an anchor (straight interpretation), a tone shift (adjusted emotional register), and a composition shift (different framing). Aspect ratio routing sends 1:1 by default, with 4:5 and 9:16 generated only for published winners. All variants and visual specs are logged to the ledger.

### Why It Matters

- **Complete ads require images.** Text-only ads are incomplete for Meta placements. This ticket transforms the system from a copy generator into a full-ad generator.
- **Multi-variant strategy** (PRD Section 4.6.3): 3 variants per ad dramatically increases the chance of producing a high-quality image. Single-shot generation is too unreliable.
- **Shared semantic brief** (R1-Q10): The visual spec is extracted from the same expanded brief that drives copy — preventing text-image incoherence by design (Prevention Over Detection, Pillar 2).
- **Cost-conscious design** (PRD Section 4.6.8): 50 ads x 3 variants = 150 images at ~$0.13/image = ~$20. Extra aspect ratios only for winners. Budget tier (Nano Banana 2) available in P3-01.
- Feeds P1-15 (visual attribute evaluator), P1-16 (text-image coherence checker), P1-17 (image regen loop), and P1-18 (full ad assembly).

---

## What Was Already Done

- **P0-02** (`iterate/ledger.py`): `log_event()`, `read_events()`, `get_ad_lifecycle()` — all image events will be logged here.
- **P0-03** (`generate/seeds.py`): `get_ad_seed()`, `load_global_seed()` — deterministic seeds for reproducible image generation.
- **P0-03** (`iterate/snapshots.py`): `capture_snapshot()` — state preservation.
- **P0-06** (`evaluate/evaluator.py`): `evaluate_ad()`, `EvaluationResult` — text evaluation (images generated only for ads passing text eval).
- **P0-08** (`iterate/checkpoint.py`): `get_pipeline_state()`, `should_skip_ad()`, `get_last_checkpoint()` — skip already-imaged ads on resume.
- **P0-08** (`iterate/retry.py`): `retry_with_backoff()` — handles Nano Banana Pro rate limits and API errors.
- **P0-10** (`generate/competitive.py`): `load_patterns()`, `query_patterns()`, `get_landscape_context()` — competitive visual patterns.
- **P1-01** (`generate/brief_expansion.py`): Expanded briefs — the input for visual spec extraction.
- **data/config.yaml**: All tunable parameters including API keys, model endpoints, `ledger_path`.

---

## What This Ticket Must Accomplish

### Goal

Build the visual spec extraction and image generation modules. Extract structured visual specs from expanded briefs. Generate 3 image variants per ad via Nano Banana Pro. Route aspect ratios (1:1 default, 4:5 + 9:16 for winners). Log everything to the ledger.

### Deliverables Checklist

#### A. Visual Spec Extractor (`generate/visual_spec.py`)

- [ ] `VisualSpec` dataclass
  - Fields: `subject` (demographic, activity, emotional expression), `setting` (location, lighting, time of day), `color_palette` (brand colors + mood accents), `composition` (rule of thirds, symmetry, framing), `campaign_goal_cue` (aspirational for awareness, action-oriented for conversion), `text_overlay` (headline if applicable), `aspect_ratio` (1:1 default), `negative_prompt` (no competitor branding, no AI artifacts), `ad_id`, `brief_id`
- [ ] `extract_visual_spec(expanded_brief: dict, campaign_goal: str, audience: str) -> VisualSpec`
  - Uses Gemini Flash to extract a structured visual spec from the expanded brief
  - Grounding constraint: visual spec must reference elements present in the expanded brief (no hallucinated visual concepts)
  - Injects brand color palette (Varsity Tutors teal/navy/white) as constraint
  - Campaign goal drives mood: awareness = aspirational/warm, conversion = action-oriented/urgent
  - Audience drives subject: parent-facing = family/study scenes, student-facing = peer/achievement scenes
  - Logs `VisualSpecExtracted` event to ledger with `tokens_consumed`
- [ ] `build_image_prompt(spec: VisualSpec, variant_type: str) -> str`
  - Converts visual spec into a text prompt for Nano Banana Pro
  - `variant_type` is one of: "anchor", "tone_shift", "composition_shift"
  - **Anchor:** Straight interpretation of the visual spec
  - **Tone shift:** Same subject/setting, adjusted emotional register (e.g., warmer lighting, more aspirational expression, softer palette)
  - **Composition shift:** Different framing (close-up vs. environment, single subject vs. group, centered vs. rule-of-thirds)
  - Appends negative prompt to all variants

#### B. Image Generator (`generate/image_generator.py`)

- [ ] `ImageVariant` dataclass
  - Fields: `ad_id`, `variant_type` (anchor | tone_shift | composition_shift), `image_path` (local file path), `aspect_ratio`, `visual_spec_hash`, `prompt_used`, `seed`, `tokens_consumed`, `timestamp`
- [ ] `generate_image(prompt: str, aspect_ratio: str, seed: int, output_dir: str) -> str`
  - Calls Nano Banana Pro (Gemini 3 Pro Image) API
  - Passes aspect ratio (1:1, 4:5, or 9:16) and seed for reproducibility
  - Saves image to `output_dir` with structured filename: `{ad_id}_{variant_type}_{aspect_ratio}.png`
  - Wrapped in `retry_with_backoff()` for rate limit handling
  - Returns the local file path of the saved image
- [ ] `generate_variants(visual_spec: VisualSpec, ad_id: str, seed: int, output_dir: str) -> list[ImageVariant]`
  - Generates all 3 variants (anchor, tone_shift, composition_shift) for a single ad
  - Default aspect ratio: 1:1 (from visual spec)
  - Each variant gets a derived seed: `seed + variant_offset` for reproducibility
  - Logs `ImageGenerated` event to ledger for each variant (with `tokens_consumed`, `variant_type`, `image_path`)
  - Returns list of 3 `ImageVariant` objects
- [ ] `generate_extra_ratios(image_variant: ImageVariant, ratios: list[str], output_dir: str) -> list[ImageVariant]`
  - For published winners only: regenerate the winning variant at 4:5 and 9:16
  - Uses the same prompt and seed as the original — only aspect ratio changes
  - Logs `ExtraRatioGenerated` event to ledger
  - Returns list of additional `ImageVariant` objects

#### C. Aspect Ratio Routing

- [ ] Default: all 3 variants generated at 1:1 (1080x1080)
- [ ] After Pareto selection (P1-15) and coherence check (P1-16), the winning variant gets regenerated at:
  - 4:5 (1080x1350) for feed placement
  - 9:16 (1080x1920) for Stories/Reels placement
- [ ] Meta-ready output specs (PRD Section 4.6.9):
  - Feed: 1:1 (1080x1080) or 4:5 (1080x1350), JPG/PNG
  - Stories/Reels: 9:16 (1080x1920), JPG/PNG

#### D. Ledger Events

- [ ] `VisualSpecExtracted` — logged when visual spec is extracted from brief. Fields: `ad_id`, `brief_id`, `spec_hash`, `tokens_consumed`.
- [ ] `ImageGenerated` — logged for each variant. Fields: `ad_id`, `variant_type`, `aspect_ratio`, `image_path`, `seed`, `tokens_consumed`.
- [ ] `ExtraRatioGenerated` — logged when winner is regenerated at additional ratios.
- [ ] All events include `checkpoint_id` for resume compatibility.

#### E. Tests (`tests/test_pipeline/test_image_generator.py`)

- [ ] TDD first
- [ ] Test `extract_visual_spec` returns all required fields from a mock expanded brief
- [ ] Test `build_image_prompt` produces different prompts for anchor vs. tone_shift vs. composition_shift
- [ ] Test `build_image_prompt` always includes negative prompt
- [ ] Test `generate_variants` produces exactly 3 variants with correct types
- [ ] Test variant seeds are deterministic and derived from base seed
- [ ] Test `generate_extra_ratios` produces variants at 4:5 and 9:16
- [ ] Test ledger events are logged for each generated image
- [ ] Test aspect ratio routing: default 1:1, extras only when explicitly requested
- [ ] Test API errors are retried via `retry_with_backoff()` (mock the API)
- [ ] Test `should_skip_ad()` integration: already-imaged ads are skipped on resume
- [ ] Minimum: 10+ tests

#### F. Documentation

- [ ] Add P1-14 entry in `docs/DEVLOG.md`

---

## Branch & Merge Workflow

All work is done directly on `develop`. No feature branches.

```bash
git switch develop && git pull
```

---

## Important Context

### Architectural Decisions

| Decision | Reference | Summary |
|----------|-----------|---------|
| Shared semantic brief | R1-Q10 | Visual spec extracted from the same expanded brief as copy — prevents incoherence by design. |
| Multi-variant generation | PRD 4.6.3 | 3 variants per ad: anchor, tone shift, composition shift. Pareto selection picks the best. |
| Visual spec extraction | PRD 4.6.2 | Structured spec: subject, setting, color palette, composition, campaign goal cue, text overlay, aspect ratio, negative prompt. |
| Aspect ratio routing | PRD 4.6.9 | 1:1 default. 4:5 + 9:16 for published winners only (cost-conscious). |
| Reproducibility | R3-Q4 | Per-ad seed chain. Variant seeds derived from base seed. Same seed = same image. |
| API resilience | R3-Q2 | `retry_with_backoff()` for Nano Banana Pro rate limits. Checkpoint after image batch. |
| Cost management | PRD 4.6.8 | ~$0.13/image. 50 ads x 3 variants = ~$20. Extra ratios for winners only. Hard cap: 5 images per ad (including regen in P1-17). |

### Files to Create

| File | Why |
|------|-----|
| `generate/visual_spec.py` | Visual spec extraction from expanded briefs |
| `generate/image_generator.py` | Nano Banana Pro API integration + multi-variant generation |
| `tests/test_pipeline/test_image_generator.py` | Image generation tests |

### Files You Should READ for Context

| File | Why |
|------|-----|
| `generate/brief_expansion.py` | The expanded brief is the input for visual spec extraction |
| `generate/seeds.py` | Seed chain for reproducible image generation |
| `iterate/ledger.py` | Event logging for all image events |
| `iterate/retry.py` | `retry_with_backoff()` wraps all API calls |
| `iterate/checkpoint.py` | `should_skip_ad()` for resume — skip already-imaged ads |
| `data/config.yaml` | API configuration, output paths |
| `docs/reference/prd.md` (Section 4.6) | Full image generation architecture |

---

## Definition of Done

- [ ] `extract_visual_spec()` produces structured specs from expanded briefs
- [ ] `generate_variants()` produces 3 image variants (anchor, tone_shift, composition_shift) per ad
- [ ] All 3 variants saved locally with structured filenames
- [ ] `generate_extra_ratios()` produces 4:5 and 9:16 variants for winners
- [ ] All image events logged to ledger with `tokens_consumed` and `checkpoint_id`
- [ ] Visual specs logged to ledger
- [ ] API calls wrapped in `retry_with_backoff()`
- [ ] Seeds are deterministic — same seed + same spec = same image
- [ ] Tests pass
- [ ] Lint clean
- [ ] DEVLOG updated
- [ ] Committed on `develop`

---

## Estimated Time: 90–120 minutes

---

## After This Ticket: What Comes Next

- **P1-15** (Visual attribute evaluator + Pareto image selection) — Score each variant against the 10-attribute checklist. Pareto-select the best variant per ad.
- **P1-16** (Text-image coherence checker) — 4-dimension coherence score. Below 6 = incoherent. Feeds Pareto selection (60% weight).
- **P1-17** (Image targeted regen loop) — All 3 fail attribute checklist → diagnose + 2 regen. Coherence-only fail → 1 regen. Max 5 images per ad.
- **P1-18** (Full ad assembly + export) — Combine copy JSON + winning image + variant metadata into Meta-ready output.
- **P1-19** (Image cost tracking) — Per-image, per-variant, per-regen cost attribution.
