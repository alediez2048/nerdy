#!/usr/bin/env python3
"""One-time backfill: data/cost_manifest.json for historical session cost display.

Allocates (billing reference − global ledger) across sessions by heuristic weight.
Run from repo root: python scripts/backfill_session_costs.py
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    from evaluate.cost_reporter import (
        BILLING_REFERENCE_TOTAL_USD,
        compute_event_cost,
        compute_standalone_global_ledger_cost_usd,
        get_fal_veo3_per_call_usd,
    )
    from iterate.ledger import read_events

    sessions_dir = ROOT / "data" / "sessions"
    global_cost = compute_standalone_global_ledger_cost_usd(str(ROOT / "data" / "ledger.jsonl"))
    remaining = max(0.0, BILLING_REFERENCE_TOTAL_USD - global_cost)

    raw_weights: dict[str, float] = {}
    ledger_usd: dict[str, float] = {}

    for ledger_path in sorted(sessions_dir.glob("*/ledger.jsonl")):
        sid = ledger_path.parent.name
        events = read_events(str(ledger_path))
        raw = sum(compute_event_cost(e) for e in events)
        ledger_usd[sid] = round(raw, 6)

        vg = sum(1 for e in events if e.get("event_type") == "VideoGenerated")
        ig = sum(1 for e in events if e.get("event_type") == "ImageGenerated")
        ag = sum(1 for e in events if e.get("event_type") == "AdGenerated")
        ae = sum(1 for e in events if e.get("event_type") == "AdEvaluated")
        # Weight video rows by Fal Veo3 per-call (config), not legacy $0.28 invoice average
        veo3 = get_fal_veo3_per_call_usd()
        heuristic = (
            vg * veo3
            + ig * 0.13
            + ag * 0.45
            + ae * 0.03
        )
        raw_weights[sid] = max(heuristic, 0.01)

    total_w = sum(raw_weights.values())
    manifest_sessions: dict[str, dict[str, object]] = {}
    if total_w > 0 and remaining > 0:
        for sid, w in raw_weights.items():
            allocated = (w / total_w) * remaining
            manifest_sessions[sid] = {
                "estimated_cost_usd": round(allocated, 4),
                "method": "backfill_estimate",
                "ledger_usd_at_backfill": ledger_usd[sid],
                "weight": round(w, 4),
            }
    else:
        for sid in raw_weights:
            manifest_sessions[sid] = {
                "estimated_cost_usd": ledger_usd[sid],
                "method": "ledger_only",
                "ledger_usd_at_backfill": ledger_usd[sid],
            }

    out = {
        "billing_reference_total_usd": BILLING_REFERENCE_TOTAL_USD,
        "global_ledger_usd": round(global_cost, 4),
        "allocated_session_pool_usd": round(remaining, 4),
        "sessions": manifest_sessions,
    }

    out_path = ROOT / "data" / "cost_manifest.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
        f.write("\n")
    print(f"Wrote {out_path} ({len(manifest_sessions)} sessions)")


if __name__ == "__main__":
    main()
