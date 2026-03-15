"""Tests for Meta performance data schema and ingestion (PF-01)."""

import json
import os
import tempfile

import pytest

from evaluate.performance_schema import (
    MetaPerformanceRecord,
    PerformanceValidationError,
    dict_to_record,
    ingest_performance_data,
    load_performance_from_csv,
    load_performance_from_json,
    validate_performance_record,
)
from iterate.ledger import read_events_filtered


def _valid_record_dict(**overrides):
    """Helper to create a valid raw record dict."""
    base = {
        "ad_id": "ad_test_001",
        "campaign_id": "camp_001",
        "impressions": 10000,
        "clicks": 180,
        "conversions": 5,
        "spend": 50.00,
        "engagement_rate": 0.032,
        "relevance_score": 7.5,
        "date_range_start": "2026-03-01",
        "date_range_end": "2026-03-07",
        "placement": "feed",
        "audience_segment": "parents",
    }
    base.update(overrides)
    return base


class TestValidation:
    def test_valid_record_passes(self):
        errors = validate_performance_record(_valid_record_dict())
        assert errors == []

    def test_missing_required_field(self):
        record = _valid_record_dict()
        del record["ad_id"]
        errors = validate_performance_record(record)
        assert any("ad_id" in e for e in errors)

    def test_negative_impressions(self):
        errors = validate_performance_record(_valid_record_dict(impressions=-1))
        assert any("non-negative" in e for e in errors)

    def test_ctr_exceeds_one(self):
        errors = validate_performance_record(_valid_record_dict(ctr=1.5))
        assert any("CTR" in e for e in errors)

    def test_ctr_mismatch(self):
        errors = validate_performance_record(
            _valid_record_dict(ctr=0.5)  # real CTR is 180/10000 = 0.018
        )
        assert any("CTR mismatch" in e for e in errors)

    def test_invalid_placement(self):
        errors = validate_performance_record(_valid_record_dict(placement="billboard"))
        assert any("placement" in e for e in errors)

    def test_relevance_out_of_range(self):
        errors = validate_performance_record(_valid_record_dict(relevance_score=15.0))
        assert any("relevance_score" in e for e in errors)

    def test_cpa_mismatch(self):
        # spend=50, conversions=5, so CPA should be 10.0
        errors = validate_performance_record(_valid_record_dict(cpa=99.0))
        assert any("CPA mismatch" in e for e in errors)


class TestDictToRecord:
    def test_creates_record(self):
        record = dict_to_record(_valid_record_dict())
        assert isinstance(record, MetaPerformanceRecord)
        assert record.ad_id == "ad_test_001"
        assert record.impressions == 10000
        assert record.clicks == 180

    def test_computes_ctr(self):
        record = dict_to_record(_valid_record_dict())
        assert abs(record.ctr - 0.018) < 0.001

    def test_computes_cpa(self):
        record = dict_to_record(_valid_record_dict())
        assert record.cpa == 10.0

    def test_none_cpa_zero_conversions(self):
        record = dict_to_record(_valid_record_dict(conversions=0))
        assert record.cpa is None

    def test_invalid_record_raises(self):
        bad = _valid_record_dict()
        del bad["ad_id"]
        with pytest.raises(PerformanceValidationError):
            dict_to_record(bad)


class TestIngestion:
    def test_ingest_writes_to_ledger(self):
        record = dict_to_record(_valid_record_dict())
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            ledger_path = f.name
        try:
            count = ingest_performance_data([record], ledger_path)
            assert count == 1
            events = read_events_filtered(ledger_path, event_type="PerformanceIngested")
            assert len(events) == 1
            assert events[0]["ad_id"] == "ad_test_001"
            assert events[0]["outputs"]["ctr"] == record.ctr
        finally:
            os.unlink(ledger_path)

    def test_ingest_multiple_records(self):
        records = [
            dict_to_record(_valid_record_dict(ad_id=f"ad_{i}"))
            for i in range(5)
        ]
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            ledger_path = f.name
        try:
            count = ingest_performance_data(records, ledger_path)
            assert count == 5
            events = read_events_filtered(ledger_path, event_type="PerformanceIngested")
            assert len(events) == 5
        finally:
            os.unlink(ledger_path)


class TestCSVLoading:
    def test_load_from_csv(self):
        csv_content = (
            "ad_id,campaign_id,impressions,clicks,conversions,spend,"
            "engagement_rate,relevance_score,date_range_start,date_range_end,"
            "placement,audience_segment\n"
            "ad_001,camp_001,10000,180,5,50.00,0.032,7.5,"
            "2026-03-01,2026-03-07,feed,parents\n"
        )
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write(csv_content)
            csv_path = f.name
        try:
            records = load_performance_from_csv(csv_path)
            assert len(records) == 1
            assert records[0].ad_id == "ad_001"
            assert records[0].impressions == 10000
        finally:
            os.unlink(csv_path)


class TestJSONLoading:
    def test_load_from_json(self):
        data = {"records": [_valid_record_dict()]}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            json_path = f.name
        try:
            records = load_performance_from_json(json_path)
            assert len(records) == 1
            assert records[0].ad_id == "ad_test_001"
        finally:
            os.unlink(json_path)
