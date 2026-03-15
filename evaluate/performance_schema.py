"""Meta Ads Manager performance data schema and ingestion (PF-01).

Defines the data contract for real-world performance metrics (CTR, conversions, CPA, etc.)
and ingestion functions that map performance records to the append-only ledger.
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

from iterate.ledger import log_event


@dataclass
class MetaPerformanceRecord:
    """A single ad's performance data from Meta Ads Manager."""
    ad_id: str
    campaign_id: str
    impressions: int
    clicks: int
    ctr: float  # clicks / impressions
    conversions: int
    cpa: float | None  # spend / conversions (None if zero conversions)
    spend: float
    engagement_rate: float  # (reactions + comments + shares) / impressions
    relevance_score: float  # Meta's 1-10 relevance score
    date_range_start: str  # ISO date
    date_range_end: str  # ISO date
    placement: str  # "feed", "stories", "reels"
    audience_segment: str  # "parents", "students", etc.


class PerformanceValidationError(ValueError):
    """Raised when a performance record fails validation."""


def validate_performance_record(record: dict[str, Any]) -> list[str]:
    """Validate a raw performance record dict. Returns list of error strings (empty = valid)."""
    errors: list[str] = []

    # Required fields
    required = ["ad_id", "campaign_id", "impressions", "clicks", "spend", "placement", "audience_segment"]
    for field in required:
        if field not in record:
            errors.append(f"Missing required field: {field}")

    if errors:
        return errors  # Can't validate further without required fields

    # Non-negative numeric fields
    for field in ["impressions", "clicks", "conversions", "spend"]:
        val = record.get(field, 0)
        if val is not None and val < 0:
            errors.append(f"{field} must be non-negative, got {val}")

    # CTR derivation check
    impressions = record.get("impressions", 0)
    clicks = record.get("clicks", 0)

    if impressions > 0:
        expected_ctr = clicks / impressions
        provided_ctr = record.get("ctr")
        if provided_ctr is not None and abs(provided_ctr - expected_ctr) > 0.001:
            errors.append(f"CTR mismatch: provided {provided_ctr:.4f}, expected {expected_ctr:.4f}")

    if record.get("ctr") is not None and record["ctr"] > 1.0:
        errors.append(f"CTR cannot exceed 1.0, got {record['ctr']}")

    if record.get("ctr") is not None and record["ctr"] < 0:
        errors.append(f"CTR must be non-negative, got {record['ctr']}")

    # CPA check
    conversions = record.get("conversions", 0)
    spend = record.get("spend", 0)
    if conversions and conversions > 0:
        expected_cpa = spend / conversions
        provided_cpa = record.get("cpa")
        if provided_cpa is not None and abs(provided_cpa - expected_cpa) > 0.01:
            errors.append(f"CPA mismatch: provided {provided_cpa:.2f}, expected {expected_cpa:.2f}")

    # Relevance score bounds
    relevance = record.get("relevance_score")
    if relevance is not None and (relevance < 1.0 or relevance > 10.0):
        errors.append(f"relevance_score must be 1-10, got {relevance}")

    # Valid placements
    valid_placements = {"feed", "stories", "reels"}
    placement = record.get("placement", "")
    if placement and placement not in valid_placements:
        errors.append(f"Invalid placement '{placement}', must be one of {valid_placements}")

    return errors


def dict_to_record(raw: dict[str, Any]) -> MetaPerformanceRecord:
    """Convert a raw dict to a MetaPerformanceRecord, computing derived fields.

    Raises PerformanceValidationError if validation fails.
    """
    errors = validate_performance_record(raw)
    if errors:
        raise PerformanceValidationError("; ".join(errors))

    impressions = int(raw["impressions"])
    clicks = int(raw["clicks"])
    conversions = int(raw.get("conversions", 0))
    spend = float(raw["spend"])

    ctr = clicks / impressions if impressions > 0 else 0.0
    cpa = spend / conversions if conversions > 0 else None

    return MetaPerformanceRecord(
        ad_id=str(raw["ad_id"]),
        campaign_id=str(raw["campaign_id"]),
        impressions=impressions,
        clicks=clicks,
        ctr=round(ctr, 6),
        conversions=conversions,
        cpa=round(cpa, 2) if cpa is not None else None,
        spend=round(spend, 2),
        engagement_rate=float(raw.get("engagement_rate", 0.0)),
        relevance_score=float(raw.get("relevance_score", 5.0)),
        date_range_start=str(raw.get("date_range_start", "")),
        date_range_end=str(raw.get("date_range_end", "")),
        placement=str(raw["placement"]),
        audience_segment=str(raw["audience_segment"]),
    )


def ingest_performance_data(
    records: list[MetaPerformanceRecord], ledger_path: str
) -> int:
    """Ingest performance records into the ledger as PerformanceIngested events.

    Returns the number of records ingested.
    """
    count = 0
    for record in records:
        event = {
            "event_type": "PerformanceIngested",
            "ad_id": record.ad_id,
            "brief_id": record.campaign_id,
            "cycle_number": 0,
            "action": "ingest_performance",
            "tokens_consumed": 0,
            "model_used": "none",
            "seed": 0,
            "inputs": {"source": "meta_ads_manager"},
            "outputs": asdict(record),
        }
        log_event(ledger_path, event)
        count += 1
    return count


def load_performance_from_csv(path: str) -> list[MetaPerformanceRecord]:
    """Load performance records from a CSV file.

    CSV must have headers matching MetaPerformanceRecord fields.
    Numeric fields are auto-converted.
    """
    records: list[MetaPerformanceRecord] = []
    csv_path = Path(path)

    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Convert numeric fields
            raw: dict[str, Any] = dict(row)
            for int_field in ["impressions", "clicks", "conversions"]:
                if int_field in raw and raw[int_field]:
                    raw[int_field] = int(raw[int_field])
            for float_field in ["spend", "engagement_rate", "relevance_score", "ctr", "cpa"]:
                if float_field in raw and raw[float_field]:
                    raw[float_field] = float(raw[float_field])
                elif float_field in raw:
                    raw[float_field] = None

            records.append(dict_to_record(raw))

    return records


def load_performance_from_json(path: str) -> list[MetaPerformanceRecord]:
    """Load performance records from a JSON file."""
    with open(path) as f:
        data = json.load(f)

    raw_records = data.get("records", data) if isinstance(data, dict) else data
    return [dict_to_record(r) for r in raw_records]
