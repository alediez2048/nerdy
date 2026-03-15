"""Tests for video cost tracking (P3-12).

Validates per-video cost calculation, audio vs silent breakdown,
regen cost separation, and unified cross-format aggregation.
"""

from __future__ import annotations

from pathlib import Path

from iterate.video_cost import (
    VEO_COST_PER_SECOND,
    VideoCostEntry,
    VideoCostSummary,
    get_video_cost_summary,
    get_video_costs_by_ad,
    track_video_cost,
)
from iterate.ledger import log_event


# --- Cost Calculation ---


def test_video_cost_calculation() -> None:
    """Cost = duration * rate ($0.15/sec)."""
    entry = track_video_cost(
        ad_id="ad_001",
        variant_id="anchor",
        generation_metadata={"duration": 6, "audio_mode": "music"},
    )
    assert isinstance(entry, VideoCostEntry)
    expected = 6 * VEO_COST_PER_SECOND
    assert abs(entry.cost_usd - expected) < 0.01


def test_audio_vs_silent_cost() -> None:
    """Silent mode should be flagged (cost differential tracked)."""
    entry_audio = track_video_cost(
        "ad_001", "anchor", {"duration": 6, "audio_mode": "music"},
    )
    entry_silent = track_video_cost(
        "ad_002", "anchor", {"duration": 6, "audio_mode": "silent"},
    )
    assert entry_audio.audio_mode == "music"
    assert entry_silent.audio_mode == "silent"


def test_regen_tracked_separately() -> None:
    """Regen costs have is_regen=True."""
    entry = track_video_cost(
        "ad_001", "regen_1", {"duration": 6, "audio_mode": "music", "is_regen": True},
    )
    assert entry.is_regen is True


# --- Per-Ad Costs ---


def test_get_video_costs_by_ad(tmp_path: Path) -> None:
    """get_video_costs_by_ad returns all video costs for one ad."""
    ledger_path = str(tmp_path / "ledger.jsonl")

    for i, (variant, is_regen) in enumerate([("anchor", False), ("alternative", False), ("regen_1", True)]):
        log_event(ledger_path, {
            "event_type": "VideoGenerated",
            "ad_id": "ad_001",
            "brief_id": "b001",
            "cycle_number": 1,
            "action": "video-regen" if is_regen else "video-generation",
            "inputs": {"variant_id": variant},
            "outputs": {"duration": 6, "audio_mode": "music", "is_regen": is_regen},
            "scores": {},
            "tokens_consumed": 0,
            "model_used": "veo-3.1-fast",
            "seed": str(i),
        })

    costs = get_video_costs_by_ad("ad_001", ledger_path)
    assert len(costs) == 3
    regen_costs = [c for c in costs if c.is_regen]
    assert len(regen_costs) == 1


# --- Summary ---


def test_video_cost_summary(tmp_path: Path) -> None:
    """get_video_cost_summary computes totals and averages."""
    ledger_path = str(tmp_path / "ledger.jsonl")

    for ad_idx in range(3):
        for variant in ["anchor", "alternative"]:
            log_event(ledger_path, {
                "event_type": "VideoGenerated",
                "ad_id": f"ad_{ad_idx:03d}",
                "brief_id": "b001",
                "cycle_number": 1,
                "action": "video-generation",
                "inputs": {"variant_id": variant},
                "outputs": {"duration": 6, "audio_mode": "music", "is_regen": False},
                "scores": {},
                "tokens_consumed": 0,
                "model_used": "veo-3.1-fast",
                "seed": "42",
            })

    summary = get_video_cost_summary(ledger_path)
    assert isinstance(summary, VideoCostSummary)
    assert summary.total_videos == 6
    assert summary.total_cost_usd > 0
    assert abs(summary.avg_cost_per_ad - summary.total_cost_usd / 3) < 0.01


def test_video_blocked_ad_zero_cost(tmp_path: Path) -> None:
    """Video-blocked ad has no video cost entries."""
    ledger_path = str(tmp_path / "ledger.jsonl")
    # Only a VideoBlocked event, no VideoGenerated
    log_event(ledger_path, {
        "event_type": "VideoBlocked",
        "ad_id": "ad_blocked",
        "brief_id": "b001",
        "cycle_number": 1,
        "action": "video-degradation",
        "inputs": {},
        "outputs": {"fallback": "image-only"},
        "scores": {},
        "tokens_consumed": 0,
        "model_used": "",
        "seed": "",
    })

    costs = get_video_costs_by_ad("ad_blocked", ledger_path)
    assert len(costs) == 0


def test_regen_overhead_percentage(tmp_path: Path) -> None:
    """Summary includes regen overhead percentage."""
    ledger_path = str(tmp_path / "ledger.jsonl")

    # 2 initial + 1 regen
    for variant, is_regen in [("anchor", False), ("alt", False), ("regen", True)]:
        log_event(ledger_path, {
            "event_type": "VideoGenerated",
            "ad_id": "ad_001",
            "brief_id": "b001",
            "cycle_number": 1,
            "action": "video-regen" if is_regen else "video-generation",
            "inputs": {"variant_id": variant},
            "outputs": {"duration": 6, "audio_mode": "music", "is_regen": is_regen},
            "scores": {},
            "tokens_consumed": 0,
            "model_used": "veo-3.1-fast",
            "seed": "42",
        })

    summary = get_video_cost_summary(ledger_path)
    # 1/3 = 33.3% regen overhead
    assert summary.regen_overhead_pct > 0
