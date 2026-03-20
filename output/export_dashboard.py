"""Dashboard data export — reads JSONL ledger, produces dashboard_data.json (P5-01).

Aggregates all pipeline data into a single JSON file consumed by the
8-panel HTML dashboard. Calls existing module functions — no duplicated logic.
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from iterate.ledger import read_events

logger = logging.getLogger(__name__)

DIMENSIONS = ("clarity", "value_proposition", "cta", "brand_voice", "emotional_resonance")
_TIME_WINDOWS: dict[str, timedelta] = {
    "day": timedelta(days=1),
    "month": timedelta(days=30),
    "year": timedelta(days=365),
}


def _session_id_from_ledger_path(ledger_path: str) -> str | None:
    path = Path(ledger_path)
    if path.parent.name == "sessions":
        return path.stem
    if path.parent.parent.name == "sessions":
        return path.parent.name
    return None


def _dedupe_events_by_checkpoint(events: list[dict]) -> list[dict]:
    """Deduplicate merged ledger events by checkpoint_id when available."""
    deduped: list[dict] = []
    by_checkpoint: dict[str, dict] = {}
    for event in events:
        checkpoint_id = event.get("checkpoint_id")
        if checkpoint_id:
            existing = by_checkpoint.get(checkpoint_id)
            if existing is not None:
                if not existing.get("source_session_id") and event.get("source_session_id"):
                    existing["source_session_id"] = event.get("source_session_id")
                    existing["source_label"] = event.get("source_label")
                continue
            by_checkpoint[checkpoint_id] = event
        deduped.append(event)
    return deduped


def _parse_event_timestamp(value: object) -> datetime | None:
    """Parse ISO timestamps from ledger events."""
    if not isinstance(value, str) or not value:
        return None
    try:
        normalized = value.replace("Z", "+00:00")
        dt = datetime.fromisoformat(normalized)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except ValueError:
        return None


def filter_events_by_timeframe(
    events: list[dict],
    timeframe: str = "all",
    now: datetime | None = None,
) -> list[dict]:
    """Filter ledger events to a relative time window."""
    if timeframe == "all":
        return events

    delta = _TIME_WINDOWS.get(timeframe)
    if delta is None:
        return events

    reference = now or datetime.now(timezone.utc)
    cutoff = reference - delta
    filtered: list[dict] = []
    for event in events:
        ts = _parse_event_timestamp(event.get("timestamp"))
        if ts is not None and ts >= cutoff:
            filtered.append(event)
    return filtered


def merge_ledger_events(
    ledger_paths: list[str],
    session_labels: dict[str, str] | None = None,
) -> list[dict]:
    """Merge events from multiple ledgers and retain source session metadata."""
    merged_events: list[dict] = []
    for ledger_path in ledger_paths:
        session_id = _session_id_from_ledger_path(ledger_path)
        source_label = (
            session_labels.get(session_id, session_id)
            if session_id and session_labels
            else (session_id or "Global ledger")
        )
        for event in read_events(ledger_path):
            event_copy = dict(event)
            event_copy["source_session_id"] = session_id
            event_copy["source_label"] = source_label
            merged_events.append(event_copy)
    return _dedupe_events_by_checkpoint(merged_events)


def _build_pipeline_summary(
    events: list[dict],
    ledger_path: str | None = None,
    session_id: str | None = None,
) -> dict:
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

    # Compute cost: session-scoped uses manifest + ledger via compute_session_cost_usd
    total_cost_usd = 0.0
    cost_source = "ledger"
    try:
        from evaluate.cost_reporter import compute_event_cost, compute_session_cost_usd

        if session_id and ledger_path:
            scr = compute_session_cost_usd(session_id, ledger_path)
            total_cost_usd = round(scr.total_usd, 4)
            cost_source = scr.source
        else:
            for e in events:
                total_cost_usd += compute_event_cost(e)
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
        "cost_source": cost_source,
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
    """Panel 5: All created ad instances with copy, scores, and status.

    Unlike the export-oriented ad library, the global dashboard should show
    every created ad instance, not just the latest state per deterministic
    ad_id. This matters because the pipeline reuses ad_ids across repeated
    runs of the same brief/seed combination, so collapsing by ad_id hides a
    large share of creation history.
    """
    # Find all creation events — filter out test/reference/calibration ads
    _SKIP_PREFIXES = ("batch_", "test_", "ref_", "adv_", "golden_")
    creation_events_by_ad: dict[str, list[int]] = {}
    for idx, e in enumerate(events):
        aid = e.get("ad_id")
        etype = e.get("event_type")
        if (
            aid
            and etype in {"AdGenerated", "AdRegenerated"}
            and not any(aid.startswith(p) for p in _SKIP_PREFIXES)
        ):
            creation_events_by_ad.setdefault(aid, []).append(idx)

    library: list[dict] = []
    for ad_id, indices in creation_events_by_ad.items():
        for occurrence_idx, start_idx in enumerate(indices):
            end_idx = indices[occurrence_idx + 1] if occurrence_idx + 1 < len(indices) else len(events)
            creation_event = events[start_idx]
            instance_events = [
                event
                for event in events[start_idx:end_idx]
                if event.get("ad_id") == ad_id
            ]

            evals = [e for e in instance_events if e.get("event_type") == "AdEvaluated"]
            latest_eval = evals[-1] if evals else None
            copy_data = creation_event.get("outputs", {})
            raw_scores = latest_eval.get("outputs", {}).get("scores", {}) if latest_eval else {}

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
            cycle_count = max(
                (e.get("cycle_number", 0) for e in instance_events),
                default=creation_event.get("cycle_number", 0),
            )

            status = "in_progress"
            if any(e.get("event_type") == "VideoSelected" for e in instance_events):
                status = "published"
            elif any(e.get("event_type") == "VideoBlocked" for e in instance_events):
                status = "discarded"
            elif any(e.get("event_type") == "AdPublished" for e in instance_events):
                status = "published"
            elif any(e.get("event_type") == "AdDiscarded" for e in instance_events):
                status = "discarded"

            pub_events = [e for e in instance_events if e.get("event_type") == "AdPublished"]
            pub_event = pub_events[-1] if pub_events else None
            image_path = None
            image_url = None
            video_path = None
            video_url = None
            video_scores = None
            if pub_event:
                winning = pub_event.get("outputs", {}).get("winning_image")
                if winning:
                    image_path = winning
                    filename = Path(winning).name
                    image_url = f"/images/{filename}"

            video_events = [e for e in instance_events if e.get("event_type") == "VideoSelected"]
            video_event = video_events[-1] if video_events else None
            if video_event:
                winning_video = video_event.get("outputs", {}).get("winner_video_path")
                if winning_video:
                    video_path = winning_video
                    parts = Path(winning_video).parts
                    if "output" in parts and "videos" in parts:
                        try:
                            output_idx = parts.index("output")
                            if parts[output_idx + 1] == "videos":
                                rel_parts = parts[output_idx + 2:]
                                video_url = f"/videos/{'/'.join(rel_parts)}"
                            else:
                                video_url = f"/videos/{Path(winning_video).name}"
                        except Exception:
                            video_url = f"/videos/{Path(winning_video).name}"
                    else:
                        video_url = f"/videos/{Path(winning_video).name}"
                video_scores = {
                    "composite_score": float(video_event.get("outputs", {}).get("composite_score", 0.0)),
                    "attribute_pass_pct": float(video_event.get("outputs", {}).get("attribute_pass_pct", 0.0)),
                    "coherence_avg": float(video_event.get("outputs", {}).get("coherence_avg", 0.0)),
                }

            # Only use the disk fallback when this ad_id appears once in the
            # ledger history. Reused deterministic ad_ids cannot be reliably
            # mapped back to a single historical image file.
            if not image_url and len(indices) == 1:
                matches = sorted(
                    Path("output/images").glob(f"{ad_id}_*.png"),
                    key=lambda path: path.stat().st_mtime,
                    reverse=True,
                )
                if matches:
                    image_path = str(matches[0])
                    image_url = f"/images/{matches[0].name}"

            has_copy = copy_data.get("primary_text") or copy_data.get("headline")
            has_scores = bool(scores)
            if not has_copy and not has_scores:
                continue

            library.append({
                "instance_id": creation_event.get("checkpoint_id", f"{ad_id}:{occurrence_idx + 1}"),
                "created_at": creation_event.get("timestamp", ""),
                "ad_id": ad_id,
                "brief_id": creation_event.get("brief_id", ""),
                "session_id": creation_event.get("source_session_id"),
                "session_label": creation_event.get("source_label", "Global ledger"),
                "copy": copy_data,
                "scores": scores,
                "aggregate_score": aggregate,
                "rationale": rationale,
                "status": status,
                "cycle_count": cycle_count,
                "image_path": image_path,
                "image_url": image_url,
                "video_path": video_path,
                "video_url": video_url,
                "video_scores": video_scores,
            })

    library.sort(key=lambda item: item.get("created_at", ""), reverse=True)
    return library


def build_global_ad_library(ledger_paths: list[str]) -> list[dict]:
    """Build ad library across multiple ledgers for the global dashboard."""
    return _build_ad_library(merge_ledger_events(ledger_paths))


def _build_token_economics(ledger_path: str, events: list[dict] | None = None) -> dict:
    """Panel 6: Cost attribution + marginal analysis."""
    if events is None:
        from iterate.token_tracker import get_token_summary

        summary = get_token_summary(ledger_path)

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

    from iterate.token_tracker import get_stage_from_event

    by_stage: dict[str, int] = defaultdict(int)
    by_model: dict[str, int] = defaultdict(int)
    total_tokens = 0
    published = 0
    for event in events:
        tokens = int(event.get("tokens_consumed", 0) or 0)
        total_tokens += tokens
        by_stage[get_stage_from_event(event)] += tokens
        by_model[event.get("model_used", "unknown")] += tokens
        if event.get("event_type") == "AdPublished":
            published += 1

    out: dict = {
        "by_stage": dict(by_stage),
        "by_model": dict(by_model),
        "cost_per_published": round(total_tokens / published, 2) if published > 0 else 0,
        "marginal_analysis": {},
    }
    # USD total — same rules as session Overview (winning variant only for billed video gen)
    try:
        from evaluate.cost_reporter import sum_session_display_cost_usd

        out["ledger_cost_usd"] = round(sum_session_display_cost_usd(events), 4)
    except ImportError:
        out["ledger_cost_usd"] = 0.0
    return out


def _build_system_health(ledger_path: str, events: list[dict] | None = None) -> dict:
    """Panel 7: SPC + confidence + compliance."""
    source_events = events if events is not None else read_events(ledger_path)

    spc_data: dict = {"batch_averages": [], "ucl": None, "lcl": None, "mean": None, "breach_indices": []}
    try:
        from evaluate.spc_monitor import compute_control_limits, is_in_control

        batch_averages: list[float] = []
        for event in source_events:
            if event.get("event_type") != "BatchCompleted":
                continue
            outputs = event.get("outputs", {})
            avg = outputs.get("batch_average", outputs.get("batch_avg_score"))
            if isinstance(avg, (int, float)):
                batch_averages.append(float(avg))

        limits = compute_control_limits(batch_averages)
        breach_indices: list[int] = []
        if limits is not None:
            for idx, avg in enumerate(batch_averages):
                if not is_in_control(avg, limits):
                    breach_indices.append(idx)

        spc_data = {
            "batch_averages": batch_averages,
            "ucl": limits.ucl if limits else None,
            "lcl": limits.lcl if limits else None,
            "mean": limits.mean if limits else None,
            "breach_indices": breach_indices,
        }
    except Exception:
        pass

    confidence: dict = {}
    try:
        counts = {
            "autonomous": 0,
            "flagged": 0,
            "human_required": 0,
            "brand_safety_stop": 0,
        }

        routed_events = [e for e in source_events if e.get("event_type") == "ConfidenceRouted"]
        if routed_events:
            for event in routed_events:
                level = event.get("outputs", {}).get("confidence_level", "")
                if level in counts:
                    counts[level] += 1
        else:
            eval_events = [e for e in source_events if e.get("event_type") == "AdEvaluated"]
            for event in eval_events:
                outputs = event.get("outputs", {})
                scores = outputs.get("scores", {})
                flags = outputs.get("flags", [])
                if any("floor_violation" in str(flag) for flag in flags):
                    counts["brand_safety_stop"] += 1
                    continue

                confidences: list[float] = []
                for dim_data in scores.values():
                    if isinstance(dim_data, dict):
                        conf = dim_data.get("confidence")
                        if isinstance(conf, (int, float)):
                            confidences.append(float(conf))

                if not confidences:
                    counts["autonomous"] += 1
                    continue

                avg_conf = sum(confidences) / len(confidences)
                if avg_conf >= 7:
                    counts["autonomous"] += 1
                elif avg_conf >= 5:
                    counts["flagged"] += 1
                else:
                    counts["human_required"] += 1

        total = sum(counts.values())

        def _pct(value: int) -> float:
            return round(value / total * 100, 1) if total > 0 else 0.0

        confidence = {
            "autonomous_count": counts["autonomous"],
            "flagged_count": counts["flagged"],
            "human_required_count": counts["human_required"],
            "brand_safety_count": counts["brand_safety_stop"],
            "total": total,
            "autonomous_pct": _pct(counts["autonomous"]),
            "flagged_pct": _pct(counts["flagged"]),
            "human_required_pct": _pct(counts["human_required"]),
        }
    except Exception:
        pass

    compliance_pass = sum(1 for e in source_events if e.get("event_type") == "AdPublished")
    compliance_fail = sum(1 for e in source_events if e.get("event_type") == "AdDiscarded")

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


def build_dashboard_data_from_events(
    events: list[dict],
    ledger_path: str,
    session_id: str | None = None,
) -> dict:
    """Build the complete dashboard data structure from preloaded events."""
    ad_library = _build_ad_library(events)
    pipeline = _build_pipeline_summary(events, ledger_path=ledger_path, session_id=session_id)
    # Same notion of "a video" as the Ad Library tab (rows with a playable/output path)
    pipeline["videos_in_library"] = sum(
        1 for item in ad_library if item.get("video_url") or item.get("video_path")
    )
    token_econ = _build_token_economics(ledger_path, events)
    token_econ["total_cost_usd"] = pipeline.get("total_cost_usd", 0.0)
    token_econ["cost_source"] = pipeline.get("cost_source", "ledger")
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "ledger_path": ledger_path,
        "pipeline_summary": pipeline,
        "iteration_cycles": _build_iteration_cycles(events),
        "quality_trends": _build_quality_trends(events),
        "dimension_deep_dive": _build_dimension_deep_dive(events),
        "ad_library": ad_library,
        "token_economics": token_econ,
        "system_health": _build_system_health(ledger_path, events),
        "competitive_intel": _build_competitive_intel(ledger_path),
    }


def build_dashboard_data(ledger_path: str, session_id: str | None = None) -> dict:
    """Build the complete dashboard data structure from a ledger.

    Args:
        ledger_path: Path to the JSONL ledger.
        session_id: When set, total cost uses manifest + ledger (historical sessions).

    Returns:
        Dict with all 8 panel data sections.
    """
    events = read_events(ledger_path)

    return build_dashboard_data_from_events(events, ledger_path, session_id=session_id)


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
