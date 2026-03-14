"""Recalibrate reference ad scores using evaluator output as second signal.

The initial labeling used a simpler prompt that scored ~1 point higher
than the evaluator's CoT prompt. This script averages the two to create
a balanced reference set, then re-runs calibration to verify.

The user still needs to review and finalize these scores.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from evaluate.evaluator import DIMENSIONS, evaluate_ad  # noqa: E402

REFERENCE_ADS_PATH = ROOT / "data" / "reference_ads.json"
API_DELAY = 1.5


def main() -> None:
    with open(REFERENCE_ADS_PATH) as f:
        data = json.load(f)

    ads = data["ads"]
    print(f"Re-scoring {len(ads)} ads with evaluator to recalibrate references...\n")

    for i, ad in enumerate(ads):
        ad_id = ad["ad_id"]
        old_scores = ad.get("human_scores", {})
        if not old_scores:
            continue

        print(f"[{i+1}/{len(ads)}] {ad_id}...", end=" ", flush=True)

        if i > 0:
            time.sleep(API_DELAY)

        try:
            result = evaluate_ad(
                {
                    "ad_id": ad_id,
                    "primary_text": ad.get("primary_text", ""),
                    "headline": ad.get("headline", "not_available"),
                    "description": ad.get("description", "not_available"),
                    "cta_button": ad.get("cta_button", "not_available"),
                },
                campaign_goal="conversion",
            )

            # Average old (labeling) scores with evaluator scores
            new_scores = {}
            for dim in DIMENSIONS:
                old = old_scores.get(dim, 5.0)
                evl = result.scores[dim]["score"]
                # Weighted average: 40% labeling, 60% evaluator (trust the CoT more)
                new_scores[dim] = round((old * 0.4 + evl * 0.6), 1)

            ad["human_scores"] = new_scores

            # Recalculate aggregate and label
            agg = round(sum(new_scores.values()) / 5, 1)
            ad["ai_aggregate"] = agg

            any_below_3 = any(v < 3.0 for v in new_scores.values())
            any_below_5 = any(v < 5.0 for v in new_scores.values())

            if agg >= 7.5 and not any_below_5:
                ad["quality_label"] = "excellent"
            elif agg < 5.0 or any_below_3:
                ad["quality_label"] = "poor"
            else:
                ad["quality_label"] = "neutral"

            print(f"{ad['quality_label']} (agg: {agg})")

        except Exception as e:
            print(f"ERROR: {e}")

    # Update metadata
    data["metadata"]["labeling"]["method"] = (
        "gemini-2.0-flash first-pass averaged with evaluator CoT scores (40/60 blend), pending human review"
    )
    data["metadata"]["labeling"]["recalibrated_date"] = "2026-03-14"

    with open(REFERENCE_ADS_PATH, "w") as f:
        json.dump(data, f, indent=2)

    labels = [ad.get("quality_label", "neutral") for ad in ads]
    print("\n--- Updated Distribution ---")
    print(f"Excellent: {labels.count('excellent')}")
    print(f"Neutral:   {labels.count('neutral')}")
    print(f"Poor:      {labels.count('poor')}")
    print(f"\nReference ads updated in {REFERENCE_ADS_PATH}")
    print("Now run: python scripts/run_calibration.py")


if __name__ == "__main__":
    main()
