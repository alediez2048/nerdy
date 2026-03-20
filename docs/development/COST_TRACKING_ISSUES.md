# Cost Tracking Issues — Root Cause Analysis & Fix Plan

**Date:** March 20, 2026
**Status:** Partially fixed, requires dedicated plan
**Impact:** Cost metrics displayed incorrectly at all levels (session, campaign, global dashboard)

---

## Executive Summary

The cost tracking system has fundamental data integrity issues. Past sessions logged `tokens_consumed: 0` for all API calls because the code discarded the Gemini SDK's `usage_metadata` response. Video calls (Fal.ai) have no billing API, so per-call costs were estimated with made-up rates. Multiple attempts to fix the display led to cascading issues because the underlying data is unreliable.

**Actual total spend (from billing dashboards):**
- Gemini API: **$54.68** (Google AI Studio)
- Fal.ai: **$30.00** (Fal.ai invoices: $20 on March 19 + $10 on March 18)
- **Total: $84.68**

---

## Issue Timeline

### Issue 1: Global Dashboard showed $17 instead of ~$85

**Root cause:** `app/api/routes/dashboard.py` line 220 overrode the ledger-calculated cost with a DB-based rollup (`_session_rollup_total_cost()`). That function read `cost_so_far` from `session.results_summary`, which was computed in `pipeline_task.py` as:

```python
cost_so_far += batch_result.generated * 0.2  # flat $0.20 per ad — NOT real cost
```

85 ads × $0.20 = $17.00. Completely fake.

**Fix applied:** Removed the override. Let `build_dashboard_data_from_events()` compute cost from ledger token data.

**Problem:** This "fix" relied on ledger token data, which is also wrong (see Issue 2).

---

### Issue 2: Session ledgers have `tokens_consumed: 0` on all events

**Root cause:** Every Gemini API call in the codebase did:

```python
response = client.models.generate_content(...)
return response.text or ""  # ← usage_metadata discarded
```

The Gemini SDK returns `response.usage_metadata.total_token_count` on every call, but the code only read `response.text` and threw away the rest. When logging to the ledger:

```python
# batch_processor.py — hardcoded to 0
log_event(ledger_path, {"tokens_consumed": 0, ...})

# image_evaluator.py — hardcoded to 500
log_event(ledger_path, {"tokens_consumed": 500, ...})

# brief_expansion.py — character-based estimate
tokens_estimate = (len(prompt) + len(response)) // 4
```

**Impact:** 748 out of 1,037 session ledger events have `tokens_consumed: 0`. Any cost calculation based on `rate × tokens` produces $0 or near-$0 for sessions.

**Data:**
- Global ledger (`data/ledger.jsonl`): 8.4M tokens (from pre-session CLI runs that used a different code path)
- Session ledgers (`data/sessions/*/ledger.jsonl`): 413K tokens total (mostly zeros)

---

### Issue 3: Campaign stats showed $2 instead of ~$85

**Root cause:** Campaign stats function `_compute_campaign_stats()` read `cost_so_far` from `session.results_summary` in the DB — the same fake $0.20/ad number from Issue 1.

**First fix attempt:** Changed to `_ledger_cost()` reading from session ledgers. But session ledgers have `tokens_consumed: 0` (Issue 2), so it computed ~$2.

**Second fix attempt:** Changed to `_total_ledger_cost()` merging global + session ledgers. This produced $198.83 because it double-counted the global ledger AND charged per-call rates for video events.

---

### Issue 4: Video costs wildly inflated ($198 displayed)

**Root cause:** Multiple compounding errors:

1. **Made-up per-call rates:** `MODEL_COST_RATES` had `"veo-3.1-fast": 0.90` ($0.90/video). Actual cost from Fal.ai invoices: $30 / 109 calls = **$0.28/call**.

2. **Model name mismatch:** Ledger events store `model_used: "veo"` or `"fal-ai/veo3"`, but `MODEL_COST_RATES` only had `"veo-3.1-fast"`. Unmatched models fell back to the default rate (`0.01 / 1000`), making some video events cost $0 and others $0.90.

3. **Evaluation events treated as per-call:** `PER_CALL_EVENT_TYPES` included `VideoEvaluated` (107 events) and `VideoCoherenceChecked` (92 events). But these are **Gemini Flash text evaluations** (`model_used: "gemini-2.0-flash"`), not video API calls. Charging them at per-call video rates added ~$100 of phantom cost.

4. **Credits-based calculation overrode per-call rate:** `compute_event_cost()` checked for `outputs.credits` and calculated `credits × 0.001`. But credits were estimated by the orchestrator (`_CREDITS_PER_SECOND` constants), not from Fal.ai billing. Credits of 1200-2400 produced $1.20-$2.40/call instead of the real $0.28.

**Breakdown of $198.83:**
- Global ledger (real Gemini tokens): $84.30
- Session VideoGenerated (109 × $0.90 made-up rate): $98.10
- Session text events with real tokens: $3.33
- Session image evals (hardcoded 500 tokens): $0.81
- Misc: $12.29

---

### Issue 5: $84.68 baseline applied to every individual session

**Root cause:** `HISTORICAL_SPEND_USD = 84.68` was used in `_build_pipeline_summary()` which is called for BOTH global dashboard AND per-session dashboards. Every session showed $84.68 regardless of what it actually spent.

**Fix applied:** Moved the baseline application to the global dashboard route only. Per-session dashboards compute cost from their own ledger events.

**Remaining problem:** Per-session cost for past sessions is still wrong because their ledger events have `tokens_consumed: 0`. Old image sessions show ~$0, old video sessions show ~$0.28 × number of videos (which is at least directionally correct for Fal.ai but missing Gemini costs).

---

## Current State (After All Fixes)

### What works:
- **Global dashboard:** Shows $84.68 (hardcoded baseline from real billing)
- **Campaign stats:** Shows $84.68 (hardcoded baseline)
- **Future sessions (Gemini):** Will capture real `total_token_count` from `response.usage_metadata` via `generate/gemini_client.py`
- **Future sessions (Fal.ai video):** Will charge $0.28/call per `VideoGenerated` event (from invoice-derived rate)
- **`compute_event_cost()`:** Correctly routes text events to per-token pricing and generation events to per-call pricing

### What doesn't work:
- **Past session costs:** Individual sessions created before the token capture fix show incorrect costs ($0 or near-$0 for Gemini, $0.28 × video count for Fal.ai)
- **Per-session Gemini cost attribution:** Even with real tokens, we're using a flat $0.01/1K rate. Gemini pricing actually varies by model, input vs output tokens, and whether images are involved
- **Per-session Fal.ai cost attribution:** $0.28/call is an average derived from total invoice ÷ total calls. Actual per-call cost may vary by model, duration, and resolution
- **No real-time billing validation:** We can't query Gemini or Fal.ai billing APIs to verify our calculations match actual charges

---

## Architecture of the Problem

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Gemini API     │     │  Fal.ai API      │     │  Image Gen      │
│  (text + image) │     │  (video)         │     │  (Gemini)       │
└────────┬────────┘     └────────┬─────────┘     └────────┬────────┘
         │                       │                         │
    usage_metadata          no cost data              usage_metadata
    (was discarded)         returned                  (was discarded)
         │                       │                         │
         ▼                       ▼                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  Ledger Events  (tokens_consumed: 0 for all past sessions)     │
│  - AdGenerated, BriefExpanded, AdEvaluated: tokens=0           │
│  - ImageEvaluated: tokens=500 (hardcoded)                      │
│  - VideoGenerated: tokens=0, credits in outputs (estimated)    │
│  - AdPublished/AdDiscarded: tokens=0, model="none" (correct)   │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                    compute_event_cost()
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
        Per-token     Per-call     Per-call
        (text)        (image)     (video)
        rate×tokens   rate×1      rate×1
        = $0 ✗        = $0.13     = $0.28
                      (no events  (correct
                       in session  for Fal.ai)
                       ledgers)
```

---

## Files Involved

| File | Role | Issue |
|------|------|-------|
| `generate/gemini_client.py` | NEW: Shared Gemini wrapper capturing usage_metadata | Fix for future sessions |
| `generate/ad_generator.py` | Ad copy generation | Was: `return response.text`. Now: returns (text, tokens) |
| `generate/brief_expansion.py` | Brief expansion | Was: `return response.text`. Now: returns (text, tokens) |
| `evaluate/evaluator.py` | CoT evaluation | Was: `return response.text`. Now: returns (parsed, tokens) |
| `evaluate/image_evaluator.py` | Image attribute eval | Was: hardcoded 500 tokens. Now: real tokens |
| `evaluate/coherence_checker.py` | Copy-image coherence | Was: no tokens. Now: real tokens |
| `evaluate/cost_reporter.py` | Cost rates + compute_event_cost() | Fixed rates, added HISTORICAL_SPEND_USD |
| `iterate/batch_processor.py` | Batch processing, ledger writes | Was: hardcoded 0. Now: propagates real tokens |
| `app/workers/tasks/pipeline_task.py` | Celery pipeline task | Was: $0.20/ad estimate. Now: compute_event_cost() |
| `app/api/routes/dashboard.py` | Global dashboard API | Applies $84.68 baseline for global view only |
| `app/api/routes/campaigns.py` | Campaign stats API | Applies $84.68 baseline for campaign view |
| `output/export_dashboard.py` | Dashboard data builder | Per-session: real data only. Global: baseline |

---

## Recommended Plan to Fully Fix

### Phase 1: Validate New Token Capture (1 hour)
- [ ] Run a new 1-ad image session and verify `tokens_consumed` > 0 in the session ledger
- [ ] Run a new 1-video session and verify `VideoGenerated` event has correct model_used
- [ ] Compare computed cost with actual Gemini/Fal.ai billing delta
- [ ] Fix any discrepancies in rates

### Phase 2: Backfill Historical Session Costs (2 hours)
- [ ] For each of the 12 existing sessions, determine session type (image vs video)
- [ ] Image sessions: estimate cost from ad count × average Gemini tokens per ad (from global ledger data where we have real tokens)
- [ ] Video sessions: count VideoGenerated events × $0.28/call for Fal.ai, plus Gemini eval costs
- [ ] Write a migration script to update `session.results_summary.cost_so_far` in the DB with corrected values
- [ ] Per-session dashboard reads from `results_summary` as fallback when ledger has no real tokens

### Phase 3: Per-Session Cost Display (1 hour)
- [ ] Session Overview tab: show cost from `results_summary.cost_so_far` (backfilled) OR computed from ledger (new sessions)
- [ ] Session card in campaign view: same logic
- [ ] Add "Estimated" label for backfilled values vs "Actual" for new sessions

### Phase 4: Ongoing Accuracy (30 min)
- [ ] Add a pre-commit check that no new `tokens_consumed: 0` hardcodes are added
- [ ] Add a health check endpoint that compares computed total with HISTORICAL_SPEND_USD
- [ ] Update HISTORICAL_SPEND_USD when new billing data is available
- [ ] Consider capturing Gemini input_tokens vs output_tokens separately (different pricing tiers)

### Phase 5: Remove Hardcoded Baseline (when ready)
- [ ] Once all sessions have real cost data (backfilled or captured), remove HISTORICAL_SPEND_USD
- [ ] Campaign and global stats compute from actual session data
- [ ] Delete the baseline fallback code

---

## Key Lessons

1. **Never discard API response metadata.** The Gemini SDK returns `usage_metadata` on every call — this should have been captured from day one.
2. **Never hardcode cost estimates.** `$0.20/ad`, `500 tokens`, `credits × 0.001` — all of these were wrong and created cascading display errors.
3. **Cost calculation must match billing source of truth.** The only reliable numbers are from Google AI Studio and Fal.ai invoices. Everything else is a guess.
4. **Shared utility functions prevent drift.** Having 10 separate `generate_content()` call sites meant 10 places that could (and did) handle tokens differently.
5. **Test with real billing data.** If we'd compared our displayed cost with actual billing early, we'd have caught these issues before they compounded.
