# Phase PF: Performance Feedback — Closing the Real-World Loop

## Context

The evaluator scores ads via LLM judgment (5 dimensions, CoT rationales, calibrated against reference ads). But it has no real-world performance data — no CTR, conversions, CPA, or engagement metrics from Meta. Phase PF builds the infrastructure and simulation to prove: if we had real Meta data, here's exactly how it integrates and how much the pipeline would improve.

## Tickets (7)

### PF-01: Meta Performance Data Schema + Ingestion
- `evaluate/performance_schema.py` — `MetaPerformanceRecord` dataclass (14 fields), validation, CSV/JSON loading
- `ingest_performance_data()` logs `PerformanceIngested` events to ledger
- **AC:** 17 tests, validation catches invalid records, round-trip through ledger

### PF-02: Simulated Performance Dataset
- `data/simulated_performance.py` — noise model: 30% copy quality, 40% targeting, 20% audience, 10% temporal
- Overall correlation between aggregate_score and CTR: r ~0.3–0.5 (realistic, not inflated)
- ~10% deliberate outliers (excellent copy + bad targeting = low CTR)
- **AC:** 10 tests, deterministic with seed, distributions within realistic bounds

### PF-03: Evaluator-Performance Correlation Analysis
- `evaluate/performance_correlation.py` — 5×4 matrix (dimensions × metrics)
- Reuses `_pearson_r` from `evaluate/correlation.py`
- Auto-generated findings: "CTA is the strongest predictor of conversion_rate (r=0.58)"
- **AC:** 11 tests, all 20 r-values computed, 4+ findings

### PF-04: Weight Recalibration from Performance Data
- `evaluate/weight_recalibrator.py` — normalize correlations → data-driven weights
- 70/30 blend: data-driven + prior (avoids overfitting to simulated data)
- Logs `WeightsRecalibrated` event to ledger
- **AC:** 11 tests, weights sum to 1.0, honest confidence note

### PF-05: Evaluator Accuracy Report
- `evaluate/accuracy_report.py` — precision@k, recall@k, confusion matrix
- False positives (high score, low CTR) and missed performers (low score, high CTR) enumerated
- **AC:** 13 tests, confusion matrix sums correctly, actionable findings

### PF-06: Closed-Loop Architecture Documentation
- `docs/deliverables/feedback_loop_architecture.md` — 4 sections: closed loop, integration points, production gaps, simulation results
- Decision log entry #22: "Why Simulated Performance Data"
- **AC:** All 4 sections, 5+ honest production gaps, ASCII architecture diagram

### PF-07: Performance Feedback Dashboard Panel
- `output/performance_dashboard.py` — Panel 9: Evaluator vs. Reality
- `PerformancePanelData`: correlation heatmap, weight comparison, accuracy metrics, key findings
- `loop_status` always = "simulated" (honest labeling)
- **AC:** 7 tests, HTML includes all required sections

## Dependency Graph

```
PF-01 (Schema)
  │
  v
PF-02 (Simulated Data)
  │
  ├──────────────┐
  v              v
PF-03 (Corr)   PF-05 (Accuracy)
  │              │
  v              │
PF-04 (Recal)   │
  │              │
  v              v
PF-06 (Docs) <──┘
  │
  v
PF-07 (Dashboard)
```

## Key Decisions Made

1. **Imperfect correlation (r ~0.3–0.5) is intentional** — real copy-to-CTR correlation is modest because targeting/audience/timing dominate
2. **70/30 blend for recalibrated weights** — pure data-driven from synthetic data = circular reasoning
3. **Ledger-native storage** — performance data gets new event types in existing JSONL (Pillar 5)
4. **Reuse `_pearson_r`** — no scipy dependency needed

## Status: ✅ COMPLETE (all 7 tickets, 69 tests)
