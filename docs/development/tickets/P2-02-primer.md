# P2-02 Primer: Correlation Analysis

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** P2-01 (inversion tests), P1-20 (50+ ad run producing evaluation data) must be complete. See `docs/DEVLOG.md`.

---

## What Is This Ticket?

P2-02 implements **pairwise Pearson correlation analysis** across all 5 evaluation dimensions. Using the 50+ evaluated ads from P1-20, compute the 10-pair correlation matrix and verify no pair exceeds r = 0.7. If any pair does, investigate whether it's a genuine relationship or a halo effect, and document mitigation.

### Why It Matters

- **The System Knows What It Doesn't Know** (Pillar 4): Correlation analysis is the statistical complement to P2-01's causal inversion tests
- If two dimensions have r > 0.7, targeted regeneration can't distinguish between them — fixing one implicitly fixes the other, wasting tokens
- R2-Q3 explicitly requires both inversion tests AND correlation analysis as the evaluation framework's proof of independence
- PRD success criteria: "5 dimensions, proven independent" requires both causal and statistical evidence
- Feeds P5 dashboard with dimension independence visualization

---

## What Was Already Done

- P2-01: Inversion tests prove dimension independence causally (degrading one drops only that one)
- P1-20: 50+ evaluated ads with scores across all 5 dimensions in the ledger
- P1-04: CoT evaluator with forced decomposition before scoring
- P1-05: Campaign-goal-adaptive weighting (awareness vs conversion have different weight profiles)

---

## What This Ticket Must Accomplish

### Goal

Compute the full 5×5 pairwise Pearson correlation matrix from production evaluation data. Verify no pair exceeds r = 0.7. Generate visualization for dashboard consumption.

### Deliverables Checklist

#### A. Correlation Analyzer (`evaluate/correlation.py`)

- [ ] `compute_correlation_matrix(scores: list[dict[str, float]]) -> dict[tuple[str, str], float]`
  - Input: list of per-ad score dicts (each has 5 dimension scores)
  - Output: dict mapping dimension pairs to Pearson r values
  - Uses numpy or manual Pearson computation (no additional dependencies beyond numpy)
- [ ] `check_independence(matrix: dict, threshold: float = 0.7) -> IndependenceResult`
  - Returns pass/fail, list of pairs exceeding threshold, max correlation found
  - Flags any pair with |r| > 0.7
- [ ] `extract_scores_from_ledger(ledger_path: str) -> list[dict[str, float]]`
  - Reads AdEvaluated events from the ledger
  - Extracts per-dimension scores for correlation analysis
  - Filters to only use first-cycle evaluations (avoid regen bias)
- [ ] `format_correlation_matrix(matrix: dict) -> str`
  - Human-readable matrix display for logging and dashboard

#### B. Tests (`tests/test_evaluation/test_correlation.py`)

- [ ] `test_perfectly_independent_dimensions`: Synthetic data with known independence → all |r| < 0.3
- [ ] `test_perfectly_correlated_pair_detected`: Synthetic data with r ≈ 1.0 → flagged
- [ ] `test_threshold_boundary`: r = 0.69 passes, r = 0.71 fails
- [ ] `test_negative_correlation_detected`: r = -0.8 also exceeds threshold (use |r|)
- [ ] `test_matrix_has_all_10_pairs`: 5 dimensions → 10 unique pairs
- [ ] `test_extract_scores_from_ledger_reads_correctly`: Mock ledger with known scores
- [ ] `test_independence_result_structure`: Result has pass/fail, max_r, violating_pairs
- [ ] `test_single_ad_returns_empty_matrix`: Need ≥2 data points for correlation
- [ ] Minimum: 8+ tests

#### C. Documentation

- [ ] Add P2-02 entry in `docs/DEVLOG.md`
- [ ] If any pair exceeds 0.7, document in decision log with analysis of why

---

## Important Context

### Architectural Decisions

| Decision | Reference | Summary |
|----------|-----------|---------|
| Correlation analysis | R2-Q3 (Option C) | Statistical proof of independence; complements causal inversion tests |
| Halo effect mitigation | Risk Register | High impact risk; correlation > 0.7 indicates decorative dimensions |
| CoT decomposition | R3-Q6 | 5-step evaluation prevents halo through forced separation |

### The 5 Dimensions

```python
DIMENSIONS = ("clarity", "value_proposition", "cta", "brand_voice", "emotional_resonance")
# 10 unique pairs: (clarity, vp), (clarity, cta), ..., (bv, er)
```

### Expected Correlations

Some natural correlation is expected and acceptable:
- Clarity ↔ Value Proposition: mild positive (clear ads tend to have clearer VPs) — r ≈ 0.3–0.5 is normal
- CTA ↔ Emotional Resonance: low correlation expected (CTA is structural, ER is tonal)
- Brand Voice ↔ others: should be most independent (brand voice is style, not content)

Red flags:
- Any pair > 0.7: halo effect — evaluator treating them as one thing
- All pairs > 0.5: general quality bias — evaluator assigning "good ad" or "bad ad" holistically

### Files to Create

| File | Why |
|------|-----|
| `evaluate/correlation.py` | Correlation analysis module |
| `tests/test_evaluation/test_correlation.py` | Correlation tests |

### Files You Should READ for Context

| File | Why |
|------|-----|
| `evaluate/evaluator.py` | EvaluationResult structure with per-dimension scores |
| `evaluate/dimensions.py` | DIMENSIONS tuple, weight profiles |
| `iterate/ledger.py` | `read_events()`, `read_events_filtered()` for extracting scores |
| `tests/test_data/golden_ads.json` | Human scores can also be used for correlation |

---

## Definition of Done

- [ ] Correlation matrix computed from 50+ evaluated ads
- [ ] No dimension pair exceeds |r| = 0.7 (or documented with mitigation)
- [ ] 8+ tests passing
- [ ] Human-readable matrix output for dashboard
- [ ] Lint clean
- [ ] DEVLOG updated

---

## After This Ticket: What Comes Next

**P2-03 (Adversarial Boundary Tests)** probes the evaluator with edge cases designed to exploit dimension boundaries — wrong brand voice with perfect clarity, pure manipulation with no substance, etc. Together, P2-01 (causal), P2-02 (statistical), and P2-03 (adversarial) form the complete evaluation validation suite.
