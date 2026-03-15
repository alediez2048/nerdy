"""Dashboard data export — reads JSONL ledger, produces dashboard_data.json (P5-01).

Aggregates all pipeline data into a single JSON file consumed by the
8-panel HTML dashboard. Calls existing module functions — no duplicated logic.
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from iterate.ledger import read_events

logger = logging.getLogger(__name__)

DIMENSIONS = ("clarity", "value_proposition", "cta", "brand_voice", "emotional_resonance")


def _build_pipeline_summary(events: list[dict]) -> dict:
    """Panel 1: Hero KPIs."""
    generated = sum(1 for e in events if e.get("event_type") == "AdGenerated")
    published = sum(1 for e in events if e.get("event_type") == "AdPublished")
    discarded = sum(1 for e in events if e.get("event_type") == "AdDiscarded")
    batches = sum(1 for e in events if e.get("event_type") == "BatchCompleted")
    total_tokens = sum(e.get("tokens_consumed", 0) for e in events)

    # Compute avg score across published ads
    pub_scores: list[float] = []
    for e in events:
        if e.get("event_type") == "AdPublished":
            score = e.get("inputs", {}).get("aggregate_score")
            if score is not None:
                pub_scores.append(float(score))

    avg_score = round(sum(pub_scores) / len(pub_scores), 1) if pub_scores else 0.0
    publish_rate = round(published / max(generated, 1), 3)

    # Estimate USD cost using cost_reporter if available
    total_cost_usd = 0.0
    try:
        from evaluate.cost_reporter import MODEL_COST_RATES
        for e in events:
            model = e.get("model_used", "unknown")
            tokens = e.get("tokens_consumed", 0)
            rate = MODEL_COST_RATES.get(model, 0.01 / 1000)
            total_cost_usd += rate * tokens
        total_cost_usd = round(total_cost_usd, 4)
    except ImportError:
        pass

    return {
        "total_ads_generated": generated,
        "total_ads_published": published,
        "total_ads_discarded": discarded,
        "publish_rate": publish_rate,
        "total_batches": batches,
        "total_tokens": total_tokens,
        "total_cost_usd": total_cost_usd,
        "avg_score": avg_score,
    }


def _build_iteration_cycles(events: list[dict]) -> list[dict]:
    """Panel 2: Per-ad before/after improvement cards."""
    # Group evaluation events by ad_id
    eval_by_ad: dict[str, list[dict]] = defaultdict(list)
    for e in events:
        if e.get("event_type") == "AdEvaluated":
            eval_by_ad[e["ad_id"]].append(e)

    # Determine final status per ad
    status_map: dict[str, str] = {}
    for e in events:
        if e.get("event_type") == "AdPublished":
            status_map[e["ad_id"]] = "published"
        elif e.get("event_type") == "AdDiscarded":
            status_map[e["ad_id"]] = "discarded"

    cycles: list[dict] = []
    for ad_id, evals in eval_by_ad.items():
        evals.sort(key=lambda x: x.get("cycle_number", 0))
        if len(evals) < 2:
            continue

        first = evals[0]
        last = evals[-1]
        score_before = first.get("outputs", {}).get("aggregate_score", 0.0)
        score_after = last.get("outputs", {}).get("aggregate_score", 0.0)

        # Find weakest dimension from first evaluation
        scores = first.get("outputs", {}).get("scores", {})
        weakest = "unknown"
        if scores:
            def _dim_score(d: str) -> float:
                val = scores.get(d, 10)
                if isinstance(val, dict):
                    return val.get("score", 10)
                if isinstance(val, (int, float)):
                    return val
                return 10
            weakest = min(
                (d for d in DIMENSIONS if d in scores),
                key=_dim_score,
                default="unknown",
            )

        cycles.append({
            "ad_id": ad_id,
            "cycle": last.get("cycle_number", len(evals)),
            "score_before": score_before,
            "score_after": score_after,
            "weakest_dimension": weakest,
            "action_taken": status_map.get(ad_id, "regenerated"),
        })

    # Sort by improvement (biggest first)
    cycles.sort(key=lambda c: c["score_after"] - c["score_before"], reverse=True)
    return cycles


def _build_quality_trends(events: list[dict]) -> dict:
    """Panel 3: Score progression over batches."""
    batch_events = [e for e in events if e.get("event_type") == "BatchCompleted"]
    batch_events.sort(key=lambda e: e.get("timestamp", ""))

    # Also collect per-batch token costs
    all_events = events  # full event list for token aggregation
    batch_token_map: dict[int, int] = defaultdict(int)
    current_batch = 0
    for e in all_events:
        if e.get("event_type") == "BatchCompleted":
            current_batch = e.get("outputs", {}).get("batch_num", current_batch + 1)
        batch_token_map[current_batch] += e.get("tokens_consumed", 0)

    # Collect all evaluation scores for distribution
    all_eval_scores: list[float] = []
    for e in all_events:
        if e.get("event_type") == "AdEvaluated":
            agg = e.get("outputs", {}).get("aggregate_score")
            if isinstance(agg, (int, float)) and agg > 0:
                all_eval_scores.append(float(agg))

    batch_scores: list[dict] = []
    for i, e in enumerate(batch_events, 1):
        outputs = e.get("outputs", {})
        avg = outputs.get("batch_average", outputs.get("batch_avg_score", 0.0))
        generated = outputs.get("generated", 0)
        published = outputs.get("published", 0)
        pub_rate = round(published / max(generated, 1), 2)
        batch_num = outputs.get("batch_num", i)
        batch_scores.append({
            "batch": batch_num,
            "avg_score": avg,
            "threshold": 7.0,
            "published": published,
            "generated": generated,
            "publish_rate": pub_rate,
            "tokens": batch_token_map.get(batch_num, 0),
        })

    # Ratchet history — compute monotonically increasing thresholds
    ratchet_history: list[dict] = []
    current_max = 7.0
    for bs in batch_scores:
        current_max = max(current_max, bs["avg_score"] - 0.5)
        current_max = max(current_max, 7.0)
        ratchet_history.append({
            "batch": bs["batch"],
            "threshold": round(current_max, 2),
        })

    # Score distribution histogram (buckets: 1-2, 2-3, ..., 9-10)
    distribution: list[int] = [0] * 10
    for s in all_eval_scores:
        bucket = min(int(s), 9)
        distribution[bucket] += 1

    return {
        "batch_scores": batch_scores,
        "ratchet_history": ratchet_history,
        "score_distribution": distribution,
    }


def _build_dimension_deep_dive(events: list[dict]) -> dict:
    """Panel 4: Per-dimension trends + correlation matrix."""
    eval_events = [e for e in events if e.get("event_type") == "AdEvaluated"]

    # Group by batch (use cycle as proxy if no batch info)
    dim_trends: dict[str, list[float]] = {d: [] for d in DIMENSIONS}

    for e in eval_events:
        scores = e.get("outputs", {}).get("scores", {})
        for dim in DIMENSIONS:
            val = scores.get(dim)
            if isinstance(val, dict):
                val = val.get("score")
            if isinstance(val, (int, float)):
                dim_trends[dim].append(float(val))

    # Correlation matrix
    correlation: dict[str, dict[str, float]] = {}
    try:
        from evaluate.correlation import compute_correlation_matrix
        score_dicts = []
        for e in eval_events:
            scores = e.get("outputs", {}).get("scores", {})
            parsed: dict[str, float] = {}
            for dim in DIMENSIONS:
                val = scores.get(dim)
                if isinstance(val, dict):
                    val = val.get("score")
                if isinstance(val, (int, float)):
                    parsed[dim] = float(val)
            if len(parsed) == len(DIMENSIONS):
                score_dicts.append(parsed)
        if score_dicts:
            matrix = compute_correlation_matrix(score_dicts)
            for (d1, d2), r in matrix.items():
                correlation.setdefault(d1, {})[d2] = round(r, 3)
    except ImportError:
        pass

    return {
        "dimension_trends": dim_trends,
        "correlation_matrix": correlation,
    }


def _build_ad_library(events: list[dict]) -> list[dict]:
    """Panel 5: All ads with copy, scores, rationales."""
    # Find all unique ad_ids from AdGenerated events
    ad_ids: list[str] = []
    seen: set[str] = set()
    for e in events:
        if e.get("event_type") == "AdGenerated":
            aid = e["ad_id"]
            if aid not in seen:
                ad_ids.append(aid)
                seen.add(aid)

    # Status map
    status_map: dict[str, str] = {}
    for e in events:
        if e.get("event_type") == "AdPublished":
            status_map[e["ad_id"]] = "published"
        elif e.get("event_type") == "AdDiscarded":
            status_map[e["ad_id"]] = "discarded"

    library: list[dict] = []
    for ad_id in ad_ids:
        ad_events = [e for e in events if e.get("ad_id") == ad_id]

        # Get latest evaluation
        evals = [e for e in ad_events if e.get("event_type") == "AdEvaluated"]
        evals.sort(key=lambda x: x.get("cycle_number", 0))
        latest_eval = evals[-1] if evals else None

        # Get generation event for copy
        gen_events = [e for e in ad_events if e.get("event_type") == "AdGenerated"]
        gen = gen_events[0] if gen_events else None

        # Get copy from latest generation or regeneration
        regen_events = [e for e in ad_events if e.get("event_type") == "AdRegenerated"]
        regen_events.sort(key=lambda x: x.get("cycle_number", 0))
        copy_source = regen_events[-1] if regen_events else gen

        copy_data = copy_source.get("outputs", {}) if copy_source else {}
        raw_scores = latest_eval.get("outputs", {}).get("scores", {}) if latest_eval else {}
        # Flatten nested score dicts to plain numbers for dashboard
        scores: dict[str, float] = {}
        rationale: dict[str, str] = {}
        for dim in DIMENSIONS:
            val = raw_scores.get(dim)
            if isinstance(val, dict):
                scores[dim] = val.get("score", 0)
                rationale[dim] = val.get("rationale", "")
            elif isinstance(val, (int, float)):
                scores[dim] = float(val)
        aggregate = latest_eval.get("outputs", {}).get("aggregate_score", 0.0) if latest_eval else 0.0
        cycle_count = max((e.get("cycle_number", 0) for e in ad_events), default=1)

        library.append({
            "ad_id": ad_id,
            "brief_id": gen.get("brief_id", "") if gen else "",
            "copy": copy_data,
            "scores": scores,
            "aggregate_score": aggregate,
            "rationale": rationale,
            "status": status_map.get(ad_id, "in_progress"),
            "cycle_count": cycle_count,
            "image_path": None,
        })

    return library


def _build_token_economics(ledger_path: str) -> dict:
    """Panel 6: Cost attribution + marginal analysis."""
    from iterate.token_tracker import get_token_summary

    summary = get_token_summary(ledger_path)

    # Marginal analysis
    marginal: dict = {}
    try:
        from iterate.marginal_analysis import get_marginal_dashboard_data
        marginal = get_marginal_dashboard_data(ledger_path)
    except Exception:
        pass

    return {
        "by_stage": summary.by_stage,
        "by_model": summary.by_model,
        "cost_per_published": round(summary.cost_per_published, 2) if summary.cost_per_published != float("inf") else 0,
        "marginal_analysis": marginal,
    }


def _build_system_health(ledger_path: str) -> dict:
    """Panel 7: SPC + confidence + compliance."""
    # SPC
    spc_data: dict = {"batch_averages": [], "ucl": None, "lcl": None, "mean": None, "breach_indices": []}
    try:
        from evaluate.spc_monitor import get_control_chart_data
        chart = get_control_chart_data(ledger_path)
        spc_data = {
            "batch_averages": chart.batch_averages,
            "ucl": chart.ucl,
            "lcl": chart.lcl,
            "mean": chart.mean,
            "breach_indices": chart.breach_indices,
        }
    except Exception:
        pass

    # Confidence stats
    confidence: dict = {}
    try:
        from evaluate.confidence_router import get_confidence_stats
        stats = get_confidence_stats(ledger_path)
        confidence = {
            "autonomous_count": stats.autonomous_count,
            "flagged_count": stats.flagged_count,
            "human_required_count": stats.human_required_count,
            "brand_safety_count": stats.brand_safety_count,
            "total": stats.total,
            "autonomous_pct": stats.autonomous_pct,
            "flagged_pct": stats.flagged_pct,
            "human_required_pct": stats.human_required_pct,
        }
    except Exception:
        pass

    # Compliance stats
    events = read_events(ledger_path)
    compliance_pass = sum(1 for e in events if e.get("event_type") == "AdPublished")
    compliance_fail = sum(1 for e in events if e.get("event_type") == "AdDiscarded")

    return {
        "spc": spc_data,
        "confidence_stats": confidence,
        "compliance_stats": {
            "total_checked": compliance_pass + compliance_fail,
            "passed": compliance_pass,
            "failed": compliance_fail,
            "pass_rate": round(compliance_pass / max(compliance_pass + compliance_fail, 1), 2),
        },
    }


def _build_competitive_intel(ledger_path: str) -> dict:
    """Panel 8: Competitive intelligence."""
    try:
        from generate.competitive import load_patterns
        from generate.competitive_trends import get_competitive_dashboard_data
        patterns = load_patterns()
        return get_competitive_dashboard_data(patterns)
    except Exception:
        return {}


def build_dashboard_data(ledger_path: str) -> dict:
    """Build the complete dashboard data structure from a ledger.

    Args:
        ledger_path: Path to the JSONL ledger.

    Returns:
        Dict with all 8 panel data sections.
    """
    events = read_events(ledger_path)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "ledger_path": ledger_path,
        "pipeline_summary": _build_pipeline_summary(events),
        "iteration_cycles": _build_iteration_cycles(events),
        "quality_trends": _build_quality_trends(events),
        "dimension_deep_dive": _build_dimension_deep_dive(events),
        "ad_library": _build_ad_library(events),
        "token_economics": _build_token_economics(ledger_path),
        "system_health": _build_system_health(ledger_path),
        "competitive_intel": _build_competitive_intel(ledger_path),
    }


def export_dashboard(
    ledger_path: str = "data/ledger.jsonl",
    output_path: str = "output/dashboard_data.json",
) -> None:
    """Export dashboard data to JSON file.

    Args:
        ledger_path: Path to the JSONL ledger.
        output_path: Path for the output JSON file.
    """
    data = build_dashboard_data(ledger_path)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(data, f, indent=2, default=str)

    logger.info("Dashboard data exported to %s", output_path)


def main() -> None:
    """CLI entry point."""
    import sys
    ledger = sys.argv[1] if len(sys.argv) > 1 else "data/ledger.jsonl"
    output = sys.argv[2] if len(sys.argv) > 2 else "output/dashboard_data.json"
    export_dashboard(ledger, output)
    print(f"Dashboard data exported to {output}")


if __name__ == "__main__":
    main()
