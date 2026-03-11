---
name: adops-tdd
description: Test-driven development workflow for the Ad-Ops-Autopilot pipeline. Use when implementing any new module, feature, or pipeline stage. Triggers on tasks involving generate/, evaluate/, iterate/, output/, or tests/ directories, or when creating new functionality.
---

# Ad-Ops-Autopilot TDD Workflow

## Cycle

For every module or feature:

1. Write the test file first (`tests/test_<module>.py`)
2. Run the test — confirm it **fails** with the expected assertion
3. Implement the minimum code to make it pass
4. Refactor only after tests are green
5. Run `python -m pytest tests/ -v` to verify no regressions

Never skip step 2. A test that passes before implementation is a bad test.

## Test File Mapping

| Source Module | Test File |
|---------------|-----------|
| `generate/brief_expander.py` | `tests/test_generation/test_brief_expansion.py` |
| `generate/ad_generator.py` | `tests/test_generation/test_ad_generator.py` |
| `generate/compliance.py` | `tests/test_generation/test_compliance.py` |
| `evaluate/evaluator.py` | `tests/test_evaluation/test_golden_set.py` |
| `evaluate/evaluator.py` | `tests/test_evaluation/test_inversion.py` |
| `evaluate/evaluator.py` | `tests/test_evaluation/test_adversarial.py` |
| `evaluate/aggregator.py` | `tests/test_evaluation/test_correlation.py` |
| `iterate/feedback_loop.py` | `tests/test_pipeline/test_checkpoint.py` |
| `iterate/pareto.py` | `tests/test_pipeline/test_batch_processor.py` |
| `iterate/token_tracker.py` | `tests/test_pipeline/test_token_tracking.py` |

## Four Test Categories (Target: 15+)

### 1. Golden Set Regression Tests (P0-07)

Maintain 15–20 "golden" ads with human-assigned scores across all 5 dimensions. Run evaluator against this set as a regression gate.

```python
import pytest
import json

@pytest.fixture
def golden_ads():
    with open("tests/test_data/golden_ads.json") as f:
        return json.load(f)

def test_evaluator_calibration(golden_ads, evaluator):
    """Evaluator scores must be within ±1.0 of human labels on 80%+ of ads."""
    within_tolerance = 0
    for ad in golden_ads:
        result = evaluator.evaluate(ad["text"])
        for dim in ["clarity", "value_proposition", "cta", "brand_voice", "emotional_resonance"]:
            if abs(result.scores[dim].score - ad["human_scores"][dim]) <= 1.0:
                within_tolerance += 1
    total = len(golden_ads) * 5
    assert within_tolerance / total >= 0.80, f"Only {within_tolerance}/{total} within tolerance"
```

### 2. Inversion Tests (P2-01)

Take high-scoring ads, systematically degrade ONE dimension. Verify only that dimension drops.

```python
@pytest.fixture
def degraded_ads():
    with open("tests/test_data/degraded_ads.json") as f:
        return json.load(f)

def test_clarity_inversion(evaluator, degraded_ads):
    """Degrading clarity should drop clarity score ≥1.5 but leave others stable."""
    original = evaluator.evaluate(degraded_ads["original"]["text"])
    degraded = evaluator.evaluate(degraded_ads["clarity_degraded"]["text"])
    
    assert original.scores["clarity"].score - degraded.scores["clarity"].score >= 1.5
    for dim in ["value_proposition", "cta", "brand_voice", "emotional_resonance"]:
        assert abs(original.scores[dim].score - degraded.scores[dim].score) <= 0.5
```

### 3. Adversarial Boundary Tests (P2-03)

Edge cases that probe each dimension's independence.

```python
def test_wrong_brand_voice(evaluator):
    """Ad written in fast-food brand voice should score near 1 on Brand Voice."""
    ad = "🍔 HUNGRY? Grab our MEGA DEAL! Two-for-one burgers, fries, and a shake! Rush in NOW!"
    result = evaluator.evaluate(ad)
    assert result.scores["brand_voice"].score <= 3.0

def test_high_clarity_zero_emotion(evaluator):
    """Purely factual ad should score high Clarity, low Emotional Resonance."""
    ad = "SAT prep tutoring. 1-on-1 sessions. Online scheduling available. Visit website."
    result = evaluator.evaluate(ad)
    assert result.scores["clarity"].score >= 7.0
    assert result.scores["emotional_resonance"].score <= 4.0
```

### 4. Correlation Analysis (P2-02)

Prove dimensions are measured independently — not just a "general quality" halo.

```python
import numpy as np

def test_dimension_independence(evaluation_results):
    """No two dimensions should have Pearson correlation > 0.7."""
    dims = ["clarity", "value_proposition", "cta", "brand_voice", "emotional_resonance"]
    scores = {d: [r.scores[d].score for r in evaluation_results] for d in dims}
    
    for i, d1 in enumerate(dims):
        for d2 in dims[i+1:]:
            r = np.corrcoef(scores[d1], scores[d2])[0, 1]
            assert abs(r) < 0.7, f"{d1} and {d2} correlated at {r:.2f} — halo effect detected"
```

## Pipeline Integration Tests

```python
def test_checkpoint_resume(tmp_path):
    """Pipeline resumes from checkpoint without duplicating work."""
    ledger = tmp_path / "ledger.jsonl"
    # Run pipeline partially, then resume
    run_pipeline(ledger_path=ledger, max_ads=5, stop_after=3)
    lines_after_partial = len(ledger.read_text().strip().split("\n"))
    
    run_pipeline(ledger_path=ledger, max_ads=5, resume=True)
    lines_after_resume = len(ledger.read_text().strip().split("\n"))
    
    # Should have more events but no duplicated ad_ids
    events = [json.loads(l) for l in ledger.read_text().strip().split("\n")]
    ad_gen_events = [e for e in events if e["event_type"] == "AdGenerated"]
    ad_ids = [e["ad_id"] for e in ad_gen_events]
    assert len(ad_ids) == len(set(ad_ids)), "Duplicate ad generations after resume"

def test_seed_reproducibility():
    """Same global_seed + brief_id + cycle = same output seed."""
    from generate.seeds import get_ad_seed
    seed1 = get_ad_seed("test_seed", "brief_001", 1)
    seed2 = get_ad_seed("test_seed", "brief_001", 1)
    assert seed1 == seed2
    
    seed3 = get_ad_seed("test_seed", "brief_001", 2)
    assert seed1 != seed3  # Different cycle = different seed

def test_compliance_filter():
    """Three-layer compliance catches all known violations."""
    violations = [
        "Guaranteed 1500+ SAT score or your money back!",
        "Princeton Review is terrible — choose us instead",
        "100% of students pass with our program, always",
    ]
    from generate.compliance import check_compliance
    for text in violations:
        result = check_compliance(text)
        assert not result.passes, f"Compliance should have caught: {text[:50]}"

def test_token_attribution():
    """Every API call is tagged with purpose."""
    events = load_ledger("tests/test_data/sample_ledger.jsonl")
    api_events = [e for e in events if e.get("tokens_consumed", 0) > 0]
    for event in api_events:
        assert "action" in event, f"Event {event['checkpoint_id']} missing purpose tag"
        assert event["action"] in [
            "generation", "evaluation", "regeneration-attempt-1",
            "regeneration-attempt-2", "regeneration-attempt-3",
            "brief-expansion", "context-distillation", "triage"
        ]
```

## Test Data Files

```
tests/
├── test_data/
│   ├── golden_ads.json          — 15–20 human-scored reference ads
│   ├── adversarial_ads.json     — Edge case ads for boundary testing
│   ├── degraded_ads.json        — High-scoring ads with one dimension degraded
│   ├── sample_ledger.jsonl      — Sample decision ledger for integration tests
│   └── sample_briefs.json       — Test ad briefs
├── conftest.py                  — Shared fixtures
```

## Running Tests

```bash
# All tests
python -m pytest tests/ -v

# Single category
python -m pytest tests/test_evaluation/ -v

# Single file
python -m pytest tests/test_evaluation/test_inversion.py -v

# With coverage summary
python -m pytest tests/ -v --tb=short
```

## Do NOT

- Skip writing tests before implementation
- Delete or modify golden set test data without documenting why in the decision log
- Mock the evaluator LLM in inversion/adversarial tests — these must test real LLM behavior
- Write tests that always pass regardless of implementation
- Treat correlation analysis as optional — if dimensions aren't independent, the evaluation framework is decorative
