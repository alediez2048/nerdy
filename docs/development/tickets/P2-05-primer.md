# P2-05 Primer: Confidence-Gated Autonomy

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** P1-04 (CoT evaluator with confidence flags), P1-06 (tiered model routing) must be complete. See `docs/DEVLOG.md`.

---

## What Is This Ticket?

P2-05 implements **confidence-gated autonomy** — routing ads based on the evaluator's self-rated confidence. The evaluator already produces confidence flags per dimension (P1-04). This ticket formalizes the routing: confidence >7 → autonomous processing; 5–7 → proceed but flag for optional review; <5 → human required. A brand safety hard stop fires when any dimension scores <4.0.

### Why It Matters

- **The System Knows What It Doesn't Know** (Pillar 4): Confidence gating concentrates human attention on the gray zone where the evaluator is uncertain
- R2-Q5 selected confidence-gated autonomy as the best human escalation approach
- Without confidence routing, all ads get equal treatment — wasting human attention on clear passes and missing uncertain cases
- Brand safety trigger (<4.0 on any dimension) prevents catastrophic failures from reaching production
- Complements P1-06's score-based routing with uncertainty-based routing

---

## What Was Already Done

- P1-04: CoT evaluator produces `confidence_flags: dict[str, float]` — dimensions with confidence < 7
- P1-06: Tiered model routing based on aggregate score (discard/escalate/publish)
- P1-05: Floor constraints (Clarity ≥ 6.0, Brand Voice ≥ 5.0) — hard stops
- P1-08: Brief mutation + escalation with diagnostic reports

---

## What This Ticket Must Accomplish

### Goal

Build confidence-based routing that uses the evaluator's per-dimension confidence to determine autonomy level. Add brand safety hard stop for extreme failures.

### Deliverables Checklist

#### A. Confidence Router (`evaluate/confidence_router.py`)

- [ ] `ConfidenceLevel` enum or constants: `AUTONOMOUS = "autonomous"`, `FLAGGED = "flagged"`, `HUMAN_REQUIRED = "human_required"`, `BRAND_SAFETY_STOP = "brand_safety_stop"`
- [ ] `ConfidenceRoutingResult` dataclass: `ad_id`, `confidence_level`, `min_confidence`, `low_confidence_dimensions`, `brand_safety_triggered`, `reason`
- [ ] `route_by_confidence(evaluation_result: EvaluationResult) -> ConfidenceRoutingResult`
  - Compute min confidence across all dimensions from `evaluation_result.confidence_flags` and `evaluation_result.scores`
  - Brand safety check: any dimension score < 4.0 → `BRAND_SAFETY_STOP`
  - Min confidence > 7.0 → `AUTONOMOUS`
  - Min confidence 5.0–7.0 → `FLAGGED`
  - Min confidence < 5.0 → `HUMAN_REQUIRED`
- [ ] `get_confidence_stats(ledger_path: str) -> ConfidenceStats`
  - Aggregate: % autonomous, % flagged, % human required, % brand safety stops
  - Dashboard-ready

#### B. Integration with Existing Routing

- [ ] Confidence routing runs AFTER score-based routing (P1-06)
- [ ] A "publish" decision from score routing can be downgraded to "flagged" if confidence is low
- [ ] A "discard" decision is never upgraded — low-score ads stay discarded regardless of confidence
- [ ] Log `ConfidenceRouted` event to ledger with full confidence breakdown

#### C. Tests (`tests/test_pipeline/test_confidence_router.py`)

- [ ] `test_high_confidence_autonomous`: All dimensions confidence >7 → autonomous
- [ ] `test_medium_confidence_flagged`: Min confidence 5.5 → flagged
- [ ] `test_low_confidence_human_required`: Min confidence 3.0 → human required
- [ ] `test_brand_safety_stop_on_low_score`: Any dimension score <4.0 → brand safety stop
- [ ] `test_brand_safety_overrides_high_confidence`: Even if confidence is 10.0, score <4.0 triggers stop
- [ ] `test_confidence_from_evaluation_result`: Correctly extracts confidence from real EvaluationResult structure
- [ ] `test_publish_downgraded_to_flagged`: Score-based publish + low confidence → flagged
- [ ] `test_discard_not_upgraded`: Score-based discard stays discard regardless of confidence
- [ ] `test_confidence_stats_aggregation`: Stats correctly count each routing level
- [ ] Minimum: 8+ tests

#### D. Documentation

- [ ] Add P2-05 entry in `docs/DEVLOG.md`

---

## Important Context

### Architectural Decisions

| Decision | Reference | Summary |
|----------|-----------|---------|
| Confidence-gated autonomy | R2-Q5 (Option B) | Evaluator self-rates confidence; routes accordingly |
| Brand safety trigger | R2-Q5 | Score <4.0 on any dimension = hard stop; supplements confidence routing |
| Score + confidence dual routing | P1-06 + P2-05 | Score determines what happens; confidence determines how much oversight |

### How Confidence Works in the Evaluator

```python
# From evaluate/evaluator.py — EvaluationResult:
result.scores["clarity"] = {
    "score": 7.5,
    "confidence": 8.0,    # Evaluator's self-rated certainty (1-10)
    ...
}
result.confidence_flags = {"brand_voice": 4.5}  # Only dims with confidence < 7
```

The evaluator's CoT prompt (P1-04) asks: "Step 5: Flag dimensions with confidence < 7." This produces `confidence_flags` dict. Dimensions NOT in `confidence_flags` have confidence ≥ 7.

### Routing Flow

```
evaluate_ad() → EvaluationResult
    ↓
route_ad() (P1-06)         → score-based: discard / escalate / publish
    ↓
route_by_confidence() (P2-05) → confidence-based: autonomous / flagged / human / brand_safety
    ↓
Final decision = most conservative of both
```

### Files to Create

| File | Why |
|------|-----|
| `evaluate/confidence_router.py` | Confidence-based routing |
| `tests/test_pipeline/test_confidence_router.py` | Confidence routing tests |

### Files You Should READ for Context

| File | Why |
|------|-----|
| `evaluate/evaluator.py` | EvaluationResult with confidence_flags |
| `generate/model_router.py` | Existing score-based routing (P1-06) to integrate with |
| `evaluate/dimensions.py` | Floor constraints pattern |
| `iterate/ledger.py` | Event logging |

---

## Definition of Done

- [ ] Confidence routing correctly classifies: autonomous (>7), flagged (5-7), human (<5), brand safety (<4 score)
- [ ] Brand safety hard stop overrides all other routing
- [ ] Integration with score-based routing (most conservative wins)
- [ ] Confidence stats aggregated for dashboard
- [ ] 8+ tests passing
- [ ] Lint clean
- [ ] DEVLOG updated

---

## After This Ticket: What Comes Next

**P2-06 (Tiered Compliance Filter)** implements the three-layer compliance architecture: prompt constraints + evaluator check + regex filter. While confidence routing handles evaluation uncertainty, compliance routing handles policy violations — a separate, non-negotiable gate.
