"""Ad library export — JSON and CSV with full metadata (P5-10).

Reads the JSONL ledger and reconstructs each ad's complete lifecycle,
scores, rationales, and status into exportable formats.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

from iterate.ledger import read_events

DIMENSIONS = ("clarity", "value_proposition", "cta", "brand_voice", "emotional_resonance")


def build_ad_library(ledger_path: str) -> list[dict]:
    """Build the complete ad library from ledger events.

    Args:
        ledger_path: Path to the JSONL ledger.

    Returns:
        List of ad dicts with full metadata.
    """
    events = read_events(ledger_path)

    # Index events by ad_id
    gen_by_ad: dict[str, dict] = {}
    eval_by_ad: dict[str, list[dict]] = {}
    status_map: dict[str, str] = {}
    tokens_by_ad: dict[str, int] = {}

    for e in events:
        aid = e.get("ad_id", "")
        if not aid:
            continue

        etype = e.get("event_type", "")
        tokens_by_ad[aid] = tokens_by_ad.get(aid, 0) + e.get("tokens_consumed", 0)

        if etype == "AdGenerated":
            gen_by_ad[aid] = e
        elif etype == "AdEvaluated":
            eval_by_ad.setdefault(aid, []).append(e)
        elif etype == "AdPublished":
            status_map[aid] = "published"
        elif etype == "AdDiscarded":
            status_map[aid] = "discarded"

    ads: list[dict] = []
    for aid, gen in gen_by_ad.items():
        evals = eval_by_ad.get(aid, [])
        evals.sort(key=lambda x: x.get("cycle_number", 0))
        latest_eval = evals[-1] if evals else None

        outputs = gen.get("outputs", {})
        eval_outputs = latest_eval.get("outputs", {}) if latest_eval else {}
        scores = eval_outputs.get("scores", {})
        aggregate = eval_outputs.get("aggregate_score", 0.0)
        rationale = eval_outputs.get("rationale", {})
        cycle_count = max((ev.get("cycle_number", 0) for ev in evals), default=0)

        ads.append({
            "ad_id": aid,
            "brief_id": gen.get("brief_id", ""),
            "copy": {
                "headline": outputs.get("headline", ""),
                "primary_text": outputs.get("primary_text", ""),
                "description": outputs.get("description", ""),
                "cta_button": outputs.get("cta_button", ""),
            },
            "scores": scores,
            "aggregate_score": aggregate,
            "rationale": rationale,
            "status": status_map.get(aid, "in_progress"),
            "cycle_count": cycle_count,
            "model_used": gen.get("model_used", "unknown"),
            "tokens_total": tokens_by_ad.get(aid, 0),
            "seed": gen.get("seed", ""),
            "audience": gen.get("inputs", {}).get("audience", ""),
            "campaign_goal": gen.get("inputs", {}).get("campaign_goal", ""),
        })

    return ads


def _build_summary(ads: list[dict]) -> dict:
    """Build summary statistics from ad list."""
    total = len(ads)
    publishable = [a for a in ads if a["aggregate_score"] >= 7.0]
    all_scores = [a["aggregate_score"] for a in ads if a["aggregate_score"] > 0]
    pub_scores = [a["aggregate_score"] for a in publishable]
    total_tokens = sum(a["tokens_total"] for a in ads)

    # Per-dimension averages
    dim_totals: dict[str, list[float]] = {d: [] for d in DIMENSIONS}
    for a in ads:
        for d in DIMENSIONS:
            val = a["scores"].get(d)
            if isinstance(val, (int, float)):
                dim_totals[d].append(float(val))

    per_dim_avg = {
        d: round(sum(vals) / len(vals), 2) if vals else 0.0
        for d, vals in dim_totals.items()
    }

    return {
        "total_ads": total,
        "total_publishable": len(publishable),
        "avg_score": round(sum(all_scores) / len(all_scores), 2) if all_scores else 0.0,
        "avg_publishable_score": round(sum(pub_scores) / len(pub_scores), 2) if pub_scores else 0.0,
        "per_dimension_avg": per_dim_avg,
        "total_tokens": total_tokens,
        "cost_per_publishable": round(total_tokens / max(len(publishable), 1), 0),
    }


def export_ad_library_json(
    ledger_path: str = "data/ledger.jsonl",
    output_path: str = "output/ad_library.json",
) -> None:
    """Export ad library as JSON with summary header.

    Args:
        ledger_path: Path to the JSONL ledger.
        output_path: Path for output JSON file.
    """
    ads = build_ad_library(ledger_path)
    summary = _build_summary(ads)

    data = {
        "summary": summary,
        "ads": sorted(ads, key=lambda a: a["aggregate_score"], reverse=True),
    }

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(data, f, indent=2, default=str)


def export_ad_library_csv(
    ledger_path: str = "data/ledger.jsonl",
    output_path: str = "output/ad_library.csv",
) -> None:
    """Export ad library as flattened CSV sorted by score descending.

    Args:
        ledger_path: Path to the JSONL ledger.
        output_path: Path for output CSV file.
    """
    ads = build_ad_library(ledger_path)
    ads.sort(key=lambda a: a["aggregate_score"], reverse=True)

    fieldnames = [
        "ad_id", "brief_id", "status", "aggregate_score",
        "clarity", "value_proposition", "cta", "brand_voice", "emotional_resonance",
        "headline", "primary_text", "description", "cta_button",
        "cycle_count", "model_used", "tokens_total", "seed",
        "audience", "campaign_goal",
    ]

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for ad in ads:
            row = {
                "ad_id": ad["ad_id"],
                "brief_id": ad["brief_id"],
                "status": ad["status"],
                "aggregate_score": ad["aggregate_score"],
                "headline": ad["copy"].get("headline", ""),
                "primary_text": ad["copy"].get("primary_text", ""),
                "description": ad["copy"].get("description", ""),
                "cta_button": ad["copy"].get("cta_button", ""),
                "cycle_count": ad["cycle_count"],
                "model_used": ad["model_used"],
                "tokens_total": ad["tokens_total"],
                "seed": ad["seed"],
                "audience": ad["audience"],
                "campaign_goal": ad["campaign_goal"],
            }
            for d in DIMENSIONS:
                row[d] = ad["scores"].get(d, "")
            writer.writerow(row)


def main() -> None:
    """CLI entry point."""
    import sys
    ledger = sys.argv[1] if len(sys.argv) > 1 else "data/ledger.jsonl"
    export_ad_library_json(ledger)
    export_ad_library_csv(ledger)
    print("Ad library exported to output/ad_library.json and output/ad_library.csv")


if __name__ == "__main__":
    main()
