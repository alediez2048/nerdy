"""Tests for simulated performance dataset generator (PF-02)."""

import json
import os
import tempfile

from data.simulated_performance import (
    BASE_CTR,
    generate_simulated_dataset,
    generate_and_save,
)


def _make_evaluated_ads(count: int = 50) -> list[dict]:
    """Generate mock evaluated ads with varied scores."""
    import random
    rng = random.Random(99)
    ads = []
    for i in range(count):
        aggregate = rng.uniform(3.0, 9.0)
        scores = {
            "clarity": _clamp(aggregate + rng.gauss(0, 0.8), 1, 10),
            "value_proposition": _clamp(aggregate + rng.gauss(0, 0.8), 1, 10),
            "cta": _clamp(aggregate + rng.gauss(0, 1.0), 1, 10),
            "brand_voice": _clamp(aggregate + rng.gauss(0, 0.7), 1, 10),
            "emotional_resonance": _clamp(aggregate + rng.gauss(0, 0.9), 1, 10),
        }
        ads.append({
            "ad_id": f"ad_test_{i:03d}",
            "scores": scores,
            "aggregate_score": aggregate,
            "campaign_goal": rng.choice(["awareness", "conversion"]),
            "audience": rng.choice(["parents", "students"]),
        })
    return ads


def _clamp(v, lo, hi):
    return max(lo, min(hi, v))


class TestDataGeneration:
    def test_generates_correct_count(self):
        ads = _make_evaluated_ads(30)
        records = generate_simulated_dataset(ads, seed=42)
        assert len(records) == 30

    def test_deterministic_with_seed(self):
        ads = _make_evaluated_ads(20)
        r1 = generate_simulated_dataset(ads, seed=42)
        r2 = generate_simulated_dataset(ads, seed=42)
        assert [r.ctr for r in r1] == [r.ctr for r in r2]

    def test_different_seed_different_results(self):
        ads = _make_evaluated_ads(20)
        r1 = generate_simulated_dataset(ads, seed=42)
        r2 = generate_simulated_dataset(ads, seed=99)
        assert [r.ctr for r in r1] != [r.ctr for r in r2]

    def test_ctr_in_realistic_range(self):
        ads = _make_evaluated_ads(100)
        records = generate_simulated_dataset(ads, seed=42)
        for r in records:
            assert 0.001 <= r.ctr <= 0.08, f"CTR {r.ctr} out of bounds for {r.ad_id}"

    def test_impressions_in_range(self):
        ads = _make_evaluated_ads(50)
        records = generate_simulated_dataset(ads, seed=42)
        for r in records:
            assert 5000 <= r.impressions <= 50000

    def test_conversions_non_negative(self):
        ads = _make_evaluated_ads(50)
        records = generate_simulated_dataset(ads, seed=42)
        for r in records:
            assert r.conversions >= 0

    def test_cpa_none_for_zero_conversions(self):
        # Generate enough to likely get some zero-conversion records
        ads = _make_evaluated_ads(100)
        records = generate_simulated_dataset(ads, seed=42)
        zero_conv = [r for r in records if r.conversions == 0]
        for r in zero_conv:
            assert r.cpa is None

    def test_outliers_present(self):
        """At least some high-score ads should have low CTR and vice versa."""
        ads = _make_evaluated_ads(200)
        records = generate_simulated_dataset(ads, seed=42)

        # Build score lookup
        score_map = {a["ad_id"]: a["aggregate_score"] for a in ads}

        # Find high-score low-CTR cases
        median_ctr = sorted(r.ctr for r in records)[len(records) // 2]
        high_score_low_ctr = [
            r for r in records
            if score_map.get(r.ad_id, 0) >= 7.0 and r.ctr < median_ctr
        ]
        assert len(high_score_low_ctr) > 0, "Expected some high-score ads with below-median CTR"


class TestSaveOutput:
    def test_save_creates_file(self):
        ads = _make_evaluated_ads(10)
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            output_path = f.name
        try:
            records = generate_and_save(ads, output_path=output_path, seed=42)
            assert os.path.exists(output_path)
            with open(output_path) as f:
                data = json.load(f)
            assert "metadata" in data
            assert "records" in data
            assert data["metadata"]["type"] == "simulated_performance_data"
            assert len(data["records"]) == 10
        finally:
            os.unlink(output_path)

    def test_metadata_documents_noise_model(self):
        ads = _make_evaluated_ads(5)
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            output_path = f.name
        try:
            generate_and_save(ads, output_path=output_path, seed=42)
            with open(output_path) as f:
                data = json.load(f)
            nm = data["metadata"]["noise_model"]
            assert nm["copy_quality_weight"] == 0.30
            assert nm["targeting_weight"] == 0.40
            assert "honest_disclaimer" in data["metadata"]
        finally:
            os.unlink(output_path)
