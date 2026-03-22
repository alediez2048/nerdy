"""Competitive intelligence API routes (PD-10, PD-11)."""
import json
import logging
import re
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, Form, Query, UploadFile

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


# ---------------------------------------------------------------------------
# PD-11: Upload & Classification
# Classifiers inlined from scripts/process_competitive_data.py to avoid
# fragile sys.path imports across Docker/local environments.
# ---------------------------------------------------------------------------

PATTERNS_PATH = Path("data/competitive/patterns.json")


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())


def _get_first_sentence(text: str, max_words: int = 15) -> str:
    cleaned = re.sub(r"^[\U0001F300-\U0001FAFF\U00002702-\U000027B0\U0000FE00-\U0000FE0F\U0000200D\s*#]+", "", text)
    match = re.search(r"[.!?]\s", cleaned)
    sentence = cleaned[: match.end()].strip() if match else cleaned[:200]
    words = sentence.split()
    return " ".join(words[:max_words]) + "..." if len(words) > max_words else sentence


def _classify_hook(text: str) -> str:
    first = text[:300].lower()
    if re.match(r"^[\U0001F300-\U0001FAFF\s]*(?:is your|are you|ready for|what if|why are|not sure|your child)", first):
        return "question"
    if "?" in first[:150]:
        return "question"
    for pat in [r"\d+\s*points?", r"\d+%", r"\d+\s*million", r"\d+x\b", r"4\.0\s", r"1[0-4]\d{2}", r"\$\d"]:
        if re.search(pat, first):
            return "statistic"
    checks = [
        ("fear_based", ["don't miss", "before it's too late", "running out of time", "losing confidence", "missing out", "don't let"]),
        ("social_proof", ["thousands", "millions", "real students", "join", "editor's choice", "rated"]),
        ("aspiration", ["picture this", "imagine", "higher sat", "game changer", "dream school", "scholarship"]),
        ("pain_point", ["struggling", "stuck", "frustrated", "can't keep up", "something's off"]),
        ("direct_offer", ["find a", "get all", "expert tutors", "test prep,", "prep package"]),
        ("pattern_interrupt", ["hot take", "secret", "certified procrastinator", "attention parents"]),
        ("curiosity_gap", ["something about", "here's what", "won't tell you", "most don't know"]),
        ("storytelling", ["day in the life", "her sat score", "my daughter", "look at your calendar"]),
    ]
    for label, words in checks:
        if any(w in first for w in words):
            return label
    return "direct_offer"


def _classify_body(text: str) -> str:
    lower = text.lower()
    if bool(re.search(r"#\w+", text)) and bool(re.search(r"@\w+", text)):
        return "ugc-endorsement"
    if any(w in lower for w in ["my daughter", "real students are saying"]):
        return "testimonial-benefit"
    if len(re.findall(r"\d+[%+x]|\d+\s*points?|\$\d", lower)) >= 2:
        return "stat-context-offer"
    if "before" in lower and "after" in lower:
        return "problem-agitate-solution"
    if any(w in lower for w in ["thousands of parents", "4 million", "editor's choice"]):
        return "social-proof-offer"
    return "feature-benefit-cta"


def _classify_cta(text: str) -> str:
    lower = text.lower()
    checks = [
        ("free-trial", ["free sat strategy call", "free resources", "14-day test drive", "free"]),
        ("urgency", ["closes soon", "now's the time", "start this week", "don't wait"]),
        ("learn-more", ["learn more", "link in bio", "click", "explore", "see how"]),
        ("sign-up", ["sign up", "get matched", "book a", "get started"]),
    ]
    for label, words in checks:
        if any(w in lower for w in words):
            return label
    return "implicit"


def _classify_emotion(text: str) -> str:
    lower = text.lower()
    checks = [
        ("parental_anxiety", ["your child", "your teen", "parent", "college admissions"]),
        ("fomo", ["missing out", "slipping away", "don't let", "before it's too late"]),
        ("aspiration", ["dream school", "game changer", "acceptance letter", "scholarship"]),
        ("empowerment", ["you deserve", "your way", "built around you", "we can help", "personalized"]),
        ("student_stress", ["stuck", "struggling", "stacking up", "can't keep up"]),
    ]
    for label, words in checks:
        if any(w in lower for w in words):
            return label
    return "empowerment"


@router.post("/upload")
async def upload_competitive_ads(
    file: UploadFile = File(...),
    competitor_name: str = Form(...),
) -> dict[str, Any]:
    """Upload and classify competitor ads from Meta Ad Library JSON export."""
    content = await file.read()
    try:
        uploaded_ads = json.loads(content)
    except json.JSONDecodeError:
        return {"error": "Invalid JSON file"}

    if not isinstance(uploaded_ads, list):
        return {"error": "Expected a JSON array of ad objects"}

    competitor_key = competitor_name.strip().lower().replace(" ", "_")

    # Load existing raw ads for dedup
    raw_path = RAW_ADS_DIR / f"{competitor_key}.json"
    existing_ads: list[dict] = []
    existing_texts: set[str] = set()
    if raw_path.exists():
        try:
            with open(raw_path) as f:
                existing_ads = json.load(f)
            for ad in existing_ads:
                txt = ad.get("Ad Text Content", "")
                if txt:
                    existing_texts.add(_normalize_text(txt))
        except Exception:
            pass

    # Load existing patterns
    patterns_data: dict[str, Any] = {"pattern_records": [], "metadata": {}, "competitor_summaries": {}}
    if PATTERNS_PATH.exists():
        try:
            with open(PATTERNS_PATH) as f:
                patterns_data = json.load(f)
        except Exception:
            pass

    new_ads: list[dict] = []
    new_patterns: list[dict] = []
    duplicates = 0

    for ad in uploaded_ads:
        text = ad.get("Ad Text Content", "").strip()
        if not text or len(text) < 10:
            continue

        if _normalize_text(text) in existing_texts:
            duplicates += 1
            continue

        existing_texts.add(_normalize_text(text))
        new_ads.append(ad)

        hook = _get_first_sentence(text)
        new_patterns.append({
            "ad_library_id": ad.get("Ad Library ID", ""),
            "competitor": competitor_name.strip(),
            "hook": hook,
            "hook_type": _classify_hook(text),
            "body_pattern": _classify_body(text),
            "cta_style": _classify_cta(text),
            "emotional_register": _classify_emotion(text),
        })

    # Save new raw ads
    if new_ads:
        RAW_ADS_DIR.mkdir(parents=True, exist_ok=True)
        all_ads = existing_ads + new_ads
        with open(raw_path, "w") as f:
            json.dump(all_ads, f, indent=2)

    # Update patterns.json
    if new_patterns:
        patterns_data.setdefault("pattern_records", []).extend(new_patterns)
        meta = patterns_data.setdefault("metadata", {})
        meta["total_ads_scraped"] = meta.get("total_ads_scraped", 0) + len(new_ads)
        meta["unique_ads"] = meta.get("unique_ads", 0) + len(new_ads)
        comps = meta.setdefault("competitors", [])
        if competitor_name.strip() not in comps:
            comps.append(competitor_name.strip())

        # Update competitor summary
        hooks = [p["hook_type"] for p in new_patterns]
        emotions = [p["emotional_register"] for p in new_patterns]
        summaries = patterns_data.setdefault("competitor_summaries", {})
        summaries[competitor_name.strip()] = {
            "strategy": f"Analyzed {len(new_patterns)} ads",
            "dominant_hooks": list(set(hooks))[:5],
            "emotional_levers": list(set(emotions))[:5],
            "gaps": "See gap analysis for details",
        }

        with open(PATTERNS_PATH, "w") as f:
            json.dump(patterns_data, f, indent=2)

    # Update module-level COMPETITORS list
    if competitor_key not in COMPETITORS:
        COMPETITORS.append(competitor_key)

    return {
        "ads_parsed": len(uploaded_ads),
        "ads_new": len(new_ads),
        "ads_duplicate": duplicates,
        "patterns_added": len(new_patterns),
        "competitor": competitor_name.strip(),
    }
