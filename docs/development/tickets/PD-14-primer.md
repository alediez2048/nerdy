# PD-14: Video Quality Scorer — 5-Dimension Video Evaluation

## Goal
Replace the binary pass/fail video attribute check with a rich 5-dimension scoring system (1-10 scale) using Gemini multimodal video understanding. Matches the scoring depth of copy (PD existing) and images (PD-13).

## The Problem
Video evaluation today uses 5 binary attributes (hook_timing, ugc_authenticity, pacing, text_legibility, no_artifacts) + 4-dimension coherence (message_alignment, audience_match, emotional_consistency, narrative_flow). The composite score mixes 0-1 and 1-10 scales, and there's no dimensional richness — no way to say "this video has great hook strength but poor narrative flow."

## 5 Dimensions (1-10 scale each)

| Dimension | What it measures | Low score (1-3) | High score (8-10) |
|-----------|-----------------|-----------------|-------------------|
| **Hook Strength** | Do the first 2 seconds grab attention? | Slow start, nothing compelling in opening frames | Immediate visual hook, curiosity or emotion in first 2s |
| **Visual Quality** | Clean motion, good lighting, no artifacts? | Glitchy, blurry, flickering, physics violations | Smooth motion, natural lighting, professional but authentic |
| **Narrative Flow** | Clear beginning-middle-end? Pacing matches message? | Disjointed scenes, unclear progression | Logical arc, builds to CTA, appropriate pacing for platform |
| **Copy-Video Coherence** | Does the video reinforce the ad text and CTA? | Video shows unrelated scene, ignores copy message | Visual directly amplifies the text message and call to action |
| **UGC Authenticity** | Feels genuine vs corporate? Relatable to target audience? | Obviously AI-generated, uncanny valley, corporate feel | Natural, relatable, "could be a real person's content" |

## Implementation

### 1. `evaluate/video_scorer.py` (new file)

```python
@dataclass
class VideoScoreResult:
    hook_strength: float           # 1-10
    visual_quality: float          # 1-10
    narrative_flow: float          # 1-10
    copy_video_coherence: float    # 1-10
    ugc_authenticity: float        # 1-10
    avg_score: float               # mean of 5
    rationales: dict[str, str]     # per-dimension explanation

VIDEO_DIMENSIONS = (
    "hook_strength",
    "visual_quality",
    "narrative_flow",
    "copy_video_coherence",
    "ugc_authenticity",
)

def score_video(
    video_path: str,
    ad_copy: dict,
    session_config: dict | None = None,
) -> VideoScoreResult:
```

### 2. Gemini Prompt Design

Send to Gemini 2.0 Flash (multimodal — native video support):
- Video file (uploaded via `client.files.upload()`)
- Ad copy: headline, primary_text, cta_button
- Brand context: Varsity Tutors, SAT test prep
- Target audience (from session config if available)

```
Evaluate this ad video for a Varsity Tutors SAT test prep campaign.

Ad copy for context:
- Headline: {headline}
- Primary text: {primary_text}
- CTA: {cta_button}

Score each dimension 1-10 and provide a one-sentence rationale:

1. hook_strength — Do the first 2 seconds grab attention and stop the scroll?
2. visual_quality — Smooth motion, good lighting, no artifacts or glitches?
3. narrative_flow — Clear beginning-middle-end? Pacing appropriate for an 8s social ad?
4. copy_video_coherence — Does the video reinforce the ad text and CTA?
5. ugc_authenticity — Does it feel genuine and relatable, not corporate or uncanny?

Return JSON only: {"hook_strength": {"score": N, "rationale": "..."}, ...}
```

### 3. Gemini Video Upload Pattern

Already established in `evaluate/video_evaluator.py`:
```python
from google import genai

client = genai.Client(api_key=api_key)
video_file = client.files.upload(file=video_path)

# Poll until processing complete
while video_file.state == "PROCESSING":
    time.sleep(2)
    video_file = client.files.get(name=video_file.name)

response = client.models.generate_content(
    model="gemini-2.0-flash",
    contents=[video_file, prompt],
)
```

### 4. Ledger Integration

New event type: `VideoScored`
```json
{
  "event_type": "VideoScored",
  "ad_id": "ad_brief_001_c0_739382362",
  "outputs": {
    "video_path": "output/videos/session_xxx/ad_brief_001_anchor_9x16.mp4",
    "video_scores": {
      "hook_strength": 7.0,
      "visual_quality": 8.0,
      "narrative_flow": 6.5,
      "copy_video_coherence": 7.5,
      "ugc_authenticity": 6.0
    },
    "video_avg_score": 7.0,
    "rationales": { ... }
  }
}
```

### 5. Pipeline Integration

Wire into `pipeline_task.py` `_run_video_pipeline()` after variant generation:
```python
# After video passes binary attribute check
video_scores = score_video(variant.video_path, ad_copy, config)
log_event(ledger, {"event_type": "VideoScored", ...})
```

Keep existing binary attribute check + coherence check as gates. Rich scoring runs as a second pass on passing videos.

### 6. Backfill Script

`scripts/backfill_video_scores.py`:
- Reads all session ledgers for `VideoSelected` events with `winner_video_path`
- Checks video file exists on disk
- Uploads to Gemini, runs `score_video(path, copy)`
- Appends `VideoScored` event to session ledger
- Estimated: ~9 videos × ~8K tokens each ≈ 72K tokens ≈ $0.01, ~5 min runtime

### 7. Relationship to Existing Video Evaluation

| Component | Today | After PD-14 |
|-----------|-------|-------------|
| `evaluate/video_evaluator.py` `evaluate_video_attributes()` | 5 binary checks → pass/fail gate | **Unchanged** — still gates publish |
| `evaluate/video_evaluator.py` `check_video_coherence()` | 4 dims × 1-10 → coherence avg | **Unchanged** — still used for selection |
| `evaluate/video_scorer.py` `score_video()` | N/A | **New** — rich 5-dim scoring for analytics |

The existing evaluation decides **if** a video publishes. The new scorer measures **how good** it is for dashboard analytics and trend tracking.

## Token Cost Estimates

| What | Tokens per call | Count | Total |
|------|----------------|-------|-------|
| Video upload + scoring prompt | ~8,000 (8 frames + prompt) | 9 existing | 72K |
| Future per-session (2 variants × 3 ads) | ~8,000 each | 6 per session | 48K |

Cost is negligible — video scoring adds ~$0.01 per session.

## Dashboard Integration (deferred to PD-15)

- `export_dashboard.py` reads `VideoScored` events
- Dimension Deep-Dive shows video dimensions
- Ad Library cards show video dimension scores (not just composite)
- Quality Trends tracks video scores over time

## Acceptance Criteria
- `score_video()` returns 5 dimension scores + rationales via Gemini multimodal
- Scores logged to ledger as `VideoScored` events
- Backfill script scores all existing selected videos
- Existing binary attribute + coherence checks unchanged
- Unit tests with mock Gemini responses
- Video upload/polling follows established pattern from `video_evaluator.py`

## Dependencies
- None (independent, but pairs with PD-12 and PD-13)

## Estimate
~2 hours (scorer + pipeline wiring + backfill script + tests)
