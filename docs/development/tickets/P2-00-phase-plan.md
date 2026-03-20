# Phase P2: Testing & Validation

## Context

P2 validates the claims made by the pipeline architecture. Without these tests, assertions like "dimensions are independent" and "the evaluator can tell good from bad" are unproven. The rubric specifically scores quality measurement (25%) — P2 provides the evidence.

## Tickets (7)

### P2-01: Inversion Tests
- Degrade one dimension at a time; verify only that dimension's score drops (≥1.5) while others stay stable (±0.5)
- `tests/test_evaluation/test_inversion.py` — 15+ degraded ad variants, 10+ tests
- **AC:** Degraded dimension drops ≥1.5, others stable

### P2-02: Correlation Analysis
- `evaluate/correlation.py` — 5×5 pairwise Pearson correlation matrix
- `check_independence()` flags any pair with |r| > 0.7 (halo effect)
- **AC:** 8+ tests, no pair exceeds 0.7, matrix generated

### P2-03: Adversarial Boundary Tests
- Edge cases: perfect Clarity + zero Brand Voice, wrong brand ad, pure manipulation
- `tests/test_evaluation/test_adversarial.py` — 8+ adversarial ads, all fail threshold
- **AC:** 8+ tests pass

### P2-04: SPC Drift Detection
- `evaluate/spc_monitor.py` — ±2σ control charts on batch-level score distributions
- Canary injection: re-evaluate golden ads to diagnose evaluator drift vs. real quality change
- **AC:** 10+ tests, canary fires on simulated drift

### P2-05: Confidence-Gated Autonomy
- Route by evaluator confidence: >7 autonomous, 5–7 flagged, <5 human required
- `evaluate/confidence_router.py` — confidence routing with brand safety hard stop
- **AC:** 8+ tests, correct routing per confidence level

### P2-06: Tiered Compliance Filter
- `generate/compliance.py` — 3 layers: regex hard rules → LLM policy check → LLM brand safety
- Catches: competitor names, guaranteed outcomes, PII, misleading claims
- **AC:** 10+ tests, known-bad ads caught, zero false negatives

### P2-07: End-to-End Integration Test
- Full pipeline with checkpoint-resume: start, kill, resume
- `tests/test_pipeline/test_e2e_integration.py` — 10+ integration tests
- **AC:** Resumed run = identical output, no duplicates

## Dependency Graph

```
P2-01 (Inversion) ──┐
P2-02 (Correlation) ─┤── Can run in parallel
P2-03 (Adversarial) ─┘
         │
P2-04 (SPC Drift) ── depends on batch data from P1-20
P2-05 (Confidence) ── depends on P1-04 confidence flags
P2-06 (Compliance) ── standalone
P2-07 (E2E Integration) ── depends on full pipeline (P1-20)
```

## Recommended Cherry-Pick (if time-constrained)

| Ticket | Priority | Why |
|--------|----------|-----|
| **P2-01** | Must | Proves dimensions are independent — rubric cares |
| **P2-02** | Must | Proves no halo effect — validates 5-dimension framework |
| **P2-07** | Must | Proves pipeline works end-to-end with resume |
| P2-03 | Nice | Adversarial edge cases strengthen claims |
| P2-04 | Skip | Complex, can mention as "designed but deferred" |
| P2-05 | Skip | Confidence flags exist; routing layer is bonus |
| P2-06 | Skip | Stub exists with Layer 1 regex |

## Status: 🔄 PARTIAL (P2-01, P2-02, P2-04 implemented; P2-03 adversarial tests exist; P2-05, P2-06, P2-07 pending)
