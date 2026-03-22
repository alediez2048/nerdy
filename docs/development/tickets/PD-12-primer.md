# PD-12: Brief Adherence Scorer — "Did the ad do what I asked?"

## Goal
Score every ad (copy, image, video) against the session's creative brief to measure how well the pipeline followed instructions. This is orthogonal to quality scoring — a beautiful ad that ignores the brief should score high on quality but low on adherence.

## The Problem
The pipeline can produce high-quality ads that don't match what the user requested. There's no way to detect when the persona is wrong, the key message is missing, or the format doesn't match the creative brief. Users have to manually review every ad against their session config.

## 5 Dimensions (1-10 scale each)

| Dimension | What it measures | Example pass | Example fail |
|-----------|-----------------|-------------|-------------|
| **Audience Match** | Does the ad speak to the configured audience? | Brief says "parents" → ad says "your child's scores" | Brief says "parents" → ad says "boost your GPA" |
| **Goal Alignment** | Does the ad serve the campaign goal? | Goal is "conversion" → strong CTA with urgency | Goal is "conversion" → informational tone, no CTA |
| **Persona Fit** | Does the tone match the persona's emotional state? | Persona "Burned Returner" → empathetic, fresh-start energy | Persona "Burned Returner" → generic corporate pitch |
| **Message Delivery** | Is the key message present or clearly conveyed? | Key message "This time will be different" → paraphrased in headline | Key message absent from ad entirely |
| **Format Adherence** | Does it match the creative brief style? | Brief "ugc_testimonial" → first-person student story | Brief "ugc_testimonial" → polished corporate copy |

## Implementation

### 1. `evaluate/brief_adherence.py` (new file)

```python
@dataclass
class BriefAdherenceResult:
    audience_match: float        # 1-10
    goal_alignment: float        # 1-10
    persona_fit: float           # 1-10
    message_delivery: float      # 1-10
    format_adherence: float      # 1-10
    avg_score: float             # mean of 5
    rationales: dict[str, str]   # per-dimension explanation

def score_brief_adherence(
    ad_copy: dict,
    session_config: dict,
    image_path: str | None = None,
    video_path: str | None = None,
) -> BriefAdherenceResult:
```

### 2. Gemini Prompt Design

Send to Gemini 2.0 Flash:
- Session config: audience, campaign_goal, persona, key_message, creative_brief
- Ad copy: headline, primary_text, description, cta_button
- Image file (if exists) — multimodal
- Video file (if exists) — multimodal

Prompt asks for JSON with 5 scores + 5 rationales.

### 3. Ledger Integration

New event type: `BriefAdherenceScored`
```json
{
  "event_type": "BriefAdherenceScored",
  "ad_id": "ad_brief_001_c0_739382362",
  "outputs": {
    "audience_match": 8.0,
    "goal_alignment": 7.5,
    "persona_fit": 6.0,
    "message_delivery": 9.0,
    "format_adherence": 7.0,
    "avg_score": 7.5,
    "rationales": {
      "audience_match": "Uses 'your child' language throughout — clearly parent-facing",
      "persona_fit": "Tone is generic rather than empathetic fresh-start energy expected for Burned Returner"
    }
  }
}
```

### 4. Pipeline Integration

Wire into `pipeline_task.py` after ad generation + evaluation:
```python
# After ad is generated and evaluated
adherence = score_brief_adherence(ad_copy, config, image_path, video_path)
log_event(ledger, {"event_type": "BriefAdherenceScored", ...})
```

### 5. Backfill Script

`scripts/backfill_brief_adherence.py`:
- Reads all session ledgers
- For each `AdPublished`/`VideoSelected` event, loads session config from DB
- Runs `score_brief_adherence(copy, config, image_path, video_path)`
- Appends `BriefAdherenceScored` event to session ledger
- Estimated cost: ~150 Gemini calls ≈ $0.02, ~10 min runtime

## Dashboard Integration (deferred to PD-15)

- New "Brief Adherence" section in Dimension Deep-Dive
- Per-ad adherence badge in Ad Library cards
- Session-level adherence avg in Pipeline Summary

## Data Flow

```
Session Config (audience, goal, persona, key_message, creative_brief)
    +
Ad Output (copy, image, video)
    ↓
[Gemini 2.0 Flash multimodal evaluation]
    ↓
BriefAdherenceResult (5 dimensions × 1-10 + rationales)
    ↓
Ledger event: BriefAdherenceScored
    ↓
Dashboard panels (PD-15)
```

## Acceptance Criteria
- `score_brief_adherence()` returns 5 dimension scores + rationales for any ad
- Works with copy-only, copy+image, and copy+video ads
- Scores logged to ledger as `BriefAdherenceScored` events
- Backfill script scores all existing published ads
- Unit tests with mock Gemini responses

## Dependencies
- None (can be built independently)

## Estimate
~2.5 hours (scorer + pipeline wiring + backfill script + tests)
