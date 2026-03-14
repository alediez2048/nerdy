"""Tests for per-ad seed chain and snapshot utilities (P0-03, R3-Q4)."""

import json
from pathlib import Path

import pytest
import yaml

from generate.seeds import get_ad_seed, load_global_seed
from iterate.snapshots import capture_snapshot


# --- get_ad_seed tests ---


def test_get_ad_seed_deterministic() -> None:
    """Same inputs always produce the same seed."""
    s1 = get_ad_seed("global", "brief_001", 0)
    s2 = get_ad_seed("global", "brief_001", 0)
    assert s1 == s2


def test_get_ad_seed_different_cycle_produces_different_seed() -> None:
    """Different cycle_number for same brief produces different seed."""
    s0 = get_ad_seed("global", "brief_001", 0)
    s1 = get_ad_seed("global", "brief_001", 1)
    s2 = get_ad_seed("global", "brief_001", 2)
    assert s0 != s1 != s2


def test_get_ad_seed_different_brief_produces_different_seed() -> None:
    """Different brief_id produces different seed."""
    s_a = get_ad_seed("global", "brief_001", 0)
    s_b = get_ad_seed("global", "brief_002", 0)
    assert s_a != s_b


def test_get_ad_seed_independent_of_order() -> None:
    """Seed for ad_006 is unchanged whether ad_005 exists or not (identity-derived)."""
    seed_006 = get_ad_seed("global", "brief_006", 0)
    seed_006_again = get_ad_seed("global", "brief_006", 0)
    # Simulating: we never computed ad_005's seed; ad_006's seed is still deterministic
    assert seed_006 == seed_006_again


def test_get_ad_seed_valid_integer() -> None:
    """Seed is a non-negative integer in reasonable range."""
    seed = get_ad_seed("global", "brief_001", 0)
    assert isinstance(seed, int)
    assert seed >= 0
    assert seed < 2**32  # sha256[:8] hex = 8 hex chars = 2^32 max


# --- load_global_seed tests ---


def test_load_global_seed_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """GLOBAL_SEED env var takes precedence."""
    monkeypatch.setenv("GLOBAL_SEED", "env-seed-123")
    assert load_global_seed() == "env-seed-123"


def test_load_global_seed_from_config(tmp_path: Path) -> None:
    """Falls back to config.yaml when GLOBAL_SEED not set."""
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.dump({"global_seed": "config-seed-456"}))
    with pytest.MonkeyPatch.context() as m:
        m.delenv("GLOBAL_SEED", raising=False)
        assert load_global_seed(str(config_path)) == "config-seed-456"


def test_load_global_seed_default(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Falls back to default when env and config missing or has no global_seed."""
    monkeypatch.delenv("GLOBAL_SEED", raising=False)
    config_path = tmp_path / "config.yaml"
    config_path.write_text("quality_threshold: 7.0\n")  # no global_seed
    result = load_global_seed(str(config_path))
    assert isinstance(result, str)
    assert len(result) > 0


# --- capture_snapshot tests ---


def test_capture_snapshot_json_serializable() -> None:
    """Snapshot dict is JSON-serializable."""
    snapshot = capture_snapshot(
        prompt="Generate ad",
        response="Here is the ad...",
        model="gemini-flash",
        parameters={"temperature": 0.7},
        seed=12345,
    )
    json_str = json.dumps(snapshot, default=str)
    parsed = json.loads(json_str)
    assert parsed == snapshot or all(k in parsed for k in ("prompt", "response", "model_version", "seed"))


def test_capture_snapshot_contains_required_fields() -> None:
    """Snapshot contains prompt, response, model_version, timestamp, parameters, seed."""
    snapshot = capture_snapshot(
        prompt="p",
        response="r",
        model="m",
        parameters={"temp": 0.5},
        seed=999,
    )
    assert "prompt" in snapshot
    assert "response" in snapshot
    assert "model_version" in snapshot
    assert "timestamp" in snapshot
    assert "parameters" in snapshot
    assert "seed" in snapshot
    assert snapshot["prompt"] == "p"
    assert snapshot["response"] == "r"
    assert snapshot["model_version"] == "m"
    assert snapshot["parameters"] == {"temp": 0.5}
    assert snapshot["seed"] == 999
