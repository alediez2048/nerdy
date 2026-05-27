# PI Phase Plan: Unified Media Quality Evaluator

**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** 2026-05-15
**Previous work:** P0–P5, PA, PB, PC, PD, PF, PG, PH complete. See `docs/development/DEVLOG.md`.
**Status:** Design approved (pending final spec review) — implementation tickets PI-01..PI-N to follow via writing-plans skill.
**Approach chosen:** B (unified evaluator, FB-native rubric) + Option II (image + video in one design)
**Successor to:** `evaluate/image_evaluator.py`, `evaluate/coherence_checker.py`, `evaluate/image_scorer.py`, `evaluate/video_evaluator.py`, `evaluate/video_attributes.py`, `evaluate/video_scorer.py`

---

## 1. Problem statement

Three layered defects discovered in the existing image + video scoring pipeline, all evidence-verified against the production ledger (228 image variants across 19 sessions; 251 video evaluation events across 17 sessions):

### Defect 1 — Coherence signal is hardcoded for 100% of variants

In `iterate/batch_processor.py:408`:
```python
coherence_avg = coherence.average if hasattr(coherence, "average") else 0.5
```

The `CoherenceResult` dataclass field is named `coherence_avg`, not `average` (see `evaluate/coherence_checker.py:120`). `hasattr` always returns `False`, so the literal `0.5` is used. Then line 409 divides by 10, contributing a constant `0.03` to every composite. The Gemini multimodal coherence call runs (and costs tokens) for every variant — its output is then thrown away.

Verified: across **228 image variants in 19 sessions, `coherence_avg = 0.5` for every single one**. Video has a parallel pattern: **82 `VideoCoherenceChecked` events stuck at `coherence_avg = 5.0`** (mid-range default-on-error).

The composite math collapses to `composite = 0.4 × attribute_pass_pct + 0.03`, so 60% of the discriminating signal is dead.

### Defect 2 — The remaining 40% signal has only 6 possible values

`evaluate/image_evaluator.py` returns `attribute_pass_pct = pass_count / 5`, restricted to `{0.0, 0.2, 0.4, 0.6, 0.8, 1.0}`. In practice across all 228 variants, **84% land at either `0.8` or `1.0`**. The five binary attributes are also "soft" (e.g. "is the lighting warm/inviting?") and a silent API error defaults all five to `True`, so most images are 4/5 or 5/5 by construction.

### Defect 3 — Variant rationales are computed but never persisted

For each variant the pipeline already produces:

- per-attribute booleans (`{age_appropriate: true, lighting: false, ...}`)
- per-coherence-dimension 1-10 scores (`{message_alignment: 7, ...}`)

…but the `ImageEvaluated` ledger event only writes three numbers: `attribute_pass_pct`, `coherence_avg`, `composite_score` (`batch_processor.py:431-435`). The detail is lost.

The 1-10 rich rationale that does appear in the dashboard (`visual_clarity`, `brand_consistency`, etc.) comes from a **third, separate evaluator** — `evaluate/image_scorer.py` — that runs **only on the post-selection winner** (`batch_processor.py:243`). So the rationale you can see has zero influence on which variant was picked.

### User-facing consequence

For the most recent real session (`sess_f71c27911fe08803`, 5 ads × 3 variants = 15 images):
- 8 of 15 scored `0.35`
- 6 of 15 scored `0.27`
- 1 scored `0.19`

Three distinct composite values, decided by a 4-vs-5 attribute count from a checklist where most items default to True. Operator's complaint — "scoring was about the same for almost 6 of those images, with no way to understand the context" — is literally describing this collapse.

---

## 2. Goals & non-goals

### Goals

1. **Granularity:** the new evaluator must produce **≥8 distinct composite values across a 15-variant batch** (vs. today's 3).
2. **Best-practice alignment:** the rubric must reflect publicly-documented Meta / FB creative best practices, not generic image-quality heuristics.
3. **Rationale persistence:** every variant carries per-dimension scores + LLM-authored rationales in the ledger, accessible from the UI.
4. **One source of truth:** a single module emits the score that drives selection AND the rationale shown to the operator. No drift between "the score that won" and "the score we explain".
5. **Image + video unified:** one module, one event shape, one UI surface; media-specific dimensions and penalty gates are configured per `media_type`.
6. **Cheaper, not more expensive:** consolidating today's two-call-per-variant flow into one call should net-decrease per-session evaluation cost.

### Non-goals (out of this design)

- Auto-calibration of dimension weights from performance data (deferred to Approach C / a future PF-phase ticket).
- Feature flagging or parallel-run rollout — current path is broken enough that hard cutover is safer than a gated migration.
- Re-evaluation / backfill of the 19 historical sessions. They stay readable with their existing (broken) scores and a "Legacy scoring" badge.
- Changing how images / videos are *generated* (PH-06 ImageModelRouter, Veo pipeline) — only how they are *evaluated*.

---

## 3. Decisions log

The load-bearing decisions, captured to prevent re-litigation mid-implementation:

1. **Unified module name:** `evaluate/media_quality.py`. Selector keeps its file name but is renamed internally: `evaluate/image_selector.py` → `evaluate/media_selector.py` (filename stays for now to minimize import churn; rename later).
2. **Ledger event:** new `MediaEvaluation` event class in `iterate/ledger_events.py`. Old `ImageEvaluated`, `ImageScored`, `VideoEvaluated`, `VideoCoherenceChecked`, `VideoScored` classes stay defined so historical ledgers parse cleanly, but no new code writes them.
3. **Backward compat:** hard cutover. New sessions emit `MediaEvaluation` v2 only. Dashboard `/variants` endpoint branches on `schema_version`; legacy sessions render with a `Legacy scoring (pre-2026-05-15)` badge and no Evidence panel.
4. **Model:** Gemini 2.5 Flash for per-variant evaluation (workhorse). Gemini 2.5 Pro one-time for golden-set calibration. No Pro per-variant.
5. **Rubric is hand-weighted, not data-driven (this round).** Dimension weights are set from Meta's published creative best-practices guidance and IPA dataBANK effectiveness findings; the calibration test verifies spread but does not auto-tune.
6. **Penalty gates are multipliers, not hard fails.** A triggered gate caps composite at `raw_score × gate_cap × 100` so a partially-flawed variant remains comparable and selectable, just lower-scored.
7. **6 modules retired in this change.** No "deprecation period" — once `MediaEvaluation` is writing cleanly and tests are green, the six legacy modules are deleted in the same merge.
8. **`frame_extractor.py` is kept** — useful when a video file is too large to upload directly (we fall back to N evenly-spaced frames).

---

## 4. Architecture

### Module layout

```
evaluate/
  media_quality.py         # NEW — single evaluator for image and video
  media_selector.py        # was image_selector.py, expanded
  frame_extractor.py       # KEPT — used as fallback for large video uploads

  # RETIRED at end of this change:
  image_evaluator.py       # 5-binary attribute checklist
  coherence_checker.py     # 4-dim image coherence
  image_scorer.py          # 5-dim post-hoc image scorer
  video_evaluator.py       # video attribute + coherence
  video_attributes.py      # 10-attribute placeholder (always returns True)
  video_scorer.py          # 5-dim post-hoc video scorer
```

### Per-variant call shape

For each variant (image or video):

```
generate variant  →  upload to Gemini 2.5 Flash multimodal  →
  evaluate (one call, returns all dimensions + gates + rationales) →
  compute composite (raw_score × penalty_mult × 100) →
  write MediaEvaluation event to ledger
```

**One Gemini call per variant** (was two: attribute + coherence). Same call returns all 8 (image) or 10 (video) dimension scores, all 3 (image) or 5 (video) penalty gate evaluations, and a rationale per dimension and per gate.

### Pipeline integration

`iterate/batch_processor.py:_generate_and_select_image` is rewritten to:

1. Call `generate_variants` (unchanged)
2. For each variant: `evaluate_media(path, ad_copy, brief, media_type="image")` → `MediaEvaluation`
3. Write the `MediaEvaluation` event
4. Call `select_best_variant(evaluations)` from `media_selector` → `SelectionResult`
5. Log the `SelectionResult` (replaces today's selection logging)

The video pipeline (`generate_video/`) gets the equivalent treatment — see §10 for the missing-file root-cause fix that's bundled.

---

## 5. Rubric

### Shared dimensions (apply to both image and video)

| Dimension | Image weight | Video weight | Why (FB / IPA / Meta Creative Hub) |
|---|---|---|---|
| `thumb_stop_potential` | 0.20 | 0.15 | Meta's #1 metric: does it stop the scroll in the first 0.3s? Strongest performance correlate. Slightly lower for video — `hook_in_3s` carries part of this. |
| `brand_consistency` | 0.10 | 0.10 | Brand recall in first 3s correlates with ad-recall lift. |
| `emotional_impact` | 0.15 | 0.10 | Emotional ads outperform rational ones 2:1 per IPA dataBANK. Video distributes emotional load across motion + pacing + audio, so the single dimension carries less. |
| `message_alignment` | 0.10 | 0.10 | Visual must reinforce headline, not contradict. |
| `audience_match` | 0.10 | 0.10 | Demographic + persona fit (e.g. parent of HS student, not child). |
| `production_quality` | 0.10 | 0.05 | Generic "looks professional?" — composition, color balance, no obvious AI tells. Video relies on `motion_quality` for most of this judgment. |

### Image-only dimensions

| Dimension | Image weight | Why |
|---|---|---|
| `mobile_legibility` | 0.15 | 98% of FB/IG traffic is mobile; key elements must read at 320px width. |
| `single_focal_point` | 0.10 | Competing subjects = lost attention; Meta Creative Hub guidance. |

### Video-only dimensions

| Dimension | Video weight | Why |
|---|---|---|
| `hook_in_3s` | 0.15 | Meta's published #1 video metric: ≥65% completion correlates with strong 3s hook. |
| `pacing` | 0.10 | Dead frames kill retention; matches energy spec set by the brief. |
| `motion_quality` | 0.10 | Veo / Sora outputs sometimes jank or morph; bad motion → trust loss. |
| `audio_appropriateness` | 0.05 | If audio present, fits tone; if silent, silence is intentional. |

### Dimension count and weight verification

- Image: 6 shared + 2 image-only = **8 dimensions**, weights sum to **1.00** (0.20 + 0.10 + 0.15 + 0.10 + 0.10 + 0.10 + 0.15 + 0.10)
- Video: 6 shared + 4 video-only = **10 dimensions**, weights sum to **1.00** (0.15 + 0.10 + 0.10 + 0.10 + 0.10 + 0.05 + 0.15 + 0.10 + 0.10 + 0.05)

### Per-dimension prompt contract

Every dimension returns:
```json
{ "score": <integer 1-10>, "rationale": "<1-2 sentences naming the specific image/video element>" }
```

The prompt explicitly forces concreteness: *"In each rationale, name a specific visual element that earned this score. Generic statements like 'good composition' will be rejected."*

---

## 6. Penalty gates

Gates are evaluated by the same multimodal call as the dimensions. Each gate is a binary "triggered / not triggered" with a one-sentence rationale.

### Shared gates (both media)

| Gate | Cap | Why |
|---|---|---|
| `has_ai_artifacts` | × 0.5 | Warped hands, mangled text, impossible geometry. Killer for trust; Meta auto-flags some. |
| `has_uncanny_faces` | × 0.6 | Subtle face wrongness. Lowers CTR via "weird vibes". **High false-negative rate caveat below.** |
| `brand_safety_violation` | × 0.3 | Competitor logos, inappropriate context. Hard signal for paid media. |

### Video-only gates

| Gate | Cap | Why |
|---|---|---|
| `has_temporal_artifacts` | × 0.4 | Flickering, frame jumps, faces morphing across cuts. Unique to video — distinct from `has_ai_artifacts`. |
| `has_pacing_dead_zones` | × 0.7 | Long static moments where nothing happens. Soft cap because pacing is subjective. |

### How multiple triggered gates combine

If multiple gates trigger, **only the most severe cap applies** (i.e. `penalty_multiplier = min(triggered_caps)`). This is intentional: an image with both `has_ai_artifacts` and `has_uncanny_faces` is bad once, not twice; a single severe penalty represents the reality.

### Known caveat on `has_uncanny_faces`

LLM vision models (including Gemini 2.5 Flash) reliably detect "is this a face" but are less reliable at "is this a subtly-wrong face". This gate is expected to have a high false-negative rate. It's still worth keeping for the obvious cases (asymmetric pupils, melted features), but the spec acknowledges this is the weakest signal in the rubric. Mitigation deferred (could add a secondary face-symmetry classifier in a follow-up).

---

## 7. Composite math

```
raw_score        = Σ (weight_i × dimension_score_i) / 10          # 0.0–1.0
penalty_mult     = min(triggered_gate_caps)  or  1.0 if no gate triggered
composite_score  = raw_score × penalty_mult × 100                 # 0–100 integer
```

### Granularity calculation

- 8 dimensions (image) × 10 score levels × hand-tuned weights → roughly 30–50 realistically reachable composite values
- × 4 distinct penalty multipliers (1.0, 0.6, 0.5, 0.3) → roughly 120+ distinguishable composites
- Video: 10 dimensions × 10 score levels × 6 penalty multipliers → even higher

Well beyond the "≥8 distinct composites across 15 variants" granularity target.

### Spread-protection signal

If a 15-variant batch yields fewer than 8 distinct composites, the pipeline emits an `ImageScoreVarianceLow` ledger warning event and the calibration test (§11) fails CI. This is the early-warning system for prompt drift or LLM lobotomization between model snapshots.

---

## 8. Ledger event schema v2

```jsonc
{
  "event_type": "MediaEvaluation",
  "schema_version": "v2",
  "ad_id": "ad_brief_001_c0_2888205907",
  "brief_id": "brief_001",
  "cycle_number": 0,
  "variant_type": "anchor",                  // anchor | tone_shift | composition_shift
  "media_type": "image",                     // "image" | "video"
  "media_path": "output/images/ad_brief_001_c0_2888205907_anchor_1x1.png",
  "media_metadata": {                        // present only when media_type == "video"
    "duration_s": 12.4,
    "resolution": "1080x1920",
    "fps": 30
  },
  "model_used": "gemini-2.5-flash",
  "tokens_consumed": 1820,
  "prompt_version": "media_quality.v2",      // bumped on any prompt change

  "dimensions": {
    "thumb_stop_potential": {
      "score": 7, "weight": 0.20,
      "rationale": "Strong colour contrast pulls the eye to the student's face, but the before/after split dilutes immediate impact."
    },
    "mobile_legibility": {
      "score": 5, "weight": 0.15,
      "rationale": "Headline reads at 320px; body copy is borderline."
    }
    // ... 6 more for image, 8 more for video
  },

  "penalty_gates": {
    "has_ai_artifacts":         {"triggered": false, "rationale": "No visible warping."},
    "has_uncanny_faces":        {"triggered": true,  "rationale": "Tutor's eyes have asymmetric pupil sizes."},
    "brand_safety_violation":   {"triggered": false, "rationale": "No competitor imagery."}
    // ... 2 more for video
  },

  "raw_score": 0.58,
  "penalty_multiplier": 0.6,
  "composite_score": 34.8
}
```

### Failure event (video-specific, replaces the 82 zero-score `VideoEvaluated` ghosts)

```jsonc
{
  "event_type": "MediaEvaluationFailed",
  "schema_version": "v2",
  "ad_id": "...",
  "variant_type": "anchor",
  "media_type": "video",
  "media_path": "...",
  "failure_reason": "file_not_found" | "upload_too_large" | "llm_call_failed" | "json_parse_failed",
  "error_message": "...",
  "tokens_consumed": 0
}
```

A failed variant is excluded from selection. If *all* variants for an ad fail, the ad is marked for regeneration (existing P1-08 brief mutation flow).

---

## 9. Selection algorithm

`evaluate/media_selector.py:select_best_variant(evaluations)`:

```python
def select_best_variant(evaluations: list[MediaEvaluation]) -> SelectionResult:
    valid = [e for e in evaluations if not e.failed]
    if not valid:
        return SelectionResult(winner=None, losers=[], all_failed=True)

    winner = max(valid, key=lambda e: e.composite_score)
    losers = [e for e in valid if e is not winner]

    # Build winner_reason: top 2 dimensions where winner outscored the mean of losers.
    # Edge case: if only one variant survived (losers empty), distinguishing
    # dimensions are the winner's top-2 absolute scores instead.
    if losers:
        delta_by_dim = {
            dim: winner.dimensions[dim].score - mean(loser.dimensions[dim].score for loser in losers)
            for dim in winner.dimensions
        }
        top_dims = sorted(delta_by_dim, key=delta_by_dim.get, reverse=True)[:2]
        distinguishing = [
            {"dimension": d, "delta_vs_mean": round(delta_by_dim[d], 2)}
            for d in top_dims
        ]
    else:
        top_dims = sorted(winner.dimensions, key=lambda d: winner.dimensions[d].score, reverse=True)[:2]
        distinguishing = [
            {"dimension": d, "absolute_score": winner.dimensions[d].score, "note": "only valid variant"}
            for d in top_dims
        ]

    winner_reason = WinnerReason(
        composite_score=winner.composite_score,
        distinguishing_dimensions=distinguishing,
    )

    # Build rejection_reason per loser: their worst dimension delta vs winner
    rejection_reasons = {}
    for loser in losers:
        deltas = {
            dim: loser.dimensions[dim].score - winner.dimensions[dim].score
            for dim in loser.dimensions
        }
        worst_dim = min(deltas, key=deltas.get)
        rejection_reasons[loser.variant_type] = RejectionReason(
            composite_delta=round(loser.composite_score - winner.composite_score, 2),
            worst_dimension=worst_dim,
            worst_dimension_delta=round(deltas[worst_dim], 2),
            worst_dimension_rationale=loser.dimensions[worst_dim].rationale,
        )

    return SelectionResult(winner=winner, losers=losers, winner_reason=winner_reason, rejection_reasons=rejection_reasons)
```

Tie-breaking: highest composite wins; on exact tie, first variant in list (stable sort, current behavior preserved).

---

## 10. UI changes (`app/frontend/src/components/VariantsPanel.tsx`)

### Per-variant card

- **Winner card** adds a `Why this won:` line under the existing label:
  > "Top vs mean of other variants — `thumb_stop_potential +2.3`, `emotional_impact +1.8`."
- **Loser card** keeps its `Lost on …` line, now referencing the worst dimension by name:
  > "Lost on `mobile_legibility`: 4 vs 8 (composite −18.4). *Headline overlaps the student's face at mobile sizes.*"

### Evidence panel (new, collapsible)

Below each card, an Evidence expander revealing:

- A table of all 8 (image) or 10 (video) dimensions: score · weight · 1-2 line rationale
- A table of triggered penalty gates: name · cap · rationale
- The composite math line: `raw 0.58 × penalty 0.6 = composite 34.8`

### Legacy-session badge

If the API returns `schema_version != "v2"` for a session's variants, the panel shows:

> "Legacy scoring (pre-2026-05-15) — per-dimension breakdown not available for this session."

…and the Evidence expander is hidden. The two-axis (`attribute_pass_pct`, `coherence_avg`) display from the old contract continues to render for legacy sessions.

### Video sessions unblocked

Today `VariantsPanel` is hidden for video sessions (commit `2c527e8`). The unified `media_type` field lets the same component render video variants — video thumbnails come from the existing `frame_extractor` first-frame fallback if no poster exists. This unblocks video sessions in the Ad Library as a side effect.

---

## 11. Calibration golden set

### Composition

- **12 reference images** — 4 obviously-great, 4 mediocre, 4 obviously-bad. Sourced from past Veo / Nano Banana Pro runs where possible; supplemented with hand-curated examples.
- **8 reference videos** — 3 great, 3 mid, 2 bad. Sourced from past Veo runs; the videos with known `temporal_artifacts` triggers are intentionally included.

### Test file

`tests/test_evaluation/test_media_quality_calibration.py`:

| Assertion | Image | Video |
|---|---|---|
| `obviously-great` composite > 70 | ✓ | ✓ |
| `obviously-bad` composite < 35 | ✓ | ✓ |
| within a tier, `max − min ≥ 10` (spread) | ✓ | ✓ |
| across all reference media, ≥ 8 distinct composites | image: ≥8 | video: ≥6 (smaller pool) |
| `has_ai_artifacts` correctly triggered on the planted bad cases | ✓ | ✓ |

### Test marker

`@pytest.mark.calibration` — opt-in, only runs when `GEMINI_API_KEY` is set. Not part of the default CI gate; runs nightly and on prompt changes.

### Why this is single-test, not per-dimension

A per-dimension assertion ("`thumb_stop_potential` ≥ 7 for great images") would be over-fitting the prompt. The spread + tier-separation contract is what we actually need: relative ranking is preserved, the rubric discriminates, scores stay calibrated as Google updates Gemini snapshots.

---

## 12. Model selection

| Use | Model | $/call | Latency | When |
|---|---|---|---|---|
| Per-variant image evaluation (15/run) | **Gemini 2.5 Flash** | ~$0.002 | 2–3s | Every pipeline run |
| Per-variant video evaluation (5–10/run) | **Gemini 2.5 Flash** | ~$0.01–0.02 | 5–15s | Every video pipeline run |
| Golden-set ceiling (one-time, 20 media) | Gemini 2.5 Pro | ~$0.02 | 5–10s | Spec finalization + on prompt changes |
| (Future) Tiebreaker for close composites | Claude Sonnet 4.6 multimodal | ~$0.04 | 3–5s | **Out of scope** for v2 |

### Net cost impact

Old image evaluation: 2 calls × 15 variants × ~$0.0015 = **~$0.045/session**
New image evaluation: 1 call × 15 variants × ~$0.002 = **~$0.030/session**

**33% cheaper per session** for image. Video evaluation cost roughly flat (one call replaces two but the unified call is bigger).

### Honest model assessment (recorded for posterity)

Gemini 2.5 Flash is **strong** at: focal point identification, on-image text reading, demographic classification, brand color detection, blatant AI artifacts, following structured JSON output.

It is **decent** at: emotional impact scoring, composition/scroll-stopping judgment, mobile-legibility judgment, rationale specificity (with prompt forcing).

It is **weak** at: subtle uncanny-face detection (high false-negative rate), cross-call calibration stability (drifts ±0.5–1.0 per dimension), avoiding central-tendency bias (without explicit "be strict" prompting, clusters at 6–7), audio judgment for video (audio analysis is a known multimodal weak spot).

Mitigations: calibration test catches drift; prompt enforces strictness; selection ranks relatively (relative ranking is much more stable than absolute scores).

---

## 13. Migration & rollout

### Plan

1. Land `media_quality.py` + `media_selector.py` + ledger event class behind tests.
2. Switch `batch_processor._generate_and_select_image` to call the new path.
3. Switch the video pipeline (in `generate_video/`) to call the new path; fix the missing-file root cause as part of the same change (see Bonus fixes §14).
4. Update dashboard `/variants` endpoint to emit v2 shape; legacy events still readable via `schema_version` branch.
5. Update `VariantsPanel` for v2 shape; legacy badge for old sessions.
6. Delete the 6 retired modules and their tests; keep the new ones.
7. Run a fresh end-to-end pipeline session against staging data; verify granularity target (≥8 distinct composites across 15 variants).
8. Tag the pre-rework SHA before merging to `main` for fast rollback.

### Rollout posture

Hard cutover. No feature flag. The current path is broken (60% signal dead, 100% of variants stuck at the same coherence); running both adds confusion. The legacy-session badge in the UI handles backward visualization.

### Rollback

If granularity target fails or production sessions regress: revert the merge. Old `ImageEvaluated` / `VideoEvaluated` / `ImageScored` writes resume immediately; dashboard reads continue to work because we never deleted the legacy event classes.

---

## 14. Bonus fixes (forced by unified scope)

1. **Delete `evaluate/video_attributes.py:99-104` placeholder code** — the function literally always returns `passed=True` regardless of input. Documented as a placeholder in 2026-04; never replaced. Deletion is part of retiring the module.
2. **Fix the 82 missing-file ghost events** in the video ledger. Root cause investigation lands as part of the video pipeline wiring: identify whether files are being deleted, never written, or written to a path the evaluator doesn't check, then fix. Failure case becomes an explicit `MediaEvaluationFailed` event (§8) instead of polluting `VideoEvaluated` with zero-scores.
3. **Unblock video sessions in `VariantsPanel`** — currently hidden for video sessions (commit `2c527e8`); unified `media_type` handling removes the hide condition.

---

## 15. Test plan

### New unit tests (full TDD)

- `tests/test_evaluation/test_media_quality.py` — 15+ unit tests covering:
  - prompt build for image and video (correct dimensions, weights, gate descriptions)
  - response parser (handles markdown fences, partial responses, missing dimensions, malformed JSON)
  - composite math (weighted sum, penalty multiplier cascade, single-cap rule)
  - failure paths (file missing, upload failed, parse failed) → `MediaEvaluationFailed` event
  - rationale specificity check (rejects generic strings — but as a soft warning, not hard fail)
- `tests/test_evaluation/test_media_selector.py` — 8+ unit tests covering:
  - winner picked by highest composite
  - tie-break (first wins, stable sort)
  - winner_reason names top 2 distinguishing dimensions
  - rejection_reason names worst-delta dimension and pulls its rationale
  - `all_failed=True` when no variants are valid

### Calibration test

- `tests/test_evaluation/test_media_quality_calibration.py` — single integration test, opt-in via `@pytest.mark.calibration`, runs against real Gemini API on 12 reference images + 8 reference videos. Spec details in §11.

### Tests to migrate / retire

- `tests/test_pipeline/test_image_evaluator.py` (15 tests) — partially migrated; structural assertions move to `test_media_quality.py`; tests of binary-attribute behavior are retired.
- `tests/test_pipeline/test_coherence_checker.py` (~10 tests) — same.
- `tests/test_pipeline/test_image_scorer.py` (~10 tests) — same.
- `tests/test_pipeline/test_video_evaluator.py`, `test_video_attributes.py`, `test_video_scorer.py` — same.
- Net: 6 test files deleted, 2 new test files added. Total test count slightly lower; coverage higher.

### Dashboard / API tests

- `tests/test_app/test_dashboard_variants_v2.py` — new tests covering v2 endpoint shape (8 / 10 dimensions, gates, schema_version, winner_reason / rejection_reasons).
- Legacy-session test: confirm a v1 session still returns the old shape and is flagged `schema_version: "v1"`.

### Frontend smoke tests

- `app/frontend/src/components/VariantsPanel.test.tsx` (or equivalent) — render v2 fixture (with Evidence panel), render v1 fixture (with legacy badge). No business-logic test; the math is in Python.

### End-to-end check

- Run `python run_pipeline.py --max-ads 5` (real Gemini calls) against a fresh staging session, open the Ad Library, confirm:
  - Composite scores span ≥8 distinct values across 15 variants
  - Each variant card's Evidence expander shows 8 dimensions with non-generic rationales
  - Winner card shows distinguishing dimensions
  - Cost panel reconciles (PH-02 still works)
- Same for a video session with 5 video variants.

---

## 16. Effort breakdown

| Phase | Effort |
|---|---|
| `media_quality.py` module + 15+ unit tests | 8h |
| `media_selector.py` + 8+ unit tests | 3h |
| Batch processor wiring for image path | 3h |
| Video pipeline wiring + missing-file root-cause fix | 7h |
| Dashboard endpoint v2 branch (both media) | 3h |
| `VariantsPanel` UI update for both + Evidence panel + legacy badge + video unblock | 5h |
| Calibration golden set assembly (12 images + 8 videos) + calibration test | 5h |
| Retire 6 legacy modules + clean up associated tests | 3h |
| End-to-end run, dashboard sanity, debugging | 6h |
| Manual ledger reconciliation + spread check on real session | 2h |
| **Total** | **~45 hours / 5 days focused** |

---

## 17. Open risks

| Risk | Mitigation |
|---|---|
| Calibration test fails on first run (rubric too strict / too lenient) | Iterate prompt wording with golden set; expect 2–3 cycles. Budget 4h for prompt-tuning. |
| Gemini 2.5 Flash drift between snapshots silently shifts scores | Calibration test is the canary; rerun on every prompt change and weekly in CI. |
| Video upload size limits hit on long Veo outputs | Fall back to `frame_extractor.extract_key_frames(N=6)` and send frames instead of the full video. |
| Missing-file root cause in video pipeline turns out to be a deep issue | Time-box to 4h; if it's deeper than a config / path bug, ship the new evaluator with the explicit `MediaEvaluationFailed` event surface and file a follow-up ticket for the file-flow fix. |
| Old dashboard URLs break for users mid-session | Hard cutover only affects new sessions; existing session URLs render legacy shape with badge. |

---

## 18. Out of scope (explicitly)

- Auto-recalibration of dimension weights from PF performance data (Approach C / future)
- A second-opinion tiebreaker call (Claude Sonnet 4.6) for close composites
- Re-evaluation or backfill of the 19 historical sessions
- Changing how variants are generated (anchor / tone-shift / composition-shift logic preserved)
- Audio-only evaluation (we use audio_appropriateness as a soft signal but don't independently analyze audio tracks)
- A secondary uncanny-face classifier to address the known weak spot — deferred to a future ticket if the false-negative rate proves problematic in practice

---

## 19. Self-check

- All three defects from Phase 1 investigation are addressed: Defect 1 (typo) is replaced by a unified single-source-of-truth call; Defect 2 (6-bucket signal) is replaced by 8/10 dimensions × 10 levels × penalty multipliers; Defect 3 (no rationale persistence) is fixed by the v2 ledger event + UI Evidence panel.
- Image and video share one module, one event shape, one UI surface — no future drift.
- Backward compatibility is preserved: old ledgers parse, old sessions render with a clear badge.
- The granularity claim (≥8 distinct composites across 15 variants) is testable, locked in by `test_media_quality_calibration.py`, and fails loud if drift creeps in.
- Cost goes down 33% for image, stays flat for video. Latency rises slightly per call but total per-variant time falls because we removed one round-trip.
- Rollout is reversible: revert the merge → legacy classes resume writing → old dashboard contract still works.
