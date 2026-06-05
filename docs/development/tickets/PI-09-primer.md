# PI-09 Primer

**Source plan:** [`PI-PLAN.md`](PI-PLAN.md) — sliced from the ticket section below.
**Phase plan:** [`PI-00-phase-plan.md`](PI-00-phase-plan.md)

**Status:** ⏳ Not started

---

# Ticket PI-09: Calibration golden set + spread test

**Goal:** Assemble a 12-image + 8-video golden set with tier labels. Add an opt-in pytest marker `calibration` that runs the unified evaluator against each item and asserts the spread + tier separation contracts. This test is the granularity canary.

**Files:**
- Create: `tests/test_evaluation/fixtures/media_quality/annotations.yaml`
- Create: `tests/test_evaluation/fixtures/media_quality/images/` (12 files)
- Create: `tests/test_evaluation/fixtures/media_quality/videos/` (8 files)
- Create: `tests/test_evaluation/test_media_quality_calibration.py`
- Modify: `pyproject.toml` — register the `calibration` pytest marker

- [ ] **Step 1: Source the 12 image references**

Walk `data/sessions/sess_*/` and copy 12 representative `.png` files to `tests/test_evaluation/fixtures/media_quality/images/`:
- 4 obviously-great (winners from past sessions with strong composition)
- 4 mediocre (mid-pack winners)
- 4 obviously-bad (planted with: blurry, off-brand, AI-artifact hands, generic stock-photo)

If you can't find 4 obviously-bad in the historical data, hand-create 4 from public-domain bad-AI-image collections. Document the source of each in `annotations.yaml`.

- [ ] **Step 2: Source the 8 video references**

Same process for 8 video files (`.mp4`) from `data/sessions/sess_*/videos/`:
- 3 great (clean Veo outputs)
- 3 mid
- 2 bad (intentionally pick clips with `has_temporal_artifacts` triggers — flickering frames, morphing faces across cuts)

- [ ] **Step 3: Write the annotations file** — `tests/test_evaluation/fixtures/media_quality/annotations.yaml`:

```yaml
# Calibration golden set — PI-09
# tier: great | mid | bad
# source: where the file came from (session_id or hand-curated)
images:
  - file: img_great_01.png
    tier: great
    source: sess_f71c27911fe08803/images/anchor_1x1.png
    notes: strong focal point, brand colors, clean composition
  # ...11 more
videos:
  - file: vid_great_01.mp4
    tier: great
    source: sess_aaf2ccf3ca302cea/videos/anchor_9x16.mp4
    notes: clean Veo output, hook within 1s, smooth motion
  # ...7 more
```

- [ ] **Step 4: Register the `calibration` marker** — append to `pyproject.toml`:

```toml
[tool.pytest.ini_options]
markers = [
    "calibration: opt-in golden-set tests that hit the real Gemini API. Skipped unless GEMINI_API_KEY is set.",
]
```

- [ ] **Step 5: Write the calibration test** — `tests/test_evaluation/test_media_quality_calibration.py`:

```python
"""Golden-set calibration test for media_quality evaluator (PI-09).

Opt-in: requires GEMINI_API_KEY. Runs nightly + on prompt changes.
Asserts spread, tier separation, and that planted gate triggers fire.
"""
from __future__ import annotations

import os
from pathlib import Path
import yaml
import pytest

from evaluate.media_quality import evaluate_media

FIXTURES = Path(__file__).parent / "fixtures" / "media_quality"
ANNOTATIONS = yaml.safe_load((FIXTURES / "annotations.yaml").read_text())

requires_api = pytest.mark.skipif(
    not os.getenv("GEMINI_API_KEY"),
    reason="GEMINI_API_KEY not set — calibration test is opt-in",
)


def _ad_copy() -> dict:
    return {
        "headline": "Ace Your SAT with Expert Tutors",
        "primary_text": "1-on-1 tutoring that builds confidence and raises scores.",
        "cta_button": "Start Today",
    }


def _evaluate_all(items: list[dict], media_subdir: str, media_type: str) -> list[dict]:
    out = []
    for item in items:
        result = evaluate_media(
            media_path=str(FIXTURES / media_subdir / item["file"]),
            ad_copy=_ad_copy(), ad_id=item["file"], variant_type="calibration",
            media_type=media_type,
        )
        assert not result.failed, f"Calibration eval failed for {item['file']}: {result.failure_reason}"
        out.append({"item": item, "result": result})
    return out


@requires_api
@pytest.mark.calibration
def test_image_calibration_spread_and_tier_separation():
    rated = _evaluate_all(ANNOTATIONS["images"], "images", "image")
    scores_by_tier = {"great": [], "mid": [], "bad": []}
    for r in rated:
        scores_by_tier[r["item"]["tier"]].append(r["result"].composite_score)

    # 1. Obvious tiers separate
    for s in scores_by_tier["great"]:
        assert s > 70, f"great image scored {s}, expected > 70"
    for s in scores_by_tier["bad"]:
        assert s < 35, f"bad image scored {s}, expected < 35"

    # 2. Within-tier spread
    for tier in ("great", "mid", "bad"):
        scores = scores_by_tier[tier]
        assert max(scores) - min(scores) >= 10, (
            f"{tier} tier collapsed: {scores}"
        )

    # 3. Overall granularity
    all_scores = sorted({round(r["result"].composite_score, 1) for r in rated})
    assert len(all_scores) >= 8, (
        f"only {len(all_scores)} distinct composites across {len(rated)} images: {all_scores}"
    )

    # 4. Planted bad images trigger has_ai_artifacts
    bad_results = [r["result"] for r in rated if r["item"]["tier"] == "bad"]
    artifact_triggered = [r for r in bad_results
                          if r.penalty_gates.get("has_ai_artifacts", None) and r.penalty_gates["has_ai_artifacts"].triggered]
    assert len(artifact_triggered) >= 2, (
        f"only {len(artifact_triggered)}/{len(bad_results)} planted bad images triggered has_ai_artifacts"
    )


@requires_api
@pytest.mark.calibration
def test_video_calibration_spread_and_tier_separation():
    rated = _evaluate_all(ANNOTATIONS["videos"], "videos", "video")
    scores_by_tier = {"great": [], "mid": [], "bad": []}
    for r in rated:
        scores_by_tier[r["item"]["tier"]].append(r["result"].composite_score)

    for s in scores_by_tier["great"]:
        assert s > 60, f"great video scored {s}"
    for s in scores_by_tier["bad"]:
        assert s < 40, f"bad video scored {s}"

    all_scores = sorted({round(r["result"].composite_score, 1) for r in rated})
    assert len(all_scores) >= 6, (
        f"only {len(all_scores)} distinct composites across {len(rated)} videos"
    )
```

- [ ] **Step 6: Run the calibration test against real API**

```
.venv/bin/python -m pytest tests/test_evaluation/test_media_quality_calibration.py -m calibration -v
```

Expected: PASS. If FAIL, iterate on the prompt in `media_quality.py` (most likely lever: strengthen "calibration" paragraph that pushes scores away from the middle). Budget 2–4 prompt-tuning cycles. Each cycle: edit prompt → run test → read which assertion failed → adjust.

- [ ] **Step 7: Commit**

```
git add tests/test_evaluation/fixtures/media_quality/ tests/test_evaluation/test_media_quality_calibration.py pyproject.toml
git commit -m "feat(PI-09): golden-set calibration test — granularity canary"
```

---
