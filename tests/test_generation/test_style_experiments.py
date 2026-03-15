"""Tests for image style transfer experiments (P3-04).

Validates style presets, audience mapping, experiment aggregation,
and recommended style retrieval with fallback.
"""

from __future__ import annotations

from pathlib import Path

from generate.style_library import (
    STYLE_PRESETS,
    StyleAudienceMap,
    StylePreset,
    apply_style_to_spec,
    build_style_audience_map,
    get_recommended_style,
    get_styles_for_audience,
)
from generate.style_experiments import (
    StyleExperimentResult,
    aggregate_style_results,
)


# --- Style Presets ---


def test_style_presets_have_required_fields() -> None:
    """All 5 style presets have name, prompt_modifier, target_audiences."""
    assert len(STYLE_PRESETS) == 5
    for name, preset in STYLE_PRESETS.items():
        assert isinstance(preset, StylePreset)
        assert preset.name == name
        assert len(preset.prompt_modifier) > 0
        assert isinstance(preset.target_audiences, list)


def test_get_styles_for_audience_returns_presets() -> None:
    """get_styles_for_audience returns valid StylePreset list."""
    styles = get_styles_for_audience("parents")
    assert len(styles) >= 1
    assert all(isinstance(s, StylePreset) for s in styles)


def test_apply_style_to_spec_modifies_spec() -> None:
    """apply_style_to_spec adds style modifier to visual spec."""
    spec = {"scene_description": "student studying", "color_palette": "warm"}
    style = STYLE_PRESETS["illustrated"]
    modified = apply_style_to_spec(spec, style)
    assert modified["style_name"] == "illustrated"
    assert modified["style_modifier"] == style.prompt_modifier
    # Original fields preserved
    assert modified["scene_description"] == "student studying"


def test_apply_style_does_not_mutate_original() -> None:
    """apply_style_to_spec returns a new dict, not mutating input."""
    spec = {"scene_description": "test"}
    style = STYLE_PRESETS["photorealistic"]
    modified = apply_style_to_spec(spec, style)
    assert "style_name" not in spec
    assert "style_name" in modified


# --- Experiment Results ---


def test_experiment_result_identifies_best_worst() -> None:
    """StyleExperimentResult correctly reports best and worst style."""
    result = StyleExperimentResult(
        ad_id="ad_001",
        audience="parents",
        style_results={
            "photorealistic": {"composite_score": 8.0},
            "illustrated": {"composite_score": 6.5},
            "flat_design": {"composite_score": 5.0},
        },
        best_style="photorealistic",
        worst_style="flat_design",
    )
    assert result.best_style == "photorealistic"
    assert result.worst_style == "flat_design"


def test_aggregate_style_results(tmp_path: Path) -> None:
    """aggregate_style_results computes average composite per audience per style."""
    from iterate.ledger import log_event

    ledger_path = str(tmp_path / "ledger.jsonl")

    # 2 experiments for parents
    for i, (photo_score, illust_score) in enumerate([(8.0, 6.0), (7.0, 7.0)]):
        log_event(ledger_path, {
            "event_type": "StyleExperiment",
            "ad_id": f"ad_{i:03d}",
            "brief_id": "b001",
            "cycle_number": 1,
            "action": "style-experiment",
            "inputs": {"audience": "parents"},
            "outputs": {
                "style_results": {
                    "photorealistic": {"composite_score": photo_score},
                    "illustrated": {"composite_score": illust_score},
                },
            },
            "scores": {},
            "tokens_consumed": 0,
            "model_used": "",
            "seed": "",
        })

    results = aggregate_style_results(ledger_path)
    assert "parents" in results
    # avg photorealistic = (8+7)/2 = 7.5, illustrated = (6+7)/2 = 6.5
    assert abs(results["parents"]["photorealistic"] - 7.5) < 0.01
    assert abs(results["parents"]["illustrated"] - 6.5) < 0.01


# --- Style-Audience Mapping ---


def test_build_style_audience_map(tmp_path: Path) -> None:
    """build_style_audience_map picks highest-scoring style per audience."""
    from iterate.ledger import log_event

    ledger_path = str(tmp_path / "ledger.jsonl")

    # 5 experiments for parents — photorealistic wins
    for i in range(5):
        log_event(ledger_path, {
            "event_type": "StyleExperiment",
            "ad_id": f"ad_{i:03d}",
            "brief_id": "b001",
            "cycle_number": 1,
            "action": "style-experiment",
            "inputs": {"audience": "parents"},
            "outputs": {
                "style_results": {
                    "photorealistic": {"composite_score": 8.0},
                    "illustrated": {"composite_score": 6.0},
                },
            },
            "scores": {},
            "tokens_consumed": 0,
            "model_used": "",
            "seed": "",
        })

    style_map = build_style_audience_map(ledger_path, min_samples=5)
    assert isinstance(style_map, StyleAudienceMap)
    assert style_map.mappings["parents"] == "photorealistic"
    assert style_map.sample_sizes["parents"] == 5


def test_low_sample_size_low_confidence(tmp_path: Path) -> None:
    """Fewer than min_samples → low confidence."""
    from iterate.ledger import log_event

    ledger_path = str(tmp_path / "ledger.jsonl")

    # Only 2 experiments (below min_samples=5)
    for i in range(2):
        log_event(ledger_path, {
            "event_type": "StyleExperiment",
            "ad_id": f"ad_{i:03d}",
            "brief_id": "b001",
            "cycle_number": 1,
            "action": "style-experiment",
            "inputs": {"audience": "students"},
            "outputs": {
                "style_results": {
                    "illustrated": {"composite_score": 8.0},
                },
            },
            "scores": {},
            "tokens_consumed": 0,
            "model_used": "",
            "seed": "",
        })

    style_map = build_style_audience_map(ledger_path, min_samples=5)
    assert style_map.confidence["students"] < 1.0


def test_get_recommended_style_with_data() -> None:
    """Returns recommended style when data exists."""
    style_map = StyleAudienceMap(
        mappings={"parents": "lifestyle"},
        confidence={"parents": 1.0},
        sample_sizes={"parents": 10},
    )
    assert get_recommended_style("parents", style_map) == "lifestyle"


def test_get_recommended_style_fallback() -> None:
    """Falls back to photorealistic when no data for audience."""
    style_map = StyleAudienceMap(mappings={}, confidence={}, sample_sizes={})
    assert get_recommended_style("unknown_audience", style_map) == "photorealistic"
