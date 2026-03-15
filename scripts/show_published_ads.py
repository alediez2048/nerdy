"""Show all published ads with scores and rationales."""
import json

with open("data/ledger.jsonl") as f:
    events = [json.loads(line) for line in f if line.strip()]

# Get published ad IDs
published_ids = {e["ad_id"] for e in events if e.get("event_type") == "AdPublished"}

# Get the latest evaluation for each published ad
evals = {}
for e in events:
    if e.get("event_type") == "AdEvaluated" and e.get("ad_id") in published_ids:
        evals[e["ad_id"]] = e  # last eval wins

# Get the generation event for each published ad
gens = {}
for e in events:
    if e.get("event_type") == "AdGenerated" and e.get("ad_id") in published_ids:
        gens[e["ad_id"]] = e

print(f"=== {len(published_ids)} PUBLISHED ADS ===\n")

for i, ad_id in enumerate(sorted(published_ids), 1):
    gen = gens.get(ad_id, {})
    ev = evals.get(ad_id, {})
    outputs = gen.get("outputs", {})
    scores = ev.get("scores", ev.get("outputs", {}).get("scores", {}))

    print(f"--- Ad {i}: {ad_id} ---")

    # Ad copy
    if isinstance(outputs, dict):
        print(f"PRIMARY TEXT: {outputs.get('primary_text', 'N/A')}")
        print(f"HEADLINE:     {outputs.get('headline', 'N/A')}")
        print(f"DESCRIPTION:  {outputs.get('description', 'N/A')}")
        print(f"CTA:          {outputs.get('cta_button', 'N/A')}")

    # Scores
    if scores:
        print("\nSCORES:")
        for dim in ["clarity", "value_proposition", "cta", "brand_voice", "emotional_resonance"]:
            if dim in scores:
                s = scores[dim]
                if isinstance(s, dict):
                    print(f"  {dim}: {s.get('score', 'N/A')}/10 — {s.get('rationale', '')[:80]}")
                else:
                    print(f"  {dim}: {s}/10")

    # Aggregate
    aggregate = ev.get("outputs", {}).get("aggregate_score") or ev.get("aggregate_score")
    if aggregate:
        print(f"  AGGREGATE: {aggregate}/10")

    print()
