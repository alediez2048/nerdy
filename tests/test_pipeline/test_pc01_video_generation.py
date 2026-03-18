"""PC-01 tests: video spec extraction + video generation wrappers."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from generate.image_generator import (
    VideoVariant,
    generate_video_variants,
)
from generate.visual_spec import (
    VideoSpec,
    build_video_prompt,
    extract_video_spec,
)
from iterate.ledger import read_events_filtered


_EXPANDED_BRIEF = {
    "brief_id": "b_pc01_001",
    "product": "SAT prep tutoring",
    "key_message": "Raise SAT scores with personalized tutoring",
    "persona": "athlete_recruit",
    "creative_brief": "ugc_testimonial",
    "messaging_rules": {
        "dos": ["Use clear outcome language", "Be encouraging"],
        "donts": ["No absolute guarantees"],
    },
}


def test_extract_video_spec_returns_dataclass() -> None:
    """extract_video_spec returns a VideoSpec with required defaults."""
    spec = extract_video_spec(
        expanded_brief=_EXPANDED_BRIEF,
        campaign_goal="conversion",
        audience="parents",
        ad_id="ad_001",
    )
    assert isinstance(spec, VideoSpec)
    assert spec.ad_id == "ad_001"
    assert spec.aspect_ratio == "9:16"
    assert spec.camera_style == "handheld"
    assert spec.duration == 6.0


def test_extract_video_spec_goal_default_pacing() -> None:
    """Campaign goal controls default pacing."""
    conv_spec = extract_video_spec(_EXPANDED_BRIEF, "conversion", "parents", "ad_conv")
    aware_spec = extract_video_spec(_EXPANDED_BRIEF, "awareness", "parents", "ad_aw")
    assert conv_spec.pacing == "fast"
    assert aware_spec.pacing == "medium"


def test_extract_video_spec_persona_and_creative_brief_context() -> None:
    """Persona and creative_brief influence scene/style context."""
    spec = extract_video_spec(
        expanded_brief=_EXPANDED_BRIEF,
        campaign_goal="conversion",
        audience="parents",
        ad_id="ad_persona",
    )
    lowered = f"{spec.scene_action} {spec.style_direction}".lower()
    assert "athlete" in lowered or "sports" in lowered or "campus" in lowered
    assert "ugc" in lowered or "handheld" in lowered or "testimonial" in lowered


def test_build_video_prompt_contains_motion_and_pacing() -> None:
    """Video prompt includes motion cues and pacing metadata."""
    spec = extract_video_spec(_EXPANDED_BRIEF, "conversion", "parents", "ad_prompt")
    prompt = build_video_prompt(spec, variant_type="anchor")
    lowered = prompt.lower()
    assert "pacing" in lowered
    assert "camera" in lowered
    assert "text overlay sequence" in lowered


def test_build_video_prompt_variants_differ() -> None:
    """Anchor and alternative prompts are not identical."""
    spec = extract_video_spec(_EXPANDED_BRIEF, "conversion", "parents", "ad_prompt_var")
    anchor = build_video_prompt(spec, "anchor")
    alternative = build_video_prompt(spec, "alternative")
    assert anchor != alternative


@patch("generate.image_generator._call_video_api")
def test_generate_video_variants_returns_two(mock_call: MagicMock, tmp_path: Path) -> None:
    """generate_video_variants returns anchor + alternative variants."""
    mock_call.side_effect = [
        str(tmp_path / "ad_001_anchor.mp4"),
        str(tmp_path / "ad_001_alternative.mp4"),
    ]
    spec = extract_video_spec(_EXPANDED_BRIEF, "conversion", "parents", "ad_001")
    variants = generate_video_variants(spec, ad_id="ad_001", seed=42, output_dir=str(tmp_path))
    assert len(variants) == 2
    assert all(isinstance(v, VideoVariant) for v in variants)
    assert {v.variant_type for v in variants} == {"anchor", "alternative"}
    assert variants[0].seed == 42
    assert variants[1].seed == 3042


@patch("generate.image_generator._call_video_api")
def test_generate_video_variants_logs_events(mock_call: MagicMock, tmp_path: Path) -> None:
    """Video generation logs VideoGenerated events when ledger path is provided."""
    mock_call.side_effect = [
        str(tmp_path / "ad_ledger_anchor.mp4"),
        str(tmp_path / "ad_ledger_alternative.mp4"),
    ]
    ledger_path = str(tmp_path / "ledger.jsonl")
    spec = extract_video_spec(_EXPANDED_BRIEF, "conversion", "parents", "ad_ledger")
    _ = generate_video_variants(
        spec,
        ad_id="ad_ledger",
        seed=77,
        output_dir=str(tmp_path),
        ledger_path=ledger_path,
    )
    events = read_events_filtered(ledger_path, event_type="VideoGenerated", ad_id="ad_ledger")
    assert len(events) == 2


@patch("generate.image_generator._call_video_api")
def test_generate_video_variants_graceful_failure(mock_call: MagicMock, tmp_path: Path) -> None:
    """Video API failures do not crash generation and still return 2 variants."""
    mock_call.side_effect = RuntimeError("Veo unavailable")
    spec = extract_video_spec(_EXPANDED_BRIEF, "conversion", "parents", "ad_fail")
    variants = generate_video_variants(spec, ad_id="ad_fail", seed=5, output_dir=str(tmp_path))
    assert len(variants) == 2
    assert all(v.video_path.endswith(".mp4") for v in variants)
