"""LLM-assisted first-pass scoring for reference ads.

Uses Gemini to suggest quality_label and human_scores for each ad
in data/reference_ads.json. Outputs labeled version for human review.
"""

from __future__ import annotations

import json
import os
import re
import time

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

REFERENCE_ADS_PATH = "data/reference_ads.json"
OUTPUT_PATH = "data/reference_ads_labeled.json"

DIMENSIONS = ["clarity", "value_proposition", "cta", "brand_voice", "emotional_resonance"]

LABELING_PROMPT = """You are an expert ad copy evaluator for education/tutoring ads on Meta (Facebook/Instagram).

Score this ad on 5 dimensions (1-10 scale). Use the FULL scale:
- 9-10: Exceptional — scroll-stopping hook, specific differentiation, strong emotion
- 7-8: Good — clear message, decent hook, some differentiation
- 5-6: Mediocre — functional but forgettable, generic claims
- 3-4: Weak — unclear, no hook, vague value prop
- 1-2: Terrible — confusing, off-brand, or counterproductive

Also assign a quality_label:
- "excellent" = aggregate 7.5+ AND no dimension below 5
- "poor" = aggregate below 5.0 OR any dimension below 3
- "neutral" = everything else

IMPORTANT context: We are evaluating these as SAT test prep ads for Varsity Tutors' brand voice (empowering, knowledgeable, approachable, results-focused). Competitor ads should be scored on general ad quality but will naturally score lower on brand_voice since they're not VT ads.

AD TO SCORE:
Brand: {brand}
Target audience: {audience}
Primary text: {primary_text}
Headline: {headline}
CTA: {cta}

Output ONLY valid JSON (no markdown, no code fences):
{{
  "clarity": {{"score": <float>, "rationale": "<1 sentence>"}},
  "value_proposition": {{"score": <float>, "rationale": "<1 sentence>"}},
  "cta": {{"score": <float>, "rationale": "<1 sentence>"}},
  "brand_voice": {{"score": <float>, "rationale": "<1 sentence>"}},
  "emotional_resonance": {{"score": <float>, "rationale": "<1 sentence>"}},
  "quality_label": "<excellent|neutral|poor>",
  "aggregate": <float>
}}
"""


def score_ad(client: genai.Client, ad: dict) -> dict:
    """Score a single ad using Gemini."""
    prompt = LABELING_PROMPT.format(
        brand=ad.get("brand", "unknown"),
        audience=ad.get("audience_guess", "unknown"),
        primary_text=ad.get("primary_text", ""),
        headline=ad.get("headline", "not_available"),
        cta=ad.get("cta_button", "not_available"),
    )

    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.2,
            max_output_tokens=1024,
        ),
    )

    text = (response.text or "").strip()
    # Strip code fences if present
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if match:
        text = match.group(1).strip()

    return json.loads(text)


def main() -> None:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set")

    client = genai.Client(api_key=api_key)

    with open(REFERENCE_ADS_PATH) as f:
        data = json.load(f)

    ads = data["ads"]
    print(f"Scoring {len(ads)} ads...\n")

    for i, ad in enumerate(ads):
        ad_id = ad["ad_id"]
        print(f"[{i+1}/{len(ads)}] {ad_id} ({ad['brand']})...", end=" ", flush=True)

        try:
            result = score_ad(client, ad)

            # Build human_scores dict
            human_scores = {}
            for dim in DIMENSIONS:
                score_val = result.get(dim, {}).get("score", 5.0)
                if isinstance(score_val, int):
                    score_val = float(score_val)
                human_scores[dim] = score_val

            ad["human_scores"] = human_scores
            ad["quality_label"] = result.get("quality_label", "neutral")
            ad["ai_aggregate"] = result.get("aggregate", 0.0)
            ad["ai_rationales"] = {
                dim: result.get(dim, {}).get("rationale", "") for dim in DIMENSIONS
            }

            label = ad["quality_label"]
            agg = ad["ai_aggregate"]
            print(f"{label} (agg: {agg})")

        except Exception as e:
            print(f"ERROR: {e}")
            ad["human_scores"] = {d: 5.0 for d in DIMENSIONS}
            ad["quality_label"] = "neutral"
            ad["ai_aggregate"] = 5.0
            ad["ai_rationales"] = {}

        # Rate limit: small delay between calls
        if i < len(ads) - 1:
            time.sleep(1.0)

    # Update metadata
    data["metadata"]["labeling"] = {
        "method": "gemini-2.0-flash first-pass, pending human review",
        "labeled_date": "2026-03-14",
        "status": "ai_draft",
    }

    with open(OUTPUT_PATH, "w") as f:
        json.dump(data, f, indent=2)

    # Summary
    labels = [ad.get("quality_label", "neutral") for ad in ads]
    print(f"\n--- Summary ---")
    print(f"Excellent: {labels.count('excellent')}")
    print(f"Neutral:   {labels.count('neutral')}")
    print(f"Poor:      {labels.count('poor')}")
    print(f"\nOutput: {OUTPUT_PATH}")
    print("Review and adjust scores, then copy to data/reference_ads.json")


if __name__ == "__main__":
    main()
