# PD-11: Competitor Upload & Classification

## Goal
Allow users to upload new competitor ad data (Meta Ad Library JSON export) and have it automatically classified and added to the competitive pattern database.

## Deliverables
1. **`app/api/routes/competitive.py`** — Add upload endpoint
   - `POST /api/competitive/upload` — accepts JSON file + competitor name
   - Runs classification pipeline, appends to `patterns.json` and `data/competitive/raw/`
2. **`app/frontend/src/views/CompetitiveIntelPage.tsx`** — Upload section
   - Competitor name input + file dropzone
   - Preview classified results before confirming
   - Refresh page data after successful upload

## Classification Pipeline (reuse from `scripts/process_competitive_data.py`)
1. Parse uploaded JSON (Meta Ad Library export format)
2. Deduplicate by normalized text against existing patterns
3. Classify each ad:
   - `hook_type` (11 types: question, statistic, fear_based, etc.)
   - `body_pattern` (7 structures)
   - `cta_style` (6 styles)
   - `emotional_register` (9 registers)
   - `tone` (7 tones)
   - `primary_audience` (students/parents/both)
   - `tags` (topic tags)
4. Append classified ads to `data/competitive/raw/{competitor}.json`
5. Select diverse patterns → append to `patterns.json`
6. Update `competitor_summaries` if new competitor

## Backend Design
- Extract classification logic from `scripts/process_competitive_data.py` into importable module
- `POST /api/competitive/upload`:
  - Body: `multipart/form-data` with `file` (JSON) + `competitor_name` (string)
  - Returns: `{ "ads_parsed": N, "ads_new": N, "patterns_added": N, "preview": [...] }`
- `POST /api/competitive/upload/confirm`:
  - Writes previewed results to disk

## Acceptance Criteria
- User can upload a Meta Ad Library JSON export for a new or existing competitor
- Classified results are previewed before confirming
- After confirmation, `patterns.json` and raw data files are updated
- Analytics on the competitive page update to reflect new data
- Duplicate ads are detected and skipped

## Dependencies
- PD-10 (raw ads browser must exist for the upload to display results)

## Estimate
~2 hours
