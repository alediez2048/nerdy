"""Simulated Meta Ads Manager performance dataset generator (PF-02).

Generates realistic synthetic performance data where LLM-scored ads correlate
imperfectly (r ~0.3-0.5) with real-world CTR/conversions. Models explicit noise
sources to demonstrate that copy quality is only ~30% of ad performance.

Noise Model:
  - Copy quality contribution: ~30% of CTR variance (what the pipeline controls)
  - Targeting quality: ~40% of variance (uncontrollable — bid strategy, audience config)
  - Audience match: ~20% of variance (uncontrollable — creative-audience fit beyond copy)
  - Temporal/fatigue: ~10% of variance (uncontrollable — time of day, ad fatigue)

This is honest about being simulated. The metadata documents every assumption.
"""

from __future__ import annotations

import hashlib
import json
import random
from dataclasses import asdict
from pathlib import Path

from evaluate.performance_schema import MetaPerformanceRecord


# Realistic Meta Ads benchmarks (education/test-prep vertical)
BASE_CTR = {
    "feed": 0.018,      # ~1.8% average for education ads on feed
    "stories": 0.032,   # ~3.2% for stories (more immersive)
    "reels": 0.025,     # ~2.5% for reels
}

BASE_CONVERSION_RATE = 0.08  # 8% of clicks convert (landing page dependent)
BASE_CPM = 12.50             # $12.50 CPM for education vertical
BASE_ENGAGEMENT_RATE = 0.035  # 3.5% engagement rate baseline

# Variance contribution weights (must sum to ~1.0)
COPY_QUALITY_WEIGHT = 0.30
TARGETING_WEIGHT = 0.40
AUDIENCE_MATCH_WEIGHT = 0.20
TEMPORAL_WEIGHT = 0.10

# Dimension-to-metric correlation targets
# These encode our hypothesis about which dimensions predict which metrics
DIMENSION_METRIC_INFLUENCE = {
    # (dimension, metric): correlation strength
    ("cta", "conversion_rate"): 0.45,
    ("value_proposition", "conversion_rate"): 0.30,
    ("emotional_resonance", "engagement_rate"): 0.50,
    ("brand_voice", "engagement_rate"): 0.30,
    ("clarity", "ctr"): 0.40,
    ("emotional_resonance", "ctr"): 0.25,
    ("value_proposition", "ctr"): 0.20,
}


def _seed_from_ad_id(ad_id: str, global_seed: str = "pf-sim") -> int:
    """Derive deterministic seed from ad_id."""
    h = hashlib.sha256(f"{global_seed}:{ad_id}".encode()).hexdigest()
    return int(h[:8], 16)


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def generate_simulated_dataset(
    evaluated_ads: list[dict],
    seed: int = 42,
    outlier_fraction: float = 0.10,
) -> list[MetaPerformanceRecord]:
    """Generate simulated performance data for evaluated ads.

    Args:
        evaluated_ads: List of dicts with keys: ad_id, scores (dict of dimension->float),
            aggregate_score, campaign_goal, audience.
        seed: Random seed for reproducibility.
        outlier_fraction: Fraction of records that are deliberate outliers (~10%).

    Returns:
        List of MetaPerformanceRecord objects with realistic distributions.
    """
    rng = random.Random(seed)
    records: list[MetaPerformanceRecord] = []
    placements = ["feed", "stories", "reels"]

    for ad in evaluated_ads:
        ad_id = ad["ad_id"]
        scores = ad.get("scores", {})
        aggregate = ad.get("aggregate_score", 5.0)
        audience = ad.get("audience", "parents")
        campaign_goal = ad.get("campaign_goal", "awareness")

        # Deterministic per-ad seed
        ad_seed = _seed_from_ad_id(ad_id)
        ad_rng = random.Random(ad_seed + seed)

        placement = ad_rng.choice(placements)
        base_ctr = BASE_CTR[placement]

        # --- Noise Model ---

        # 1. Copy quality contribution (~30% of variance)
        # Normalize aggregate score: (score - 5) / 5 gives -1 to +1 range
        score_factor = (aggregate - 5.0) / 5.0
        copy_contribution = score_factor * COPY_QUALITY_WEIGHT

        # 2. Targeting quality (~40% of variance) — uncontrollable
        targeting_factor = ad_rng.gauss(0, 1) * 0.5  # wide spread
        targeting_contribution = targeting_factor * TARGETING_WEIGHT

        # 3. Audience match (~20% of variance) — uncontrollable
        audience_factor = ad_rng.gauss(0, 1) * 0.4
        audience_contribution = audience_factor * AUDIENCE_MATCH_WEIGHT

        # 4. Temporal/fatigue (~10% of variance) — uncontrollable
        temporal_factor = ad_rng.gauss(0, 1) * 0.3
        temporal_contribution = temporal_factor * TEMPORAL_WEIGHT

        # Combined multiplier (centered around 1.0)
        total_multiplier = 1.0 + copy_contribution + targeting_contribution + audience_contribution + temporal_contribution

        # Deliberate outlier injection
        is_outlier = ad_rng.random() < outlier_fraction
        if is_outlier:
            if aggregate >= 7.0:
                # Excellent copy, terrible targeting → low CTR
                total_multiplier *= ad_rng.uniform(0.2, 0.5)
            else:
                # Mediocre copy, perfect targeting → high CTR
                total_multiplier *= ad_rng.uniform(1.8, 3.0)

        # --- Compute Metrics ---

        # CTR
        ctr = _clamp(base_ctr * total_multiplier, 0.001, 0.08)

        # Impressions (random but realistic — 5K to 50K)
        impressions = int(ad_rng.gauss(20000, 8000))
        impressions = max(5000, min(50000, impressions))

        clicks = max(1, int(impressions * ctr))
        actual_ctr = clicks / impressions

        # Conversion rate — influenced by CTA and value_proposition scores
        cta_score = scores.get("cta", 5.0)
        vp_score = scores.get("value_proposition", 5.0)
        conv_factor = 1.0 + ((cta_score - 5) / 5) * 0.45 + ((vp_score - 5) / 5) * 0.30
        conv_factor += ad_rng.gauss(0, 0.3)  # noise
        conv_factor = _clamp(conv_factor, 0.3, 2.5)
        conversion_rate = BASE_CONVERSION_RATE * conv_factor

        conversions = max(0, int(clicks * conversion_rate))

        # Spend (CPM-based)
        spend = round((impressions / 1000) * BASE_CPM * ad_rng.uniform(0.8, 1.3), 2)
        cpa = round(spend / conversions, 2) if conversions > 0 else None

        # Engagement rate — influenced by emotional_resonance and brand_voice
        er_score = scores.get("emotional_resonance", 5.0)
        bv_score = scores.get("brand_voice", 5.0)
        eng_factor = 1.0 + ((er_score - 5) / 5) * 0.50 + ((bv_score - 5) / 5) * 0.30
        eng_factor += ad_rng.gauss(0, 0.2)  # noise
        eng_factor = _clamp(eng_factor, 0.3, 2.5)
        engagement_rate = _clamp(BASE_ENGAGEMENT_RATE * eng_factor, 0.005, 0.10)

        # Relevance score — correlated with aggregate but noisy
        relevance_base = 3.0 + (aggregate - 3.0) * 0.6 + ad_rng.gauss(0, 1.0)
        relevance_score = _clamp(round(relevance_base, 1), 1.0, 10.0)

        records.append(MetaPerformanceRecord(
            ad_id=ad_id,
            campaign_id=f"camp_{campaign_goal}",
            impressions=impressions,
            clicks=clicks,
            ctr=round(actual_ctr, 6),
            conversions=conversions,
            cpa=cpa,
            spend=spend,
            engagement_rate=round(engagement_rate, 4),
            relevance_score=relevance_score,
            date_range_start="2026-03-01",
            date_range_end="2026-03-07",
            placement=placement,
            audience_segment=audience,
        ))

    return records


def generate_and_save(
    evaluated_ads: list[dict],
    output_path: str = "data/simulated_performance.json",
    seed: int = 42,
) -> list[MetaPerformanceRecord]:
    """Generate simulated dataset and save to JSON with metadata."""
    records = generate_simulated_dataset(evaluated_ads, seed=seed)

    output = {
        "metadata": {
            "version": "1.0",
            "type": "simulated_performance_data",
            "source": "PF-02 noise model simulation",
            "record_count": len(records),
            "seed": seed,
            "honest_disclaimer": (
                "This is SIMULATED data. Performance records are synthetically generated "
                "using a noise model that encodes realistic variance sources. "
                "Copy quality contributes ~30% of CTR variance. "
                "In production, replace with real Meta Ads Manager exports."
            ),
            "noise_model": {
                "copy_quality_weight": COPY_QUALITY_WEIGHT,
                "targeting_weight": TARGETING_WEIGHT,
                "audience_match_weight": AUDIENCE_MATCH_WEIGHT,
                "temporal_weight": TEMPORAL_WEIGHT,
            },
            "dimension_metric_targets": {
                f"{dim}->{met}": strength
                for (dim, met), strength in DIMENSION_METRIC_INFLUENCE.items()
            },
            "outlier_fraction": 0.10,
            "base_benchmarks": {
                "ctr_feed": BASE_CTR["feed"],
                "ctr_stories": BASE_CTR["stories"],
                "ctr_reels": BASE_CTR["reels"],
                "conversion_rate": BASE_CONVERSION_RATE,
                "cpm": BASE_CPM,
                "engagement_rate": BASE_ENGAGEMENT_RATE,
            },
        },
        "records": [asdict(r) for r in records],
    }

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(output, f, indent=2)

    return records
