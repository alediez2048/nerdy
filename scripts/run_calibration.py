#!/usr/bin/env python3
"""Run evaluator calibration against labeled reference ads (P0-06).

Compares evaluator scores to human labels. Success criteria:
- Evaluator within ±1.0 of human labels on 80%+ of scores
- Excellent ads average ≥7.5
- Poor ads average ≤5.0

Requires GEMINI_API_KEY in .env.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

# Add project root to path (must run before importing project modules)
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from evaluate.evaluator import evaluate_ad  # noqa: E402

# Delay between API calls to respect rate limits (config.yaml: api_delay_seconds)
API_DELAY = 1.5

REFERENCE_ADS_PATH = ROOT / "data" / "reference_ads.json"


def _ad_to_eval(ad: dict) -> dict:
    """Extract ad text dict for evaluator."""
    return {
        "ad_id": ad["ad_id"],
        "primary_text": ad["primary_text"],
        "headline": ad["headline"],
        "description": ad["description"],
        "cta_button": ad["cta_button"],
    }


def run_calibration() -> dict:
    """Run evaluator against all labeled reference ads."""
    with open(REFERENCE_ADS_PATH, encoding="utf-8") as f:
        data = json.load(f)

    labeled = [a for a in data["ads"] if "quality_label" in a and "human_scores" in a]

    results = []
    within_tolerance = 0
    total_scores = 0

    for i, ad in enumerate(labeled):
        if i > 0:
            time.sleep(API_DELAY)
        ad_text = _ad_to_eval(ad)
        result = evaluate_ad(ad_text, campaign_goal="conversion")
        human = ad["human_scores"]

        row = {
            "ad_id": ad["ad_id"],
            "label": ad["quality_label"],
            "human_aggregate": sum(human[d] for d in human) / 5,
            "eval_aggregate": result.aggregate_score,
            "dimension_deltas": {},
        }
        for dim in human:
            h = human[dim]
            e = result.scores[dim]["score"]
            delta = abs(e - h)
            row["dimension_deltas"][dim] = {"human": h, "eval": e, "delta": delta}
            if delta <= 1.0:
                within_tolerance += 1
            total_scores += 1
        results.append(row)

    excellent_evals = [r for r in results if r["label"] == "excellent"]
    poor_evals = [r for r in results if r["label"] == "poor"]

    excellent_avg = sum(r["eval_aggregate"] for r in excellent_evals) / len(excellent_evals) if excellent_evals else 0
    poor_avg = sum(r["eval_aggregate"] for r in poor_evals) / len(poor_evals) if poor_evals else 0
    pct_within = (within_tolerance / total_scores * 100) if total_scores else 0

    passed = (
        pct_within >= 80
        and excellent_avg >= 7.5
        and poor_avg <= 5.0
    )

    return {
        "passed": passed,
        "within_tolerance_pct": round(pct_within, 1),
        "excellent_avg": round(excellent_avg, 2),
        "poor_avg": round(poor_avg, 2),
        "n_labeled": len(labeled),
        "n_excellent": len(excellent_evals),
        "n_poor": len(poor_evals),
        "results": results,
    }


def main() -> int:
    """Entry point."""
    print("Running evaluator calibration (P0-06)...")
    print("(This makes real Gemini API calls. Ensure GEMINI_API_KEY is set.)\n")
    try:
        out = run_calibration()
    except Exception as e:
        print(f"Calibration failed: {e}")
        return 1

    print("=" * 60)
    print("CALIBRATION RESULTS")
    print("=" * 60)
    print(f"Scores within ±1.0 of human: {out['within_tolerance_pct']}% (need 80%+)")
    print(f"Excellent ads avg: {out['excellent_avg']} (need ≥7.5)")
    print(f"Poor ads avg: {out['poor_avg']} (need ≤5.0)")
    print(f"PASSED: {out['passed']}")
    print()

    for r in out["results"]:
        print(f"  {r['ad_id']} ({r['label']}): human={r['human_aggregate']:.1f} eval={r['eval_aggregate']:.2f}")

    # Write results for DEVLOG
    out_path = ROOT / "data" / "calibration_results.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(
            {k: v for k, v in out.items() if k != "results"},
            f,
            indent=2,
        )
    print(f"\nSummary written to {out_path}")

    return 0 if out["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
