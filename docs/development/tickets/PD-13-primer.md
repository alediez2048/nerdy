# PD-13: Image Quality Scorer — 5-Dimension Visual Evaluation

## Goal
Replace the binary pass/fail image attribute check with a rich 5-dimension scoring system (1-10 scale) using Gemini multimodal. Gives images the same scoring depth that copy already has.

## The Problem
Image evaluation today is binary: 5 attributes pass/fail (composition, brand safety, text overlay legibility, color harmony, subject focus) + a 4-dimension coherence score. This tells you "is the image acceptable?" but not "how good is the image?" There's no way to track visual quality trends, compare image quality across sessions, or identify which visual dimensions need improvement.

## 5 Dimensions (1-10 scale each)

| Dimension | What it measures | Low score (1-3) | High score (8-10) |
|-----------|-----------------|-----------------|-------------------|
| **Visual Clarity** | Is the subject immediately identifiable? Clean composition? | Cluttered, confusing, subject unclear | Instant recognition, clean focal point, uncluttered |
| **Brand Consistency** | Colors match Varsity Tutors palette? Professional tone? | Off-brand colors, inconsistent style | On-brand palette (#17e2ea, #0a2240), professional feel |
| **Emotional Impact** | Does the image evoke the intended emotion? | Flat, generic stock photo feel | Strong emotional resonance — aspiration, relief, confidence |
| **Copy-Image Coherence** | Does the visual reinforce the ad text's message? | Image contradicts or ignores the copy | Visual directly amplifies the text message |
| **Platform Fit** | Mobile-optimized? Readable at small size? Right composition for feed? | Text too small, bad crop, wasted space | Optimized for mobile scroll, strong at thumbnail size |

## Implementation

### 1. `evaluate/image_scorer.py` (new file)

```python
@dataclass
class ImageScoreResult:
    visual_clarity: float          # 1-10
    brand_consistency: float       # 1-10
    emotional_impact: float        # 1-10
    copy_image_coherence: float    # 1-10
    platform_fit: float            # 1-10
    avg_score: float               # mean of 5
    rationales: dict[str, str]     # per-dimension explanation

IMAGE_DIMENSIONS = (
    "visual_clarity",
    "brand_consistency",
    "emotional_impact",
    "copy_image_coherence",
    "platform_fit",
)

def score_image(
    image_path: str,
    ad_copy: dict,
    session_config: dict | None = None,
) -> ImageScoreResult:
```

### 2. Gemini Prompt Design

Send to Gemini 2.0 Flash (multimodal):
- Image file
- Ad copy: headline, primary_text, cta_button
- Brand context: Varsity Tutors, SAT test prep, palette #17e2ea/#0a2240
- Target audience (from session config if available)

```
Evaluate this ad image for a Varsity Tutors SAT test prep campaign.

Ad copy for context:
- Headline: {headline}
- Primary text: {primary_text}
- CTA: {cta_button}

Score each dimension 1-10 and provide a one-sentence rationale:

1. visual_clarity — Is the subject immediately clear? Clean composition?
2. brand_consistency — Does it feel like Varsity Tutors? On-brand colors and tone?
3. emotional_impact — Does the image evoke aspiration, confidence, or relief?
4. copy_image_coherence — Does the visual reinforce the text message?
5. platform_fit — Would this work well in a mobile feed at small size?

Return JSON only: {"visual_clarity": {"score": N, "rationale": "..."}, ...}
```

### 3. Ledger Integration

New event type: `ImageScored`
```json
{
  "event_type": "ImageScored",
  "ad_id": "ad_brief_001_c0_739382362",
  "outputs": {
    "image_path": "output/images/ad_brief_001_c0_739382362_9x16.png",
    "image_scores": {
      "visual_clarity": 7.5,
      "brand_consistency": 8.0,
      "emotional_impact": 6.5,
      "copy_image_coherence": 7.0,
      "platform_fit": 8.5
    },
    "image_avg_score": 7.5,
    "rationales": { ... }
  }
}
```

### 4. Pipeline Integration

Wire into `batch_processor.py` after image generation + existing attribute check:
```python
# After image passes binary attribute check
image_scores = score_image(image_path, ad_copy, config)
log_event(ledger, {"event_type": "ImageScored", ...})
```

Keep the existing binary attribute check as a gate (fail = don't score), add rich scoring as a second pass on passing images.

### 5. Backfill Script

`scripts/backfill_image_scores.py`:
- Reads all session ledgers for `AdPublished` events with `winning_image`
- Checks image file exists on disk
- Runs `score_image(path, copy)`
- Appends `ImageScored` event to session ledger
- Estimated: ~58 images × ~4K tokens each ≈ 232K tokens ≈ $0.03, ~5 min runtime

### 6. Competitor Image Scoring (optional, deferred)

Score competitor images from Meta CDN URLs in `data/competitive/raw/*.json`:
- Download from `"Ad Creative Image"` URL (may have expired)
- Run same scorer
- Store in `patterns.json` alongside hook/body/CTA classifications
- Enables benchmark: "Your avg Visual Clarity: 7.2, Chegg avg: 6.8"

## Dashboard Integration (deferred to PD-15)

- `export_dashboard.py` reads `ImageScored` events
- Dimension Deep-Dive shows image dimensions alongside copy dimensions
- Ad Library cards show image score badge
- Quality Trends tracks image scores over time

## Acceptance Criteria
- `score_image()` returns 5 dimension scores + rationales
- Scores logged to ledger as `ImageScored` events
- Backfill script scores all existing published images
- Existing binary attribute check unchanged (still gates publish)
- Unit tests with mock Gemini responses

## Dependencies
- None (independent, but pairs naturally with PD-12)

## Estimate
~2 hours (scorer + pipeline wiring + backfill script + tests)
