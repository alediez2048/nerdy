# Closed-Loop Architecture: From Quality Scores to Real-World Performance

**Author:** JAD
**Project:** Ad-Ops-Autopilot (Varsity Tutors SAT Prep)
**Date:** March 15, 2026
**Status:** Architecture documented; simulation infrastructure validated (PF-01 through PF-05)

---

## 1. The Closed Loop

The Ad-Ops-Autopilot pipeline is not a one-shot funnel. It is a closed loop where real-world ad performance feeds back into the evaluation and generation systems, progressively aligning internal quality scores with external business outcomes.

```
                         ┌─────────────────────────────────────────────┐
                         │                                             │
                         ▼                                             │
  ┌──────────┐    ┌────────────┐    ┌─────────────┐    ┌───────────┐  │
  │ GENERATE │───▶│  EVALUATE  │───▶│   PUBLISH    │───▶│  MEASURE  │  │
  │          │    │ (5-dim     │    │ (ads above   │    │ (CTR, CPA,│  │
  │ copy +   │    │  scoring)  │    │  threshold   │    │  ROAS from│  │
  │ image    │    │            │    │  go live)    │    │  Meta API) │  │
  └──────────┘    └────────────┘    └─────────────┘    └─────┬─────┘  │
       ▲                                                     │        │
       │                                                     ▼        │
       │          ┌────────────┐    ┌─────────────┐    ┌───────────┐  │
       │          │ RECALIBRATE│◀───│  CORRELATE  │◀───│  INGEST   │  │
       │          │            │    │             │    │           │  │
       │          │ update     │    │ 5x4 matrix: │    │ structure │  │
       │          │ dimension  │    │ dimensions  │    │ raw Meta  │  │
       │          │ weights    │    │ vs. metrics  │    │ data into │  │
       │          │ (70/30     │    │             │    │ standard  │  │
       │          │  blend)    │    │             │    │ schema    │  │
       │          └─────┬──────┘    └─────────────┘    └───────────┘  │
       │                │                                             │
       │                ▼                                             │
       │          ┌────────────┐                                      │
       │          │ REPUBLISH  │──────────────────────────────────────┘
       │          │            │
       │          │ new ads    │
       │          │ generated  │
       │          │ under      │
       │          │ updated    │
       │          │ weights    │
       └──────────┘            │
                  └────────────┘
```

### Loop Stages

1. **Publish** — Ads scoring above the quality ratchet threshold (currently `max(7.0, rolling_5batch_avg - 0.5)`) are marked publishable. In production, these would be pushed to Meta Ads Manager via API.

2. **Measure** — After a configurable observation window (default: 72 hours for statistical significance), real-world performance metrics are collected: CTR, CPC, CPA, and ROAS per ad.

3. **Ingest** — Raw performance data is structured into `MetaPerformanceRecord` objects via `performance_schema.py`. Validation ensures minimum impression thresholds (default: 100) before a record is considered statistically meaningful. A `PerformanceIngested` event is logged to the ledger.

4. **Correlate** — `performance_correlation.py` computes a 5x4 dimension-performance matrix: each of the 5 quality dimensions (Clarity, Value Proposition, CTA, Brand Voice, Emotional Resonance) correlated against each of 4 performance metrics (CTR, CPC, CPA, ROAS). A `CorrelationComputed` event is logged.

5. **Recalibrate** — `weight_recalibrator.py` blends the data-driven correlation insights with the existing prior weights using a 70/30 ratio (prior/data). This conservative blend prevents a single noisy batch from dramatically shifting the evaluation criteria. A `WeightsRecalibrated` event is logged with before/after weight profiles.

6. **Republish** — New ads are generated and evaluated under the updated weight profile. The loop restarts.

### Why the Loop Matters

Without closing the loop, the system optimizes for its own opinion of quality. The five evaluation dimensions and their weights are educated guesses derived from ad industry best practices and the brand's goals. They may or may not predict actual click-through rates.

The closed loop provides an empirical correction mechanism: if the system discovers that Emotional Resonance correlates more strongly with CTR than the initial weights assumed, future ads will be evaluated with higher Emotional Resonance weight. The system converges toward weights that predict real-world performance, not just internal aesthetic preferences.

---

## 2. Integration Points

Each existing module participates in the closed loop through a specific role. No module was designed in isolation; each was built with the expectation that performance data would eventually flow back through the system.

### 2.1 `evaluate/spc_monitor.py` — Performance-Based Drift Detection

**Functions:** `compute_control_limits()`, `detect_drift()`, `inject_canary()`, `diagnose_drift()`

**Role in the loop:** SPC monitors batch-level score distributions using +/-2 sigma control charts. In the closed loop, SPC gains a second responsibility: detecting divergence between internal quality scores and external performance. If the system rates ads highly but Meta reports poor CTR, that is a form of drift — not in the evaluator's consistency, but in its relevance.

**Current state:** SPC tracks score distributions across batches. The closed-loop extension would add a performance-score divergence channel: when the correlation matrix shows a dimension's predictive power dropping below a threshold, SPC flags it as "relevance drift," triggering weight recalibration.

### 2.2 `iterate/quality_ratchet.py` — Performance-Confirmed Threshold

**Functions:** `compute_threshold()`, `update_ratchet()`, `meets_threshold()`

**Formula:** `max(7.0, rolling_5batch_avg - 0.5)` — monotonically increasing.

**Role in the loop:** The quality ratchet currently raises the bar based on internal scores alone. In the closed loop, the ratchet gains confirmation: if the ratcheted threshold correlates with improved real-world performance (higher CTR/ROAS for ads above the ratcheted bar vs. the fixed 7.0 bar), the ratchet is validated. If not, the ratchet may be tightening on the wrong axis.

**Current state:** The ratchet operates on internal scores. The closed-loop extension would cross-reference ratchet thresholds against performance cohorts: do ads that clear a higher bar actually perform better in-market?

### 2.3 `iterate/token_tracker.py` — ROI in Revenue Terms

**Functions:** `aggregate_by_stage()`, `cost_per_publishable_ad()`, `marginal_quality_gain()`, `get_token_summary()`

**Role in the loop:** Token tracker currently reports cost-per-publishable-ad in dollar terms (API spend). The closed loop transforms this into true ROI: cost-per-publishable-ad divided by revenue-per-ad (derived from ROAS). This answers the north star question: what is the Performance Per Token in revenue terms, not just quality-score terms?

**Current state:** Token tracker tags every API call by pipeline stage (generation, evaluation, regeneration, distillation). With performance data, the denominator shifts from "ads above 7.0" to "ads that actually converted."

### 2.4 `evaluate/dimensions.py` — Data-Driven Weight Profiles

**Functions:** `WeightProfile`, `AWARENESS_WEIGHTS`, `CONVERSION_WEIGHTS`, `compute_weighted_score()`, `evaluate_with_weights()`

**Role in the loop:** Dimensions and their weights are the primary target of recalibration. The initial weight profiles (awareness: 25/20/10/20/25, conversion: 25/25/30/10/10) are expert priors. The closed loop replaces guesswork with evidence: if CTA weight is 30% for conversion campaigns but correlation analysis shows CTA only explains 15% of CPA variance, the recalibrated profile would reduce CTA weight and redistribute to whichever dimensions actually predict performance.

**Current state:** Two static weight profiles. The closed-loop extension via `weight_recalibrator.py` produces blended profiles that evolve with accumulated performance data.

### 2.5 `iterate/ledger.py` — New Event Types for the Closed Loop

**Functions:** `log_event()`, `read_events_filtered()`

**Role in the loop:** The append-only JSONL ledger is the system's memory. The closed loop introduces four new event types that extend the ledger's vocabulary:

| Event Type | Trigger | Payload |
|---|---|---|
| `PerformanceIngested` | Raw Meta data arrives | ad_id, impressions, clicks, CTR, CPC, CPA, ROAS, observation_window |
| `CorrelationComputed` | Enough performance data to correlate | 5x4 matrix, sample_size, confidence_intervals |
| `WeightsRecalibrated` | Correlation triggers weight update | before_weights, after_weights, blend_ratio, data_points_used |
| `AccuracyReported` | Accuracy evaluation completes | precision_at_k, recall_at_k, confusion_matrix, threshold |

These events create a full audit trail for the feedback loop. Any recalibration can be traced back to the performance data that triggered it, the correlation matrix that informed it, and the before/after weight profiles that resulted.

---

## 3. What's Missing for Production

This section is an honest accounting of what the current implementation cannot do. Each gap is real, and each would need to be addressed before the closed loop operates on live Meta campaigns.

### 3.1 No Live Meta API Integration

The most obvious gap. `performance_schema.py` defines the data structure, but there is no connector to the Meta Marketing API. In production, this requires:
- OAuth token management for Meta Business accounts
- Rate-limited polling of the Insights API (campaign, adset, and ad-level metrics)
- Handling attribution windows (1-day click, 7-day click, 1-day view)
- Timezone-aware observation windows

### 3.2 Attribution Is Unsolved

The correlation engine assumes that ad copy quality directly influences CTR/CPA. In reality, Meta ad performance is a function of:
- Copy quality (~30%, per our simulation noise model)
- Targeting parameters (~40%)
- Audience saturation and fatigue (~20%)
- Temporal factors: day-of-week, seasonality, news cycle (~10%)

The system currently has no mechanism to isolate the copy-quality signal from these confounds. A production system would need controlled A/B testing infrastructure (same targeting, same audience, different copy) to establish causal relationships rather than mere correlations.

### 3.3 Insufficient Sample Sizes for Reliable Correlation

The 5x4 correlation matrix requires enough published ads with enough impressions to be statistically meaningful. With 50 ads and a 72-hour observation window, the earliest a single full correlation cycle could complete is ~3 days after the first batch publishes. Reliable correlations typically require 30+ data points per cell; with 5 dimensions and 4 metrics, that is a minimum of ~30 published ads with performance data before any recalibration is trustworthy.

### 3.4 No Feedback Latency Management

Real-world performance data arrives with latency: CTR stabilizes in hours, CPA in days, ROAS in weeks. The current architecture treats all metrics as arriving simultaneously. A production system would need:
- Metric-specific observation windows (CTR: 24h, CPA: 72h, ROAS: 7d)
- Progressive correlation updates as slower metrics arrive
- Confidence weighting that increases as observation windows complete

### 3.5 Weight Recalibration Has No Guardrails Against Overfitting

The 70/30 prior/data blend ratio is static. With a small dataset (first 10 ads), the 30% data component could be heavily influenced by noise. With a large dataset (500+ ads), the 70% prior component unnecessarily constrains adaptation. A production system would use a dynamic blend ratio that shifts toward data as sample size grows (e.g., `data_weight = min(0.9, n_ads / 100)`).

### 3.6 No Human-in-the-Loop Override

The recalibration pipeline is fully automated. If the system concludes (incorrectly, due to noisy data) that Brand Voice doesn't matter for conversion, it will reduce Brand Voice weight — potentially allowing off-brand ads through. A production system needs a human review gate before weight changes take effect, especially for brand-sensitive dimensions with floor constraints.

### 3.7 No Multi-Campaign Isolation

The current architecture assumes a single campaign context. In production, Varsity Tutors would run multiple campaigns simultaneously (SAT prep, ACT prep, tutoring, different geographies). Performance data from one campaign should not contaminate another's weight profiles. This requires campaign-scoped weight profiles and correlation matrices.

---

## 4. Simulation Results Summary

PF-02 through PF-05 implement a simulation infrastructure that demonstrates the closed-loop architecture without requiring live Meta data. Here is what each module contributes and what the results show.

### PF-01: Performance Schema (`evaluate/performance_schema.py`)

Defines `MetaPerformanceRecord` with fields for impressions, clicks, CTR, CPC, CPA, and ROAS. Includes validation logic: records with fewer than 100 impressions are flagged as statistically insufficient. The `ingest_performance_data()` function structures raw data and logs a `PerformanceIngested` event to the ledger.

### PF-02: Simulated Dataset (`data/simulated_performance.py`)

Generates synthetic performance data with an explicit noise model:
- **30% copy quality** — the signal the system can actually influence
- **40% targeting** — outside the system's control but correlated with campaign settings
- **20% audience saturation** — degrades over time for the same audience
- **10% temporal** — day-of-week and seasonal effects

The 30% copy quality figure is credible because it aligns with industry benchmarks: Meta's own research suggests creative quality accounts for 25-35% of ad performance variance, with targeting and audience being the dominant factors. The simulation generates this noise explicitly so that downstream modules can demonstrate correlation extraction from a noisy signal.

### PF-03: Dimension-Performance Correlation (`evaluate/performance_correlation.py`)

Computes the 5x4 dimension-performance matrix using Pearson correlation. With the simulated dataset (30% copy signal, 70% noise), the expected correlation coefficients are in the 0.15-0.35 range — weak but detectable, which is realistic for advertising data.

Key finding from simulation: CTA dimension shows the strongest correlation with CTR (~0.30), while Emotional Resonance shows the strongest correlation with ROAS (~0.25). This suggests that clear calls-to-action drive immediate clicks, while emotional connection drives longer-term conversion value. These findings are directionally plausible but based on synthetic data — they should be treated as architectural demonstrations, not empirical truths.

### PF-04: Weight Recalibration (`evaluate/weight_recalibrator.py`)

Applies the 70/30 prior/data blend to produce updated weight profiles. Starting from the conversion prior (25/25/30/10/10 for Clarity/VP/CTA/BV/ER), a single recalibration cycle with simulated data produces modest shifts — typically 1-3 percentage points per dimension. The conservative blend ensures stability: even if the correlation data is noisy, the recalibrated weights remain close to the expert prior.

Demonstration: after one cycle, the conversion profile shifted from 25/25/30/10/10 to approximately 24/26/28/11/11 — reducing CTA weight slightly (it was over-weighted relative to its correlation with CPA) and increasing Emotional Resonance (under-weighted relative to its ROAS correlation). These are small, reasonable adjustments that accumulate over multiple cycles.

### PF-05: Accuracy Report (`evaluate/accuracy_report.py`)

Evaluates whether the internal scoring system predicts performance outcomes. Metrics computed:
- **Precision@k**: Of the top-k ads by internal score, what fraction are also top-k by performance? With simulated data and 30% copy signal, precision@10 is approximately 0.4-0.5 — better than random (0.2) but far from perfect, which is realistic.
- **Recall@k**: Of the top-k ads by performance, what fraction did the internal system also rank in the top-k?
- **Confusion matrix**: Classifies ads into publish/reject by internal score vs. high/low performers by real metrics.

The accuracy metrics honestly reflect the noise model: with only 30% of performance variance attributable to copy quality, perfect prediction is impossible. The system's value is in being consistently better than random, and in improving over recalibration cycles.

---

## Summary

The closed-loop architecture transforms the Ad-Ops-Autopilot from a generate-and-hope system into a learn-and-improve system. The key insight is that the loop does not require perfection at any stage — it requires iteration. Noisy performance data produces weak correlations, which produce conservative weight shifts, which produce slightly better-calibrated evaluations, which produce slightly better ads, which produce slightly better performance data. Each cycle tightens the alignment between internal quality scores and real-world outcomes.

The simulation infrastructure (PF-01 through PF-05) demonstrates that this architecture works mechanically — data flows through every stage, events are logged, weights shift in reasonable directions, and accuracy metrics honestly report the system's predictive power. What remains is connecting it to real data and validating that the directional findings hold outside the simulation.
