"""Quick ledger sanity check — run after a pipeline run."""
import json

with open("data/ledger.jsonl") as f:
    events = [json.loads(line) for line in f if line.strip()]

types = {}
for e in events:
    t = e.get("event_type", "unknown")
    types[t] = types.get(t, 0) + 1

for t, c in sorted(types.items()):
    print(f"{t}: {c}")

print(f"---\nTotal events: {len(events)}")
