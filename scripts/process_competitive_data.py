#!/usr/bin/env python3
"""
Process raw competitive ad data from Meta Ad Library into structured outputs.

Reads raw JSON files from data/competitive/raw/, deduplicates, classifies,
and produces:
  1. data/competitive/patterns.json — competitive pattern analysis
  2. data/reference_ads.json — reference ad set for pipeline calibration

Usage:
    python scripts/process_competitive_data.py
"""

import json
import re
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "competitive" / "raw"
PATTERNS_OUT = PROJECT_ROOT / "data" / "competitive" / "patterns.json"
REFERENCE_OUT = PROJECT_ROOT / "data" / "reference_ads.json"

RAW_FILES = {
    "chegg": RAW_DIR / "chegg.json",
    "wyzant": RAW_DIR / "wyzant.json",
    "kaplan": RAW_DIR / "kaplan.json",
    "varsity_tutors": RAW_DIR / "varsity_tutors.json",
}

# Canonical competitor names
COMPETITOR_NAMES = {
    "Chegg": "Chegg",
    "Wyzant": "Wyzant",
    "Kaplan College Prep": "Kaplan",
    "Varsity Tutors": "Varsity Tutors",
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_raw_ads():
    """Load all raw ad files and return flat list of ads with source info."""
    all_ads = []
    for key, path in RAW_FILES.items():
        with open(path, "r", encoding="utf-8") as f:
            ads = json.load(f)
        for ad in ads:
            ad["_source_file"] = key
        all_ads.extend(ads)
    return all_ads


def normalize_text(text: str) -> str:
    """Normalize whitespace for dedup comparison."""
    return re.sub(r"\s+", " ", text.strip())


def strip_hashtags_and_mentions(text: str) -> str:
    """Remove hashtags and @mentions for word counting."""
    cleaned = re.sub(r"#\w+", "", text)
    cleaned = re.sub(r"@\w+", "", cleaned)
    return cleaned.strip()


def word_count_real(text: str) -> int:
    """Count words excluding hashtags and mentions."""
    cleaned = strip_hashtags_and_mentions(text)
    return len(cleaned.split())


def has_long_legal(text: str) -> bool:
    """Detect ads with long legal disclaimers."""
    legal_signals = [
        "terms and conditions",
        "This offer requires activation",
        "not valid for existing",
        "has no cash value",
        "is not transferable",
        "may not be combined",
        "See additional terms",
    ]
    count = sum(1 for s in legal_signals if s.lower() in text.lower())
    return count >= 2


def is_valid_competitor(advertiser_name: str) -> bool:
    """Check if the advertiser is one of our four target competitors."""
    return advertiser_name in COMPETITOR_NAMES


def get_first_sentence(text: str, max_words: int = 15) -> str:
    """Extract the first sentence / hook, up to max_words."""
    # Strip leading emoji and whitespace
    cleaned = re.sub(r"^[\U0001F300-\U0001FAFF\U00002702-\U000027B0\U0000FE00-\U0000FE0F\U0000200D\s*#]+", "", text)
    # Find first sentence boundary
    match = re.search(r"[.!?]\s", cleaned)
    if match:
        sentence = cleaned[: match.end()].strip()
    else:
        sentence = cleaned[:200]  # fallback

    words = sentence.split()
    if len(words) > max_words:
        return " ".join(words[:max_words]) + "..."
    return sentence


# ---------------------------------------------------------------------------
# Classification functions
# ---------------------------------------------------------------------------

def classify_hook(text: str) -> str:
    """Classify the hook type based on the first sentence/phrase."""
    first = text[:300].lower()

    # Question hooks
    if re.match(r"^[\U0001F300-\U0001FAFF\s]*(?:is your|are you|ready for|what if|why are|not sure|your child)", first):
        return "question"
    if "?" in first[:150]:
        return "question"

    # Statistic hooks
    stat_patterns = [r"\d+\s*points?", r"\d+%", r"\d+\s*million", r"\d+x\b", r"4\.0\s", r"1[0-4]\d{2}", r"\$\d"]
    for pat in stat_patterns:
        if re.search(pat, first):
            return "statistic"

    # Fear-based
    fear_words = ["don't miss", "before it's too late", "running out of time",
                  "losing confidence", "missing out", "slipping away", "panic",
                  "don't let", "crash out", "bombing"]
    for fw in fear_words:
        if fw in first:
            return "fear_based"

    # Metaphor
    metaphor_phrases = ["deserted island", "fumbling", "dark", "puzzle piece",
                        "baseball field", "football", "stacking up", "crash"]
    for mp in metaphor_phrases:
        if mp in first:
            return "metaphor"

    # Social proof
    social_proof_words = ["thousands", "millions", "real students", "join",
                          "they spilled", "parents who trust", "parents who use",
                          "test prep insight", "editor's choice", "rated"]
    for sp in social_proof_words:
        if sp in first:
            return "social_proof"

    # Aspiration
    aspiration_words = ["picture this", "imagine", "higher sat", "game changer",
                        "acceptance letter", "dream school", "scholarship",
                        "future career", "jumpstart"]
    for aw in aspiration_words:
        if aw in first:
            return "aspiration"

    # Pain point
    pain_words = ["struggling", "stuck", "frustrated", "can't keep up",
                  "something's off", "disconnect", "hard", "tough",
                  "out of hand", "crash"]
    for pw in pain_words:
        if pw in first:
            return "pain_point"

    # Direct offer
    offer_words = ["find a", "get all", "get a college", "expert tutors",
                   "test prep,", "from essay help", "prep package",
                   "cover every base", "no juggling"]
    for ow in offer_words:
        if ow in first:
            return "direct_offer"

    # Pattern interrupt
    interrupt_words = ["hot take", "secret", "certified procrastinator",
                       "attention parents", "here's what most", "harsh truth"]
    for iw in interrupt_words:
        if iw in first:
            return "pattern_interrupt"

    # Curiosity gap
    curiosity_words = ["something about", "here's what", "won't tell you",
                       "most don't know", "most parents don't"]
    for cw in curiosity_words:
        if cw in first:
            return "curiosity_gap"

    # Storytelling
    story_words = ["day in the life", "her sat score", "sarah", "jennifer",
                   "my daughter", "look at your calendar"]
    for sw in story_words:
        if sw in first:
            return "storytelling"

    return "direct_offer"  # default


def classify_body_pattern(text: str) -> str:
    """Classify the overall body structure."""
    lower = text.lower()
    has_hashtags = bool(re.search(r"#\w+", text))
    has_mentions = bool(re.search(r"@\w+", text))

    # UGC
    if has_hashtags and has_mentions and ("ad" in lower[:50] or "#ad" in lower or "#sponsored" in lower):
        return "ugc-endorsement"

    # Testimonial
    if any(w in lower for w in ["my daughter", "sarah's mom", "jennifer's daughter",
                                 "real students are saying", "they spilled"]):
        return "testimonial-benefit"

    # Stat-context-offer
    stat_count = len(re.findall(r"\d+[%+x]|\d+\s*points?|\$\d", lower))
    if stat_count >= 2:
        return "stat-context-offer"

    # Problem-agitate-solution (before/after pattern or problem then solution)
    if "before" in lower and "after" in lower:
        return "problem-agitate-solution"
    if any(w in lower for w in ["here's what changes", "that's where", "we can help",
                                 "here's what we do"]):
        return "problem-agitate-solution"

    # Social-proof-offer
    if any(w in lower for w in ["thousands of parents", "4 million", "test prep insight",
                                 "editor's choice"]):
        return "social-proof-offer"

    # Comparison
    if any(w in lower for w in ["princeton review", "khan academy", "other kids",
                                 "while other", "local tutors"]):
        return "comparison"

    # Feature-benefit-CTA (step-by-step, homework help, specific features)
    if any(w in lower for w in ["step-by-step", "homework help", "flashcard",
                                 "built-in", "diagnostic"]):
        return "feature-benefit-cta"

    return "feature-benefit-cta"  # default


def classify_cta(text: str) -> str:
    """Classify the CTA style."""
    lower = text.lower()

    # Free trial
    if any(w in lower for w in ["free sat strategy call", "free resources",
                                 "14-day test drive", "free"]):
        return "free-trial"

    # Urgency
    if any(w in lower for w in ["march registration closes", "before march",
                                 "may 2nd", "8 weeks away", "closes soon",
                                 "now's the time", "start this week",
                                 "don't let", "don't wait"]):
        return "urgency"

    # Social proof CTA
    if any(w in lower for w in ["join thousands", "see what real students"]):
        return "social-proof-cta"

    # Learn more
    if any(w in lower for w in ["learn more", "link in bio", "click",
                                 "fill out the quick form", "explore",
                                 "find out why", "see how"]):
        return "learn-more"

    # Sign up
    if any(w in lower for w in ["sign up", "get matched", "book a",
                                 "reserve your", "get started"]):
        return "sign-up"

    return "implicit"


def classify_emotional_register(text: str) -> str:
    """Classify the emotional register."""
    lower = text.lower()

    has_hashtags = bool(re.search(r"#\w+", text))
    has_mentions = bool(re.search(r"@\w+", text))

    # UGC/casual
    if has_hashtags and has_mentions and len(text) < 300:
        return "casual_friendly"

    # Parental anxiety
    parent_anxiety = ["your child", "your teen", "parent", "your son",
                      "your daughter", "your kid", "scholarship money",
                      "college admissions"]
    if sum(1 for w in parent_anxiety if w in lower) >= 2:
        return "parental_anxiety"

    # FOMO
    if any(w in lower for w in ["missing out", "slipping away", "don't let",
                                 "before it's too late", "losing"]):
        return "fomo"

    # Competitive
    if any(w in lower for w in ["2.6x", "10x", "better results", "advantage",
                                 "while other", "princeton review charges"]):
        return "competitive"

    # Aspiration
    if any(w in lower for w in ["dream school", "game changer", "acceptance letter",
                                 "scholarship", "confident", "future career",
                                 "picture this"]):
        return "aspiration"

    # Empowerment
    if any(w in lower for w in ["you deserve", "your way", "built around you",
                                 "support for real learners", "we can help",
                                 "keep up", "personalized"]):
        return "empowerment"

    # Relief
    if any(w in lower for w in ["no more", "makes it easy", "stress less",
                                 "cancel anytime", "makes sense"]):
        return "relief"

    # Student stress
    if any(w in lower for w in ["stuck", "struggling", "stacking up",
                                 "can't keep up", "crash out", "overwhelm"]):
        return "student_stress"

    # Curiosity
    if any(w in lower for w in ["here's what", "something about", "find out"]):
        return "curiosity"

    return "empowerment"  # default


def classify_audience(text: str) -> str:
    """Classify primary audience."""
    lower = text.lower()

    parent_signals = ["your child", "your teen", "your kid", "your son",
                      "your daughter", "parents", "your child's", "give your teen"]
    student_signals = ["#college", "#finals", "#exams", "@chegg",
                       "#collegestudent", "#studytok", "your classes",
                       "your homework", "your study", "new semester",
                       "you deserve", "your scores", "your passion",
                       "day in the life"]

    parent_count = sum(1 for w in parent_signals if w in lower)
    student_count = sum(1 for w in student_signals if w in lower)

    if parent_count > 0 and student_count > 0:
        return "both"
    if parent_count > 0:
        return "parents"
    if student_count > 0:
        return "students"

    # Heuristics for ambiguous
    if any(w in lower for w in ["high school", "college prep", "admissions",
                                 "sat prep", "sat tutor"]):
        return "both"

    return "both"  # default


def classify_tone(text: str) -> str:
    """Classify the tone of the ad."""
    lower = text.lower()

    has_hashtags = bool(re.search(r"#\w+", text))
    has_mentions = bool(re.search(r"@\w+", text))

    # UGC authentic
    if has_hashtags and has_mentions and ("#ad" in lower or "#sponsored" in lower):
        return "ugc_authentic"

    # Data driven
    stat_count = len(re.findall(r"\d+[%+x]|\d+\s*points?|\$\d", lower))
    if stat_count >= 3:
        return "data_driven"

    # Urgent direct
    if any(w in lower for w in ["now's the time", "march registration",
                                 "8 weeks away", "don't wait", "don't let",
                                 "start this week", "today"]):
        return "urgent_direct"

    # Premium exclusive
    if any(w in lower for w in ["official prep partner", "partners directly",
                                 "editor's choice", "test prep insight",
                                 "only kaplan"]):
        return "premium_exclusive"

    # Empathetic supportive
    if any(w in lower for w in ["we understand", "we can help", "that's where",
                                 "you're not alone", "it's not about intelligence",
                                 "your child isn't failing"]):
        return "empathetic_supportive"

    # Casual friendly
    if any(w in lower for w in ["hot take", "new semester", "new you",
                                 "dive headfirst", "keep your child's creativity"]):
        return "casual_friendly"

    # Authoritative reassuring
    if any(w in lower for w in ["expert", "proven", "guaranteed", "trust",
                                 "real human tutor", "1-on-1", "personalized"]):
        return "authoritative_reassuring"

    return "authoritative_reassuring"  # default


def build_tags(ad: dict, hook_type: str, audience: str) -> list:
    """Build tags list for a pattern record."""
    tags = [audience, hook_type]
    lower = ad["Ad Text Content"].lower()

    theme_map = {
        "sat_prep": ["sat", "digital sat"],
        "act_prep": ["act"],
        "ap_prep": ["ap calc", "ap chem", "ap class"],
        "homework_help": ["homework"],
        "college_admissions": ["college admissions", "acceptance letter", "college apps"],
        "test_prep": ["test prep", "mcat", "nclex", "bar exam"],
        "tutoring": ["tutor", "1-on-1", "1:1"],
        "study_tools": ["study tools", "flashcard", "step-by-step"],
        "ugc": ["#ad", "#sponsored", "@chegg"],
        "affordability": ["$30", "$349", "affordable"],
        "score_improvement": ["points", "score", "improvement"],
    }

    for theme, keywords in theme_map.items():
        if any(kw in lower for kw in keywords):
            tags.append(theme)

    return tags[:6]  # cap at 6 tags


# ---------------------------------------------------------------------------
# Selection logic — pick diverse ads per competitor
# ---------------------------------------------------------------------------

def select_diverse_ads(ads_by_competitor: dict, target_per_competitor: dict) -> list:
    """
    Pick diverse ads per competitor, prioritizing variety in hook types.
    """
    selected = []

    for competitor, target_count in target_per_competitor.items():
        pool = ads_by_competitor.get(competitor, [])
        if not pool:
            continue

        # Group by hook_type
        by_hook = {}
        for ad in pool:
            ht = ad["_hook_type"]
            by_hook.setdefault(ht, []).append(ad)

        picked = []
        # Round-robin through hook types
        hook_types = list(by_hook.keys())
        idx = 0
        while len(picked) < target_count and any(by_hook.values()):
            ht = hook_types[idx % len(hook_types)]
            if by_hook.get(ht):
                picked.append(by_hook[ht].pop(0))
            idx += 1
            # Remove empty buckets
            hook_types = [h for h in hook_types if by_hook.get(h)]
            if not hook_types:
                break

        selected.extend(picked)

    return selected


# ---------------------------------------------------------------------------
# Main processing
# ---------------------------------------------------------------------------

def main():
    # 1. Load all raw ads
    all_ads = load_raw_ads()
    total_scraped = len(all_ads)
    print(f"Total raw ads loaded: {total_scraped}")

    # 2. Filter to target competitors only
    all_ads = [a for a in all_ads if is_valid_competitor(a["Advertiser Name"])]
    print(f"After filtering to target competitors: {len(all_ads)}")

    # 3. Deduplicate by normalized ad text
    seen_texts = {}
    unique_ads = []
    for ad in all_ads:
        text = ad.get("Ad Text Content", "").strip()
        if not text:
            continue
        norm = normalize_text(text)
        if norm not in seen_texts:
            seen_texts[norm] = ad
            unique_ads.append(ad)
    print(f"Unique ads after dedup: {len(unique_ads)}")

    # 4. Filter out low-quality ads
    filtered_ads = []
    for ad in unique_ads:
        text = ad["Ad Text Content"]
        wc = word_count_real(text)
        if wc < 10:
            continue
        if has_long_legal(text):
            continue
        filtered_ads.append(ad)
    print(f"After filtering (min words, legal): {len(filtered_ads)}")

    # 5. Classify all ads
    for ad in filtered_ads:
        text = ad["Ad Text Content"]
        ad["_hook_type"] = classify_hook(text)
        ad["_body_pattern"] = classify_body_pattern(text)
        ad["_cta_style"] = classify_cta(text)
        ad["_emotional_register"] = classify_emotional_register(text)
        ad["_primary_audience"] = classify_audience(text)
        ad["_tone"] = classify_tone(text)
        ad["_word_count"] = word_count_real(text)
        ad["_has_hashtags"] = bool(re.search(r"#\w+", text))
        ad["_has_mentions"] = bool(re.search(r"@\w+", text))
        ad["_is_ugc"] = ad["_has_hashtags"] and ad["_has_mentions"]
        ad["_competitor"] = COMPETITOR_NAMES.get(ad["Advertiser Name"], ad["Advertiser Name"])

    # Group by competitor
    by_competitor = {}
    for ad in filtered_ads:
        comp = ad["_competitor"]
        by_competitor.setdefault(comp, []).append(ad)

    for comp, ads in by_competitor.items():
        print(f"  {comp}: {len(ads)} unique filtered ads")

    # 6. Select diverse ads for patterns.json (~8-10 per competitor, ~40 total)
    target_patterns = {
        "Chegg": 10,
        "Wyzant": 10,
        "Kaplan": 10,
        "Varsity Tutors": 10,
    }
    pattern_ads = select_diverse_ads(by_competitor, target_patterns)
    print(f"\nSelected {len(pattern_ads)} ads for patterns.json")

    # 7. Build pattern records
    pattern_records = []
    counters = {}
    for ad in pattern_ads:
        comp = ad["_competitor"]
        counters[comp] = counters.get(comp, 0) + 1
        comp_abbrev = comp.lower().replace(" ", "_")

        text = ad["Ad Text Content"]
        record = {
            "pattern_id": f"comp_{comp_abbrev}_{counters[comp]:02d}",
            "ad_library_id": ad["Ad Library ID"],
            "competitor": comp,
            "captured_date": ad["Started Running Date"],
            "ad_text": text,
            "hook_type": ad["_hook_type"],
            "hook_text": get_first_sentence(text),
            "body_pattern": ad["_body_pattern"],
            "cta_style": ad["_cta_style"],
            "emotional_register": ad["_emotional_register"],
            "primary_audience": ad["_primary_audience"],
            "tone": ad["_tone"],
            "word_count": ad["_word_count"],
            "has_hashtags": ad["_has_hashtags"],
            "has_mentions": ad["_has_mentions"],
            "is_ugc_creator": ad["_is_ugc"],
            "tags": build_tags(ad, ad["_hook_type"], ad["_primary_audience"]),
        }
        pattern_records.append(record)

    # 8. Build competitor summaries
    def build_summary(comp_ads):
        hooks = {}
        emotions = {}
        for a in comp_ads:
            hooks[a["_hook_type"]] = hooks.get(a["_hook_type"], 0) + 1
            emotions[a["_emotional_register"]] = emotions.get(a["_emotional_register"], 0) + 1

        dominant_hooks = sorted(hooks, key=hooks.get, reverse=True)[:3]
        emotional_levers = sorted(emotions, key=emotions.get, reverse=True)[:3]
        return dominant_hooks, emotional_levers

    competitor_summaries = {}
    strategy_map = {
        "Chegg": {
            "strategy": "Heavy UGC creator partnerships with student ambassadors. Positions as everyday study companion with step-by-step help. Mix of polished brand ads and authentic creator content. Targets college students directly.",
            "gaps": "No parent-facing messaging. No SAT/ACT test prep positioning. Limited data-driven claims about outcomes.",
        },
        "Wyzant": {
            "strategy": "Marketplace positioning emphasizing tutor choice and flexibility (no packages required). Broad subject coverage from K-12 to professional exams. Heavy reliance on social proof (thousands of parents, 4M reviews).",
            "gaps": "Very repetitive copy across ads. No outcome data or score improvement claims. No emotional storytelling or urgency.",
        },
        "Kaplan": {
            "strategy": "Authority-based positioning as official ACT partner. Bundled college prep packages at accessible price ($30/month). Mix of test prep and college admissions advising. Third-party credibility via Test Prep Insight ratings.",
            "gaps": "No 1-on-1 tutoring messaging. No specific score improvement testimonials. Limited emotional hooks — mostly rational/authority-based.",
        },
        "Varsity Tutors": {
            "strategy": "Aggressive direct-response with long-form copy targeting parents. Data-heavy claims (2.6x improvement, 200+ points). Strong digital SAT differentiation (paper vs laptop). Comparison positioning against Khan Academy, Princeton Review. High urgency around test dates.",
            "gaps": "Very long ads may cause scroll-past. Heavy repetition of same claims across variants. Limited brand warmth or student voice.",
        },
    }

    for comp in ["Chegg", "Wyzant", "Kaplan", "Varsity Tutors"]:
        comp_ads = by_competitor.get(comp, [])
        dominant_hooks, emotional_levers = build_summary(comp_ads)
        competitor_summaries[comp] = {
            "strategy": strategy_map[comp]["strategy"],
            "dominant_hooks": dominant_hooks,
            "emotional_levers": emotional_levers,
            "gaps": strategy_map[comp]["gaps"],
        }

    # 9. Build patterns.json
    patterns_output = {
        "metadata": {
            "version": "2.0",
            "created": "2026-03-14",
            "source": "Meta Ad Library via Thunderbit scraper (P0-09)",
            "purpose": "Real competitive patterns for pipeline differentiation (R2-Q2)",
            "competitors": ["Chegg", "Wyzant", "Kaplan College Prep", "Varsity Tutors"],
            "total_ads_scraped": total_scraped,
            "unique_ads": len(unique_ads),
            "pattern_records": len(pattern_records),
        },
        "patterns": pattern_records,
        "competitor_summaries": competitor_summaries,
    }

    PATTERNS_OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(PATTERNS_OUT, "w", encoding="utf-8") as f:
        json.dump(patterns_output, f, indent=2, ensure_ascii=False)
    print(f"\nWrote {PATTERNS_OUT}")

    # -------------------------------------------------------------------
    # 10. Build reference_ads.json
    # -------------------------------------------------------------------
    # Select ~15 VT, ~8-10 each from competitors
    target_ref = {
        "Varsity Tutors": 15,
        "Chegg": 9,
        "Wyzant": 9,
        "Kaplan": 9,
    }
    ref_ads_selected = select_diverse_ads(
        # Use fresh copy of by_competitor since select_diverse_ads mutates
        {k: list(v) for k, v in by_competitor.items()},
        target_ref,
    )
    print(f"\nSelected {len(ref_ads_selected)} ads for reference_ads.json")

    brand_abbrev_map = {
        "Chegg": "chg",
        "Wyzant": "wyz",
        "Kaplan": "kap",
        "Varsity Tutors": "vt",
    }

    ref_counters = {}
    ref_records = []
    for ad in ref_ads_selected:
        comp = ad["_competitor"]
        ref_counters[comp] = ref_counters.get(comp, 0) + 1
        abbrev = brand_abbrev_map.get(comp, comp[:3].lower())

        ref_records.append({
            "ad_id": f"ref_{abbrev}_{ref_counters[comp]:02d}",
            "primary_text": ad["Ad Text Content"],
            "headline": "not_available",
            "description": "not_available",
            "cta_button": "not_available",
            "source": "meta_ad_library",
            "brand": ad["Advertiser Name"],
            "audience_guess": ad["_primary_audience"],
            "captured_date": ad["Started Running Date"],
        })

    reference_output = {
        "metadata": {
            "version": "2.0",
            "created": "2026-03-14",
            "collection_methodology": "Real ads scraped from Meta Ad Library using Thunderbit (P0-09). Replaces synthetic v1.0.",
            "sources": ["meta_ad_library"],
            "total_count": len(ref_records),
        },
        "ads": ref_records,
    }

    REFERENCE_OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(REFERENCE_OUT, "w", encoding="utf-8") as f:
        json.dump(reference_output, f, indent=2, ensure_ascii=False)
    print(f"Wrote {REFERENCE_OUT}")

    # Print summary stats
    print("\n--- Pattern Records Summary ---")
    hook_dist = {}
    for r in pattern_records:
        hook_dist[r["hook_type"]] = hook_dist.get(r["hook_type"], 0) + 1
    for h, c in sorted(hook_dist.items(), key=lambda x: -x[1]):
        print(f"  {h}: {c}")

    print("\n--- Reference Ads by Brand ---")
    ref_brand_dist = {}
    for r in ref_records:
        ref_brand_dist[r["brand"]] = ref_brand_dist.get(r["brand"], 0) + 1
    for b, c in sorted(ref_brand_dist.items(), key=lambda x: -x[1]):
        print(f"  {b}: {c}")


if __name__ == "__main__":
    main()
