"""Competitive intelligence API routes (PD-10)."""
import json
import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Query

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/competitive", tags=["competitive"])

RAW_ADS_DIR = Path("data/competitive/raw")
COMPETITORS = ["chegg", "kaplan", "varsity_tutors", "wyzant"]


@router.get("/ads")
def get_competitive_ads(
    competitor: str | None = Query(None),
    hook_type: str | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> dict[str, Any]:
    """Return scraped competitor ads from Meta Ad Library.

    Reads from data/competitive/raw/{competitor}.json files.
    Optionally filters by hook_type from patterns.json classification.
    """
    ads: list[dict] = []

    # Load raw ads from JSON files
    target_files = [f"{competitor}.json"] if competitor else [f"{c}.json" for c in COMPETITORS]

    for filename in target_files:
        filepath = RAW_ADS_DIR / filename
        if not filepath.exists():
            continue
        try:
            with open(filepath) as f:
                file_ads = json.load(f)
            comp_name = filename.replace(".json", "").replace("_", " ").title()
            for ad in file_ads:
                ad["_competitor"] = comp_name
            ads.extend(file_ads)
        except Exception as e:
            logger.warning("Failed to load %s: %s", filepath, e)

    # Load pattern classifications for hook_type filtering
    if hook_type:
        patterns_path = Path("data/competitive/patterns.json")
        classified: dict[str, dict] = {}
        if patterns_path.exists():
            try:
                with open(patterns_path) as f:
                    pdata = json.load(f)
                for record in pdata.get("pattern_records", []):
                    ad_id = record.get("ad_library_id", "")
                    if ad_id:
                        classified[ad_id] = record
            except Exception:
                pass

        # Filter ads that match the hook_type
        filtered = []
        for ad in ads:
            ad_id = ad.get("Ad Library ID", "")
            record = classified.get(ad_id, {})
            if record.get("hook_type", "").lower() == hook_type.lower():
                ad["_hook_type"] = record.get("hook_type", "")
                ad["_emotional_register"] = record.get("emotional_register", "")
                filtered.append(ad)
        ads = filtered
    else:
        # Enrich all ads with classification data if available
        patterns_path = Path("data/competitive/patterns.json")
        if patterns_path.exists():
            try:
                with open(patterns_path) as f:
                    pdata = json.load(f)
                classified_all: dict[str, dict] = {}
                for record in pdata.get("pattern_records", []):
                    ad_id = record.get("ad_library_id", "")
                    if ad_id:
                        classified_all[ad_id] = record
                for ad in ads:
                    ad_id = ad.get("Ad Library ID", "")
                    if ad_id in classified_all:
                        ad["_hook_type"] = classified_all[ad_id].get("hook_type", "")
                        ad["_emotional_register"] = classified_all[ad_id].get("emotional_register", "")
                        ad["_body_pattern"] = classified_all[ad_id].get("body_pattern", "")
                        ad["_cta_style"] = classified_all[ad_id].get("cta_style", "")
            except Exception:
                pass

    total = len(ads)
    paginated = ads[offset:offset + limit]

    return {
        "ads": paginated,
        "total": total,
        "offset": offset,
        "limit": limit,
        "competitors": COMPETITORS,
    }
