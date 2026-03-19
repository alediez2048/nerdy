# PC-02: Video orchestrator tests (TDD)
"""Tests for video variant generation, selection, checkpoint-resume, and pipeline."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture()
def tmp_output(tmp_path):
    return str(tmp_path)


@pytest.fixture()
def tmp_ledger(tmp_path):
    ledger = tmp_path / "ledger.jsonl"
    return str(ledger)


def _make_spec(**overrides):
    from generate_video.video_spec import VideoSpec
    defaults = dict(
        scene="Test scene", visual_style="UGC realistic",
        camera_movement="handheld", subject_action="Student studying",
        setting="Home", lighting_mood="Warm", audio_mode="silent",
        audio_detail="", color_palette="#17e2ea", negative_prompt="blur, logos",
        duration=10, aspect_ratio="9:16", text_overlay_sequence=["Hook", "VP", "CTA"],
        persona="auto", campaign_goal="conversion",
    )
    defaults.update(overrides)
    return VideoSpec(**defaults)


# --- generate_video_variants ---


@patch("generate_video.orchestrator.KlingClient")
def test_generate_variants_produces_two(mock_client_cls, tmp_output, tmp_ledger):
    mock_client = MagicMock()
    mock_client.generate_video.side_effect = lambda **kw: _write_fake_video(kw["output_path"])
    mock_client_cls.return_value = mock_client

    from generate_video.orchestrator import generate_video_variants
    spec = _make_spec()
    variants = generate_video_variants(spec, "ad_001", 42, tmp_output, tmp_ledger, mock_client)

    assert len(variants) == 2
    assert variants[0].variant_type == "anchor"
    assert variants[1].variant_type == "alternative"


@patch("generate_video.orchestrator.KlingClient")
def test_generate_variants_handles_api_failure(mock_client_cls, tmp_output, tmp_ledger):
    mock_client = MagicMock()
    call_count = [0]

    def side_effect(**kw):
        call_count[0] += 1
        if call_count[0] == 1:
            return _write_fake_video(kw["output_path"])
        raise Exception("Kling API error")

    mock_client.generate_video.side_effect = side_effect
    mock_client_cls.return_value = mock_client

    from generate_video.orchestrator import generate_video_variants
    spec = _make_spec()
    variants = generate_video_variants(spec, "ad_002", 42, tmp_output, tmp_ledger, mock_client)

    assert len(variants) == 1
    assert variants[0].variant_type == "anchor"


@patch("generate_video.orchestrator.KlingClient")
def test_generate_variants_logs_events(mock_client_cls, tmp_output, tmp_ledger):
    mock_client = MagicMock()
    mock_client.generate_video.side_effect = lambda **kw: _write_fake_video(kw["output_path"])
    mock_client_cls.return_value = mock_client

    from generate_video.orchestrator import generate_video_variants
    spec = _make_spec()
    generate_video_variants(spec, "ad_003", 42, tmp_output, tmp_ledger, mock_client)

    from iterate.ledger import read_events
    events = read_events(tmp_ledger)
    video_gen = [e for e in events if e["event_type"] == "VideoGenerated"]
    assert len(video_gen) == 2


@patch("generate_video.orchestrator.KlingClient")
def test_video_generated_only_logged_when_file_exists(mock_client_cls, tmp_output, tmp_ledger):
    """VideoGenerated must NOT be logged when file doesn't exist on disk."""
    mock_client = MagicMock()
    mock_client.generate_video.side_effect = Exception("Kling error")
    mock_client_cls.return_value = mock_client

    from generate_video.orchestrator import generate_video_variants
    spec = _make_spec()
    variants = generate_video_variants(spec, "ad_004", 42, tmp_output, tmp_ledger, mock_client)

    assert len(variants) == 0

    from iterate.ledger import read_events
    events = read_events(tmp_ledger)
    assert all(e["event_type"] != "VideoGenerated" for e in events)
    failed = [e for e in events if e["event_type"] == "VideoGenerationFailed"]
    assert len(failed) == 2


# --- select_best_video ---


def test_select_best_picks_higher_score():
    from generate_video.orchestrator import VideoVariant, select_best_video
    from evaluate.video_evaluator import VideoEvalResult, VideoCoherenceResult

    v1 = VideoVariant("ad_1", "anchor", "/v1.mp4", 10, "silent", "9:16", "p1", 42, 130, "kling-v2.6-pro")
    v2 = VideoVariant("ad_1", "alternative", "/v2.mp4", 10, "silent", "9:16", "p2", 3042, 130, "kling-v2.6-pro")

    eval1 = VideoEvalResult("ad_1", "anchor", {"a": True, "b": True, "c": True, "d": True, "e": True}, 1.0, True)
    eval2 = VideoEvalResult("ad_1", "alternative", {"a": True, "b": True, "c": True, "d": False, "e": True}, 0.8, True)

    coh1 = VideoCoherenceResult("ad_1", "anchor", {"m": 5.0, "a": 5.0, "e": 5.0, "n": 5.0}, 5.0, True)
    coh2 = VideoCoherenceResult("ad_1", "alternative", {"m": 7.0, "a": 7.0, "e": 7.0, "n": 7.0}, 7.0, True)

    winner = select_best_video(
        [v1, v2],
        {"anchor": eval1, "alternative": eval2},
        {"anchor": coh1, "alternative": coh2},
    )

    assert winner is not None
    # v2 has higher composite: 0.4*0.8 + 0.6*0.7 = 0.74 vs v1: 0.4*1.0 + 0.6*0.5 = 0.70
    assert winner.variant_type == "alternative"


def test_select_best_returns_none_when_all_fail():
    from generate_video.orchestrator import VideoVariant, select_best_video
    from evaluate.video_evaluator import VideoEvalResult, VideoCoherenceResult

    v1 = VideoVariant("ad_1", "anchor", "/v1.mp4", 10, "silent", "9:16", "p", 42, 130, "kling-v2.6-pro")

    eval1 = VideoEvalResult("ad_1", "anchor", {"a": False, "b": False, "c": True, "d": False, "e": True}, 0.4, False)
    coh1 = VideoCoherenceResult("ad_1", "anchor", {"m": 3.0, "a": 2.0, "e": 3.0, "n": 2.0}, 2.5, False)

    winner = select_best_video([v1], {"anchor": eval1}, {"anchor": coh1})

    assert winner is None


# --- checkpoint-resume ---


def test_should_skip_video_ad_returns_true_for_processed(tmp_ledger):
    from iterate.ledger import log_event
    log_event(tmp_ledger, {
        "event_type": "VideoSelected", "ad_id": "ad_010", "brief_id": "b",
        "cycle_number": 0, "action": "selected", "tokens_consumed": 0,
        "model_used": "kling-v2.6-pro", "seed": "42",
    })

    from generate_video.orchestrator import should_skip_video_ad
    assert should_skip_video_ad("ad_010", tmp_ledger) is True


def test_should_skip_video_ad_returns_false_for_new(tmp_ledger):
    from generate_video.orchestrator import should_skip_video_ad
    assert should_skip_video_ad("ad_new", tmp_ledger) is False


def test_should_skip_blocked_ad(tmp_ledger):
    from iterate.ledger import log_event
    log_event(tmp_ledger, {
        "event_type": "VideoBlocked", "ad_id": "ad_020", "brief_id": "b",
        "cycle_number": 0, "action": "blocked", "tokens_consumed": 0,
        "model_used": "kling-v2.6-pro", "seed": "42",
    })

    from generate_video.orchestrator import should_skip_video_ad
    assert should_skip_video_ad("ad_020", tmp_ledger) is True


# --- helpers ---


def _write_fake_video(path: str) -> str:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_bytes(b"\x00" * 512)
    return path
