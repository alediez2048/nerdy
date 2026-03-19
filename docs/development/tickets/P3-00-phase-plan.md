# Phase P3: A/B Variant Engine + UGC Video

## Context

P3 extends the pipeline from single-best-ad output to multi-variant experimentation and multi-format output. A/B variants isolate which creative elements drive performance. UGC video (now via Kling 2.6) unlocks Stories/Reels placements as a **separate session track** from image ads. This is v2 scope — impressive but not required for the rubric.

## Tickets (13 original + 4 simplified PC)

### A/B Variant Track (P3-01 through P3-06)

### P3-01: Nano Banana 2 Integration (Cost Tier)
- Add Gemini 3.1 Flash Image as cheap alternative to Pro for variant volume
- **AC:** Both models producing, cost tracked separately

### P3-02: Single-Variable A/B Variants — Copy
- Control + 3 copy variants changing one element (hook, emotion, CTA)
- **AC:** Winning patterns identified per segment

### P3-03: Single-Variable A/B Variants — Image
- Same copy + 3 image variants isolating visual impact
- **AC:** Image variants produced, coherence compared

### P3-04: Image Style Transfer Experiments
- Different styles per audience (photorealistic, illustrated, lifestyle, editorial)
- **AC:** Style-audience mapping documented

### P3-05: Multi-Model Orchestration Doc
- Document which model does what and why; cost attribution across text + image + video
- **AC:** Architecture doc with rationale across all formats

### P3-06: Multi-Aspect-Ratio Batch Generation
- For published ads: 1:1, 4:5, 9:16 variants all passing attribute checklist
- **AC:** All 3 ratios per published ad

### Video Track — Phase PC (4 tickets, replaces P3-07 through P3-13)

**Key design changes from original P3-07–P3-13:**
- **Kling 2.6 replaces Veo** — better rate limits, pricing ($0.049/sec vs $0.15/sec), native audio, negative prompt support
- **Separate session track** — video sessions are independent from image sessions (different form, different pipeline, different output)
- **8-part prompt framework** — video form uses scene/style/camera/subject/setting/lighting/audio/color fields (simple mode + advanced accordion)
- **Dedicated video evaluator** — not an extension of the image evaluator

### PC-00: Session Type + Schema Foundation
- Add `session_type` (image/video) to SessionConfig and form
- Video form: simple mode (persona, key message, audio, duration) + advanced accordion (8-part framework)
- Session list: type badge + filter
- **AC:** Form toggles between image and video modes; image sessions unchanged

### PC-01: Kling 2.6 Client + Video Spec Builder
- `generate_video/kling_client.py`: async task-based Kling API client (submit → poll → download)
- `generate_video/video_spec.py`: VideoSpec dataclass, `build_video_spec()` (auto-derive or use explicit fields), `build_kling_prompt()` (8-part framework)
- Rate limiter, retry logic, brand safety negative prompt
- **AC:** Client can generate videos; spec builder produces 100–150 word prompts

### PC-02: Video Pipeline + Evaluation
- `generate_video/orchestrator.py`: 2 variants per ad (anchor + alternative), `run_video_pipeline()`
- `evaluate/video_evaluator.py`: 5 attributes + 4-dimension coherence (threshold 4.0, not 6.0)
- Graceful degradation: missing files handled, correct ledger semantics
- Checkpoint-resume for video ads
- **AC:** Pipeline generates, evaluates, selects videos; failures degrade to copy-only

### PC-03: App Integration + Video Assembly
- Celery task routing by `session_type` (video → video pipeline, image → image pipeline)
- `output/video_assembler.py`: copy + video output (no image in video track)
- Frontend: video player in Ad Library, video-specific progress stages
- Static video file serving
- **AC:** Video sessions run end-to-end in the app; Ad Library shows video player

See `docs/development/tickets/PC-00-primer.md` through `PC-03-primer.md`.

## Dependency Graph

```
A/B Track (parallel, independent of video):
P3-01 (NB2) ─┐
P3-02 (Copy AB) ─┤── A/B track
P3-03 (Image AB) ─┤
P3-04 (Style Transfer) ─┘
         │
P3-05 (Orchestration Doc)
P3-06 (Multi-Ratio)

Video Track (sequential):
PC-00 (Schema + Form) → PC-01 (Kling Client) → PC-02 (Pipeline + Eval) → PC-03 (App Integration)
```

A/B track and Video track are **independent** — can be done in any order.

## Rubric Impact

- **Not required for submission** — rubric scores pipeline quality, iteration, evaluation, docs
- **Bonus points:** +3 for multi-model orchestration, +2 for quality visualization
- **Demo value:** High — "the system supports two independent creative tracks with different AI models" is a strong story

## Status: 🔄 IN PROGRESS (PC tickets rewritten for Kling + separate tracks)
