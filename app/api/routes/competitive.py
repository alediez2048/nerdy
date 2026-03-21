"""Competitive intelligence API routes (PD-10, PD-11)."""
import json
import logging
import sys
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, Form, Query, UploadFile

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/competitive", tags=["competitive"])

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
RAW_ADS_DIR = PROJECT_ROOT / "data" / "competitive" / "raw"
PATTERNS_PATH = PROJECT_ROOT / "data" / "competitive" / "patterns.json"
COMPETITORS = ["chegg", "kaplan", "varsity_tutors", "wyzant"]

# Import classifiers from scripts/process_competitive_data.py
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
from process_competitive_data import (  # noqa: E402
    classify_body_pattern,
    classify_cta,
    classify_emotional_register,
    classify_hook,
    get_first_sentence,
    normalize_text,
)


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


@router.post("/upload")
async def upload_competitive_ads(
    file: UploadFile = File(...),
    competitor_name: str = Form(...),
) -> dict[str, Any]:
    """Upload and classify competitor ads from Meta Ad Library JSON export.

    Parses the JSON, classifies each ad using regex-based classifiers,
    deduplicates against existing data, saves raw ads and updates patterns.json.
    """
    global COMPETITORS

    # 1. Read and parse the uploaded JSON
    content = await file.read()
    try:
        uploaded_ads: list[dict] = json.loads(content)
    except json.JSONDecodeError as exc:
        return {"error": f"Invalid JSON: {exc}"}

    if not isinstance(uploaded_ads, list):
        return {"error": "Expected a JSON array of ad objects"}

    # 2. Determine competitor key for file naming
    competitor_key = competitor_name.strip().lower().replace(" ", "_")

    # 3. Load existing raw ads for this competitor (for dedup)
    raw_path = RAW_ADS_DIR / f"{competitor_key}.json"
    existing_ads: list[dict] = []
    existing_texts: set[str] = set()
    if raw_path.exists():
        try:
            with open(raw_path) as f:
                existing_ads = json.load(f)
            for ad in existing_ads:
                text = ad.get("Ad Text Content", "").strip()
                if text:
                    existing_texts.add(normalize_text(text))
        except Exception:
            pass

    # 4. Load existing patterns.json
    patterns_data: dict[str, Any] = {
        "metadata": {
            "version": "2.0",
            "created": "2026-03-14",
            "source": "Meta Ad Library via Thunderbit scraper (P0-09)",
            "purpose": "Real competitive patterns for pipeline differentiation (R2-Q2)",
            "competitors": [],
            "total_ads_scraped": 0,
            "unique_ads": 0,
            "pattern_records": 0,
        },
        "patterns": [],
        "competitor_summaries": {},
    }
    if PATTERNS_PATH.exists():
        try:
            with open(PATTERNS_PATH) as f:
                patterns_data = json.load(f)
        except Exception:
            pass

    existing_pattern_ids: set[str] = set()
    for rec in patterns_data.get("patterns", []):
        aid = rec.get("ad_library_id", "")
        if aid:
            existing_pattern_ids.add(aid)

    # 5. Process each ad
    new_ads: list[dict] = []
    new_patterns: list[dict] = []
    ads_parsed = 0
    ads_duplicate = 0

    # Count existing patterns for this competitor to continue numbering
    comp_abbrev = competitor_key
    existing_count = sum(
        1 for r in patterns_data.get("patterns", [])
        if r.get("competitor", "").lower().replace(" ", "_") == comp_abbrev
    )

    for ad in uploaded_ads:
        text = ad.get("Ad Text Content", "").strip()
        if not text or len(text) < 10:
            continue
        ads_parsed += 1

        norm = normalize_text(text)
        if norm in existing_texts:
            ads_duplicate += 1
            continue

        # Mark as seen
        existing_texts.add(norm)
        new_ads.append(ad)

        # Classify
        hook_type = classify_hook(text)
        body_pattern = classify_body_pattern(text)
        cta_style = classify_cta(text)
        emotional_register = classify_emotional_register(text)

        ad_library_id = ad.get("Ad Library ID", "")

        # Skip if this ad_library_id already has a pattern record
        if ad_library_id and ad_library_id in existing_pattern_ids:
            continue

        existing_count += 1
        record = {
            "pattern_id": f"comp_{comp_abbrev}_{existing_count:02d}",
            "ad_library_id": ad_library_id,
            "competitor": competitor_name.strip(),
            "captured_date": ad.get("Started Running Date", ""),
            "ad_text": text,
            "hook_type": hook_type,
            "hook_text": get_first_sentence(text),
            "body_pattern": body_pattern,
            "cta_style": cta_style,
            "emotional_register": emotional_register,
            "primary_audience": "both",
            "tone": "authoritative_reassuring",
            "word_count": len(text.split()),
            "has_hashtags": bool("#" in text),
            "has_mentions": bool("@" in text),
            "is_ugc_creator": bool("#" in text and "@" in text),
            "tags": [hook_type, body_pattern],
        }
        new_patterns.append(record)
        if ad_library_id:
            existing_pattern_ids.add(ad_library_id)

    # 6. Save — append new ads to raw file
    RAW_ADS_DIR.mkdir(parents=True, exist_ok=True)
    all_raw = existing_ads + new_ads
    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump(all_raw, f, indent=2, ensure_ascii=False)

    # 7. Update patterns.json
    patterns_data.setdefault("patterns", []).extend(new_patterns)
    meta = patterns_data.setdefault("metadata", {})
    meta["total_ads_scraped"] = meta.get("total_ads_scraped", 0) + len(new_ads)
    meta["unique_ads"] = meta.get("unique_ads", 0) + len(new_ads)
    meta["pattern_records"] = len(patterns_data["patterns"])

    # Update competitor list in metadata
    comp_list: list[str] = meta.get("competitors", [])
    if competitor_name.strip() not in comp_list:
        comp_list.append(competitor_name.strip())
        meta["competitors"] = comp_list

    # Build/update competitor summary for this competitor
    comp_patterns = [
        r for r in patterns_data["patterns"]
        if r.get("competitor", "").lower().replace(" ", "_") == comp_abbrev
    ]
    if comp_patterns:
        hooks: dict[str, int] = {}
        emotions: dict[str, int] = {}
        for r in comp_patterns:
            ht = r.get("hook_type", "")
            er = r.get("emotional_register", "")
            hooks[ht] = hooks.get(ht, 0) + 1
            emotions[er] = emotions.get(er, 0) + 1
        dominant_hooks = sorted(hooks, key=hooks.get, reverse=True)[:3]  # type: ignore[arg-type]
        emotional_levers = sorted(emotions, key=emotions.get, reverse=True)[:3]  # type: ignore[arg-type]

        summaries = patterns_data.setdefault("competitor_summaries", {})
        existing_summary = summaries.get(competitor_name.strip(), {})
        summaries[competitor_name.strip()] = {
            "strategy": existing_summary.get("strategy", f"Uploaded competitor data for {competitor_name.strip()}."),
            "dominant_hooks": dominant_hooks,
            "emotional_levers": emotional_levers,
            "gaps": existing_summary.get("gaps", "Analysis pending."),
        }

    PATTERNS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(PATTERNS_PATH, "w", encoding="utf-8") as f:
        json.dump(patterns_data, f, indent=2, ensure_ascii=False)

    # 8. Update module-level COMPETITORS list
    if competitor_key not in COMPETITORS:
        COMPETITORS.append(competitor_key)

    return {
        "ads_parsed": ads_parsed,
        "ads_new": len(new_ads),
        "ads_duplicate": ads_duplicate,
        "patterns_added": len(new_patterns),
        "competitor": competitor_name.strip(),
    }
