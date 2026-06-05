"""Golden-set calibration test for media_quality evaluator (PI-09).

Opt-in: requires GEMINI_API_KEY AND populated fixture media. Skips
cleanly when either is missing so the default CI gate stays green.
Runs nightly + on prompt changes — see docs/development/tickets/PI-09.

Asserts:
  1. obviously-great items score above the tier ceiling
  2. obviously-bad items score below the tier floor
  3. within each tier the spread (max − min) is ≥ a small floor
  4. overall composite values are distinct enough to hit the
     granularity target from PI-00 (≥ 8 distinct image composites)
  5. planted "bad" gates fire as expected
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest
import yaml

from evaluate.media_quality import evaluate_media

FIXTURES = Path(__file__).parent / "fixtures" / "media_quality"
ANNOTATIONS_PATH = FIXTURES / "annotations.yaml"
ANNOTATIONS = yaml.safe_load(ANNOTATIONS_PATH.read_text()) if ANNOTATIONS_PATH.exists() else {}


def _fixtures_present(subdir: str, items: list[dict]) -> bool:
    if not items:
        return False
    return all((FIXTURES / subdir / it["file"]).exists() for it in items)


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
            ad_copy=_ad_copy(),
            ad_id=item["file"],
            variant_type="calibration",
            media_type=media_type,
        )
        assert not result.failed, (
            f"Calibration eval failed for {item['file']}: {result.failure_reason}"
        )
        out.append({"item": item, "result": result})
    return out


@requires_api
@pytest.mark.calibration
def test_image_calibration_spread_and_tier_separation():
    items = ANNOTATIONS.get("images", [])
    if not _fixtures_present("images", items):
        pytest.skip("image golden-set fixtures not populated; see annotations.yaml")

    rated = _evaluate_all(items, "images", "image")
    scores_by_tier: dict[str, list[float]] = {"great": [], "mid": [], "bad": []}
    for r in rated:
        scores_by_tier[r["item"]["tier"]].append(r["result"].composite_score)

    for s in scores_by_tier["great"]:
        assert s > 70, f"great image scored {s}, expected > 70"
    for s in scores_by_tier["bad"]:
        assert s < 35, f"bad image scored {s}, expected < 35"

    for tier in ("great", "mid", "bad"):
        scores = scores_by_tier[tier]
        if len(scores) >= 2:
            assert max(scores) - min(scores) >= 10, (
                f"{tier} tier collapsed: {scores}"
            )

    all_scores = sorted({round(r["result"].composite_score, 1) for r in rated})
    assert len(all_scores) >= 8, (
        f"only {len(all_scores)} distinct composites across {len(rated)} images: {all_scores}"
    )

    bad_results = [r["result"] for r in rated if r["item"]["tier"] == "bad"]
    artifact_triggered = [
        r for r in bad_results
        if r.penalty_gates.get("has_ai_artifacts")
        and r.penalty_gates["has_ai_artifacts"].triggered
    ]
    assert len(artifact_triggered) >= 2, (
        f"only {len(artifact_triggered)}/{len(bad_results)} planted bad images triggered has_ai_artifacts"
    )


@requires_api
@pytest.mark.calibration
def test_video_calibration_spread_and_tier_separation():
    items = ANNOTATIONS.get("videos", [])
    if not _fixtures_present("videos", items):
        pytest.skip("video golden-set fixtures not populated; see annotations.yaml")

    rated = _evaluate_all(items, "videos", "video")
    scores_by_tier: dict[str, list[float]] = {"great": [], "mid": [], "bad": []}
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


def test_calibration_annotations_well_formed():
    """Cheap sanity check that runs without GEMINI_API_KEY — guards the YAML."""
    assert ANNOTATIONS, "annotations.yaml missing or empty"
    assert "images" in ANNOTATIONS and "videos" in ANNOTATIONS
    assert len(ANNOTATIONS["images"]) == 12, "expected 12 image fixtures"
    assert len(ANNOTATIONS["videos"]) == 8, "expected 8 video fixtures"

    image_tiers = [it["tier"] for it in ANNOTATIONS["images"]]
    video_tiers = [it["tier"] for it in ANNOTATIONS["videos"]]
    assert image_tiers.count("great") == 4
    assert image_tiers.count("mid") == 4
    assert image_tiers.count("bad") == 4
    assert video_tiers.count("great") == 3
    assert video_tiers.count("mid") == 3
    assert video_tiers.count("bad") == 2

    for it in ANNOTATIONS["images"] + ANNOTATIONS["videos"]:
        assert {"file", "tier", "source", "notes"} <= set(it.keys())
