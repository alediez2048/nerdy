"""Tests for dashboard data export script (P5-01).

Validates that the export script reads the JSONL ledger and produces
a dashboard_data.json file with all 8 panel data sections.
"""

from __future__ import annotations

import json
from pathlib import Path

from iterate.ledger import log_event
from output.export_dashboard import (
    _build_ad_library,
    build_dashboard_data,
    export_dashboard,
    merge_ledger_events,
)


def _seed_ledger(ledger_path: str) -> None:
    """Populate a ledger with representative events for all panels."""
    # Brief expansion
    log_event(ledger_path, {
        "event_type": "BriefExpanded", "ad_id": "ad_001", "brief_id": "b001",
        "cycle_number": 0, "action": "brief-expansion", "tokens_consumed": 200,
        "model_used": "gemini-2.0-flash", "seed": "42",
        "inputs": {"audience": "parents", "campaign_goal": "awareness"},
        "outputs": {"expanded": True},
    })
    # Ad generated
    log_event(ledger_path, {
        "event_type": "AdGenerated", "ad_id": "ad_001", "brief_id": "b001",
        "cycle_number": 1, "action": "generation", "tokens_consumed": 1000,
        "model_used": "gemini-2.0-flash", "seed": "42",
        "inputs": {"hook_type": "question"},
        "outputs": {"headline": "Boost SAT Scores", "primary_text": "Expert tutoring."},
    })
    # Ad evaluated (cycle 1)
    log_event(ledger_path, {
        "event_type": "AdEvaluated", "ad_id": "ad_001", "brief_id": "b001",
        "cycle_number": 1, "action": "evaluation", "tokens_consumed": 500,
        "model_used": "gemini-2.0-flash", "seed": "42",
        "inputs": {},
        "outputs": {
            "aggregate_score": 6.2,
            "scores": {"clarity": 7, "value_proposition": 6, "cta": 5, "brand_voice": 6, "emotional_resonance": 7},
            "rationale": {"clarity": "Clear message", "value_proposition": "Needs work"},
        },
    })
    # Ad regenerated
    log_event(ledger_path, {
        "event_type": "AdRegenerated", "ad_id": "ad_001", "brief_id": "b001",
        "cycle_number": 2, "action": "regeneration-attempt-1", "tokens_consumed": 800,
        "model_used": "gemini-2.0-flash", "seed": "43",
        "inputs": {"weakest_dimension": "cta"},
        "outputs": {"headline": "Boost SAT Scores Now"},
    })
    # Ad evaluated (cycle 2 — improved)
    log_event(ledger_path, {
        "event_type": "AdEvaluated", "ad_id": "ad_001", "brief_id": "b001",
        "cycle_number": 2, "action": "evaluation", "tokens_consumed": 500,
        "model_used": "gemini-2.0-flash", "seed": "43",
        "inputs": {},
        "outputs": {
            "aggregate_score": 7.6,
            "scores": {"clarity": 8, "value_proposition": 7, "cta": 7, "brand_voice": 8, "emotional_resonance": 8},
            "rationale": {"clarity": "Very clear", "cta": "Strong CTA now"},
        },
    })
    # Ad published
    log_event(ledger_path, {
        "event_type": "AdPublished", "ad_id": "ad_001", "brief_id": "b001",
        "cycle_number": 2, "action": "publish", "tokens_consumed": 0,
        "model_used": "none", "seed": "0",
        "inputs": {"aggregate_score": 7.6},
        "outputs": {},
    })
    # Second ad — discarded
    log_event(ledger_path, {
        "event_type": "AdGenerated", "ad_id": "ad_002", "brief_id": "b001",
        "cycle_number": 1, "action": "generation", "tokens_consumed": 1000,
        "model_used": "gemini-2.0-flash", "seed": "44",
        "inputs": {"hook_type": "statistic"},
        "outputs": {"headline": "90% of students improve"},
    })
    log_event(ledger_path, {
        "event_type": "AdEvaluated", "ad_id": "ad_002", "brief_id": "b001",
        "cycle_number": 1, "action": "evaluation", "tokens_consumed": 500,
        "model_used": "gemini-2.0-flash", "seed": "44",
        "inputs": {},
        "outputs": {
            "aggregate_score": 5.0,
            "scores": {"clarity": 5, "value_proposition": 5, "cta": 4, "brand_voice": 5, "emotional_resonance": 6},
        },
    })
    log_event(ledger_path, {
        "event_type": "AdDiscarded", "ad_id": "ad_002", "brief_id": "b001",
        "cycle_number": 1, "action": "discard", "tokens_consumed": 0,
        "model_used": "none", "seed": "0",
        "inputs": {},
        "outputs": {"reason": "below threshold"},
    })
    # Batch completed
    log_event(ledger_path, {
        "event_type": "BatchCompleted", "ad_id": "batch_1", "brief_id": "batch_1",
        "cycle_number": 0, "action": "batch-complete", "tokens_consumed": 0,
        "model_used": "none", "seed": "0",
        "inputs": {"batch_num": 1},
        "outputs": {
            "generated": 2, "published": 1, "discarded": 1, "regenerated": 1,
            "batch_avg_score": 6.3, "batch_num": 1,
        },
    })


# --- Tests ---


def test_export_produces_valid_json(tmp_path: Path) -> None:
    """Export produces valid JSON with all 8 panel keys."""
    ledger_path = str(tmp_path / "ledger.jsonl")
    output_path = str(tmp_path / "dashboard_data.json")
    _seed_ledger(ledger_path)

    export_dashboard(ledger_path, output_path)

    with open(output_path) as f:
        data = json.load(f)

    assert "generated_at" in data
    assert "pipeline_summary" in data
    assert "iteration_cycles" in data
    assert "quality_trends" in data
    assert "dimension_deep_dive" in data
    assert "ad_library" in data
    assert "token_economics" in data
    assert "system_health" in data
    assert "competitive_intel" in data


def test_pipeline_summary_counts(tmp_path: Path) -> None:
    """Pipeline summary has correct generated/published/discarded counts."""
    ledger_path = str(tmp_path / "ledger.jsonl")
    _seed_ledger(ledger_path)

    data = build_dashboard_data(ledger_path)
    summary = data["pipeline_summary"]

    assert summary["total_ads_generated"] == 2
    assert summary["total_ads_published"] == 1
    assert summary["total_ads_discarded"] == 1
    assert 0 < summary["publish_rate"] <= 1.0
    assert summary["total_batches"] == 1
    assert summary["total_tokens"] > 0
    assert summary["videos_in_library"] == 0


def test_iteration_cycles_before_after(tmp_path: Path) -> None:
    """Iteration cycles reconstruct before/after from evaluation events."""
    ledger_path = str(tmp_path / "ledger.jsonl")
    _seed_ledger(ledger_path)

    data = build_dashboard_data(ledger_path)
    cycles = data["iteration_cycles"]

    assert isinstance(cycles, list)
    assert len(cycles) >= 1

    # ad_001 had cycle 1 (6.2) -> cycle 2 (7.6)
    ad1_cycles = [c for c in cycles if c["ad_id"] == "ad_001"]
    assert len(ad1_cycles) >= 1
    c = ad1_cycles[0]
    assert c["score_before"] < c["score_after"]


def test_ad_library_includes_all_ads(tmp_path: Path) -> None:
    """Ad library includes all ads with required fields."""
    ledger_path = str(tmp_path / "ledger.jsonl")
    _seed_ledger(ledger_path)

    data = build_dashboard_data(ledger_path)
    library = data["ad_library"]

    assert isinstance(library, list)
    ad_ids = {ad["ad_id"] for ad in library}
    assert "ad_001" in ad_ids
    assert "ad_002" in ad_ids

    for ad in library:
        assert "ad_id" in ad
        assert "aggregate_score" in ad
        assert "status" in ad
        assert "scores" in ad


def test_token_economics_populated(tmp_path: Path) -> None:
    """Token economics section has stage and model breakdowns."""
    ledger_path = str(tmp_path / "ledger.jsonl")
    _seed_ledger(ledger_path)

    data = build_dashboard_data(ledger_path)
    econ = data["token_economics"]

    assert "by_stage" in econ
    assert "by_model" in econ
    assert "cost_per_published" in econ
    assert isinstance(econ["by_stage"], dict)
    assert len(econ["by_stage"]) > 0


def test_empty_ledger_graceful(tmp_path: Path) -> None:
    """Empty ledger produces valid data without crashing."""
    ledger_path = str(tmp_path / "empty.jsonl")
    Path(ledger_path).touch()

    data = build_dashboard_data(ledger_path)

    assert data["pipeline_summary"]["total_ads_generated"] == 0
    assert data["pipeline_summary"]["total_ads_published"] == 0
    assert data["pipeline_summary"]["videos_in_library"] == 0
    assert data["iteration_cycles"] == []
    assert data["ad_library"] == []


def test_ad_library_maps_video_selected_to_video_url(tmp_path: Path) -> None:
    ledger_path = str(tmp_path / "ledger.jsonl")
    video_path = tmp_path / "output" / "videos" / "session_test" / "ad_001.mp4"
    video_path.parent.mkdir(parents=True, exist_ok=True)
    video_path.write_bytes(b"video")

    log_event(ledger_path, {
        "event_type": "AdGenerated", "ad_id": "ad_001", "brief_id": "b001",
        "cycle_number": 0, "action": "generation", "tokens_consumed": 10,
        "model_used": "gemini-2.0-flash", "seed": "42",
        "outputs": {"headline": "Boost SAT Scores", "primary_text": "Expert tutoring."},
    })
    log_event(ledger_path, {
        "event_type": "VideoSelected", "ad_id": "ad_001", "brief_id": "b001",
        "cycle_number": 0, "action": "video_selected", "tokens_consumed": 0,
        "model_used": "kling-v2.6-pro", "seed": "42",
        "outputs": {
            "winner_video_path": str(video_path),
            "composite_score": 0.82,
            "attribute_pass_pct": 1.0,
            "coherence_avg": 4.9,
        },
    })

    data = build_dashboard_data(ledger_path)
    assert data["pipeline_summary"]["videos_in_library"] == 1
    ad = data["ad_library"][0]
    assert ad["status"] == "published"
    assert ad["video_url"].endswith("/videos/session_test/ad_001.mp4")
    assert ad["video_scores"]["composite_score"] == 0.82


def test_ad_library_maps_video_blocked_to_discarded(tmp_path: Path) -> None:
    ledger_path = str(tmp_path / "ledger.jsonl")

    log_event(ledger_path, {
        "event_type": "AdGenerated", "ad_id": "ad_002", "brief_id": "b001",
        "cycle_number": 0, "action": "generation", "tokens_consumed": 10,
        "model_used": "gemini-2.0-flash", "seed": "42",
        "outputs": {"headline": "Boost SAT Scores", "primary_text": "Expert tutoring."},
    })
    log_event(ledger_path, {
        "event_type": "VideoBlocked", "ad_id": "ad_002", "brief_id": "b001",
        "cycle_number": 0, "action": "video_blocked", "tokens_consumed": 0,
        "model_used": "kling-v2.6-pro", "seed": "0",
        "outputs": {"reason": "all_variants_failed_thresholds"},
    })

    data = build_dashboard_data(ledger_path)
    assert data["pipeline_summary"]["videos_in_library"] == 0
    ad = data["ad_library"][0]
    assert ad["status"] == "discarded"
    assert ad["video_url"] is None


def test_quality_trends_batch_scores(tmp_path: Path) -> None:
    """Quality trends includes batch scores."""
    ledger_path = str(tmp_path / "ledger.jsonl")
    _seed_ledger(ledger_path)

    data = build_dashboard_data(ledger_path)
    trends = data["quality_trends"]

    assert "batch_scores" in trends
    assert isinstance(trends["batch_scores"], list)
    assert len(trends["batch_scores"]) >= 1
    assert "avg_score" in trends["batch_scores"][0]


def test_system_health_spc(tmp_path: Path) -> None:
    """System health includes SPC data."""
    ledger_path = str(tmp_path / "ledger.jsonl")
    _seed_ledger(ledger_path)

    data = build_dashboard_data(ledger_path)
    health = data["system_health"]

    assert "spc" in health
    assert "batch_averages" in health["spc"]


# --- Cross-ledger merge and dedup tests ---


def test_merge_ledger_events_sorts_by_timestamp(tmp_path: Path) -> None:
    """Merged events from multiple ledgers are sorted chronologically."""
    ledger_a = str(tmp_path / "a.jsonl")
    ledger_b = str(tmp_path / "b.jsonl")

    # Write events with timestamps out of file order
    log_event(ledger_a, {
        "event_type": "AdGenerated", "ad_id": "ad_late", "brief_id": "b1",
        "cycle_number": 0, "action": "gen", "tokens_consumed": 10,
        "model_used": "flash", "seed": "1",
        "outputs": {"headline": "Late"},
    })
    log_event(ledger_b, {
        "event_type": "AdGenerated", "ad_id": "ad_early", "brief_id": "b1",
        "cycle_number": 0, "action": "gen", "tokens_consumed": 10,
        "model_used": "flash", "seed": "2",
        "outputs": {"headline": "Early"},
    })

    merged = merge_ledger_events([ledger_a, ledger_b])
    timestamps = [e.get("timestamp", "") for e in merged]
    assert timestamps == sorted(timestamps), "Merged events should be sorted by timestamp"


def test_overlapping_ledgers_dedup_to_single_instance(tmp_path: Path) -> None:
    """Same ad_id in global + session ledger produces one library entry, not two."""
    global_ledger = str(tmp_path / "global.jsonl")
    session_ledger = str(tmp_path / "sessions" / "sess_01" / "ledger.jsonl")
    Path(session_ledger).parent.mkdir(parents=True)

    # Same ad in both ledgers
    for ledger in [global_ledger, session_ledger]:
        log_event(ledger, {
            "event_type": "AdGenerated", "ad_id": "ad_overlap", "brief_id": "b1",
            "cycle_number": 0, "action": "gen", "tokens_consumed": 10,
            "model_used": "flash", "seed": "1",
            "outputs": {"headline": "Test Ad", "primary_text": "Overlap test."},
        })
    # Publish event only in session ledger
    log_event(session_ledger, {
        "event_type": "AdPublished", "ad_id": "ad_overlap", "brief_id": "b1",
        "cycle_number": 0, "action": "publish", "tokens_consumed": 0,
        "model_used": "none", "seed": "0",
        "outputs": {},
    })

    merged = merge_ledger_events([global_ledger, session_ledger])
    library = _build_ad_library(merged)

    overlap_ads = [a for a in library if a["ad_id"] == "ad_overlap"]
    assert len(overlap_ads) == 1, f"Expected 1 entry, got {len(overlap_ads)}"
    assert overlap_ads[0]["status"] == "published"


def test_published_status_wins_over_discarded(tmp_path: Path) -> None:
    """An ad published in one run and discarded in another shows as published."""
    ledger_path = str(tmp_path / "ledger.jsonl")

    log_event(ledger_path, {
        "event_type": "AdGenerated", "ad_id": "ad_mixed", "brief_id": "b1",
        "cycle_number": 0, "action": "gen", "tokens_consumed": 10,
        "model_used": "flash", "seed": "1",
        "outputs": {"headline": "Mixed Status", "primary_text": "Test."},
    })
    log_event(ledger_path, {
        "event_type": "AdDiscarded", "ad_id": "ad_mixed", "brief_id": "b1",
        "cycle_number": 0, "action": "discard", "tokens_consumed": 0,
        "model_used": "none", "seed": "0",
        "outputs": {"reason": "below threshold"},
    })
    log_event(ledger_path, {
        "event_type": "AdPublished", "ad_id": "ad_mixed", "brief_id": "b1",
        "cycle_number": 1, "action": "publish", "tokens_consumed": 0,
        "model_used": "none", "seed": "0",
        "outputs": {},
    })

    data = build_dashboard_data(ledger_path)
    ad = [a for a in data["ad_library"] if a["ad_id"] == "ad_mixed"]
    assert len(ad) == 1
    assert ad[0]["status"] == "published"


def test_video_status_resolved_across_ledgers(tmp_path: Path) -> None:
    """VideoSelected in session ledger marks ad as published even when
    AdGenerated is only in the global ledger."""
    global_ledger = str(tmp_path / "global.jsonl")
    session_ledger = str(tmp_path / "sessions" / "sess_v" / "ledger.jsonl")
    Path(session_ledger).parent.mkdir(parents=True)

    log_event(global_ledger, {
        "event_type": "AdGenerated", "ad_id": "ad_vid", "brief_id": "b1",
        "cycle_number": 0, "action": "gen", "tokens_consumed": 10,
        "model_used": "flash", "seed": "1",
        "outputs": {"headline": "Video Ad", "primary_text": "Video test."},
    })
    log_event(session_ledger, {
        "event_type": "AdGenerated", "ad_id": "ad_vid", "brief_id": "b1",
        "cycle_number": 0, "action": "gen", "tokens_consumed": 10,
        "model_used": "flash", "seed": "1",
        "outputs": {"headline": "Video Ad", "primary_text": "Video test."},
    })
    log_event(session_ledger, {
        "event_type": "VideoSelected", "ad_id": "ad_vid", "brief_id": "b1",
        "cycle_number": 0, "action": "video_selected", "tokens_consumed": 0,
        "model_used": "fal-ai/veo3", "seed": "1",
        "outputs": {
            "winner_video_path": "/output/videos/session_v/ad_vid.mp4",
            "composite_score": 0.75,
            "attribute_pass_pct": 0.8,
            "coherence_avg": 5.0,
        },
    })

    merged = merge_ledger_events([global_ledger, session_ledger])
    library = _build_ad_library(merged)

    vid_ads = [a for a in library if a["ad_id"] == "ad_vid"]
    assert len(vid_ads) == 1
    assert vid_ads[0]["status"] == "published"
    assert vid_ads[0]["video_scores"]["composite_score"] == 0.75
