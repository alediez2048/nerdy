# PI-01 Primer

**Source plan:** [`PI-PLAN.md`](PI-PLAN.md) — sliced from the ticket section below.
**Phase plan:** [`PI-00-phase-plan.md`](PI-00-phase-plan.md)

**Status:** ✅ Merged on `final-submission`

---

# Ticket PI-01: Ledger event classes

**Goal:** Add `MediaEvaluation` and `MediaEvaluationFailed` event classes to `iterate/ledger_events.py` so subsequent tickets have a target type to write to.

**Files:**
- Modify: `iterate/ledger_events.py`
- Test: `tests/test_pipeline/test_ledger_seam.py` (extend existing)

- [ ] **Step 1: Write the failing test** — append to `tests/test_pipeline/test_ledger_seam.py`:

```python
def test_media_evaluation_event_roundtrip():
    from iterate.ledger_events import MediaEvaluation, parse_event
    ev = MediaEvaluation(
        ad_id="ad_x",
        brief_id="brief_001",
        cycle_number=0,
        action="media_eval_anchor",
        tokens_consumed=1820,
        model_used="gemini-2.5-flash",
        seed="0",
        inputs={"variant_type": "anchor", "media_type": "image"},
        outputs={
            "schema_version": "v2",
            "media_type": "image",
            "media_path": "out/foo.png",
            "dimensions": {
                "thumb_stop_potential": {"score": 7, "weight": 0.20, "rationale": "x"},
            },
            "penalty_gates": {
                "has_ai_artifacts": {"triggered": False, "rationale": "clean"},
            },
            "raw_score": 0.58,
            "penalty_multiplier": 1.0,
            "composite_score": 58.0,
        },
    )
    line = ev.to_jsonl()
    parsed = parse_event(line)
    assert isinstance(parsed, MediaEvaluation)
    assert parsed.outputs["composite_score"] == 58.0
    assert parsed.outputs["schema_version"] == "v2"


def test_media_evaluation_failed_event():
    from iterate.ledger_events import MediaEvaluationFailed, parse_event
    ev = MediaEvaluationFailed(
        ad_id="ad_x",
        brief_id="brief_001",
        cycle_number=0,
        action="media_eval_failed_anchor",
        tokens_consumed=0,
        model_used="gemini-2.5-flash",
        seed="0",
        inputs={"variant_type": "anchor", "media_type": "video"},
        outputs={
            "schema_version": "v2",
            "media_type": "video",
            "failure_reason": "file_not_found",
            "error_message": "videofile.mp4 missing",
        },
    )
    line = ev.to_jsonl()
    parsed = parse_event(line)
    assert isinstance(parsed, MediaEvaluationFailed)
    assert parsed.outputs["failure_reason"] == "file_not_found"
```

- [ ] **Step 2: Run tests to verify they fail**

```
.venv/bin/python -m pytest tests/test_pipeline/test_ledger_seam.py::test_media_evaluation_event_roundtrip tests/test_pipeline/test_ledger_seam.py::test_media_evaluation_failed_event -v
```

Expected: FAIL with `ImportError: cannot import name 'MediaEvaluation'`.

- [ ] **Step 3: Add the event classes to `iterate/ledger_events.py`** — append before the `EVENT_TYPES` registry (look for `EVENT_TYPES = (` at the bottom):

```python
class MediaEvaluation(LedgerEvent):
    """Unified per-variant media quality evaluation (PI-02). Schema v2.

    Replaces ImageEvaluated, ImageScored, VideoEvaluated, VideoCoherenceChecked,
    VideoScored. The outputs dict carries the full rubric: per-dimension
    {score, weight, rationale}, per-gate {triggered, rationale},
    raw_score / penalty_multiplier / composite_score, and schema_version.
    """
    event_type: str = "MediaEvaluation"


class MediaEvaluationFailed(LedgerEvent):
    """Explicit failure event for a single variant (PI-02).

    Emitted when the evaluator cannot produce a MediaEvaluation — e.g.
    file missing, upload too large, LLM JSON unparseable. Selection skips
    failed variants; if all variants for an ad fail, the ad is
    regenerated via the existing P1-08 brief-mutation flow.
    """
    event_type: str = "MediaEvaluationFailed"
```

- [ ] **Step 4: Register them in the `EVENT_TYPES` tuple** — find the existing tuple (currently includes `ImageEvaluated, ImageScored, VideoEvaluated, ...`) and add the two new classes:

```python
EVENT_TYPES = (
    # ... existing entries ...
    ImageEvaluated,
    ImageScored,
    VideoEvaluated,
    VideoCoherenceChecked,
    VideoScored,
    MediaEvaluation,         # PI-01
    MediaEvaluationFailed,   # PI-01
)
```

- [ ] **Step 5: Run tests to verify they pass**

```
.venv/bin/python -m pytest tests/test_pipeline/test_ledger_seam.py -v
```

Expected: all green (previous tests + 2 new ones).

- [ ] **Step 6: Commit**

```
git add iterate/ledger_events.py tests/test_pipeline/test_ledger_seam.py
git commit -m "feat(PI-01): MediaEvaluation + MediaEvaluationFailed ledger events"
```

---
