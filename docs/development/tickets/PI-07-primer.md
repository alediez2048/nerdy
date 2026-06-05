# PI-07 Primer

**Source plan:** [`PI-PLAN.md`](PI-PLAN.md) — sliced from the ticket section below.
**Phase plan:** [`PI-00-phase-plan.md`](PI-00-phase-plan.md)

**Status:** ⏳ Not started

---

# Ticket PI-07: Dashboard `/variants` endpoint v2 branch

**Goal:** `/api/sessions/{id}/ads/{ad_id}/variants` returns the new v2 shape when the session's ledger has `MediaEvaluation` events. Falls back to the existing v1 shape for legacy sessions.

**Files:**
- Modify: `app/api/routes/dashboard.py` — `get_ad_variants` function (lines ~243-367)
- Test: `tests/test_app/test_ad_variants_route_v2.py` (new)

- [ ] **Step 1: Write the failing test** — `tests/test_app/test_ad_variants_route_v2.py`:

```python
"""PI-07: /variants endpoint emits v2 shape when MediaEvaluation events exist."""
from __future__ import annotations

import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient


def _write_v2_ledger(p: Path, ad_id: str) -> None:
    """Write a ledger with 3 MediaEvaluation events for one ad."""
    events = []
    for i, (variant, composite) in enumerate(
        [("anchor", 80.0), ("tone_shift", 60.0), ("composition_shift", 45.0)]
    ):
        events.append({
            "event_type": "ImageGenerated",
            "ad_id": ad_id, "model_used": "nano-banana-pro-preview",
            "inputs": {"variant_type": variant},
            "outputs": {"image_path": f"out/{ad_id}_{variant}.png"},
        })
        events.append({
            "event_type": "MediaEvaluation",
            "ad_id": ad_id, "brief_id": "brief_001",
            "cycle_number": 0, "action": f"media_eval_{variant}",
            "tokens_consumed": 1500, "model_used": "gemini-2.5-flash",
            "seed": "0",
            "inputs": {"variant_type": variant, "media_type": "image"},
            "outputs": {
                "schema_version": "v2", "media_type": "image",
                "media_path": f"out/{ad_id}_{variant}.png",
                "dimensions": {
                    "thumb_stop_potential": {"score": 8, "weight": 0.20, "rationale": "rich"},
                    "mobile_legibility": {"score": 7, "weight": 0.15, "rationale": "ok"},
                },
                "penalty_gates": {
                    "has_ai_artifacts": {"triggered": False, "rationale": "clean"},
                },
                "raw_score": composite/100.0, "penalty_multiplier": 1.0,
                "composite_score": composite,
            },
        })
    p.write_text("\n".join(json.dumps(e) for e in events))


def test_variants_endpoint_returns_v2_shape(tmp_path, monkeypatch, auth_test_client):
    ledger = tmp_path / "ledger.jsonl"
    _write_v2_ledger(ledger, ad_id="ad_X")
    # Test fixture should make a session row with this ledger_path; reuse the
    # existing pattern from test_ad_variants_route.py.
    client, session_id, ad_id = auth_test_client(ledger)
    resp = client.get(f"/api/sessions/{session_id}/ads/{ad_id}/variants")
    assert resp.status_code == 200
    body = resp.json()
    assert body["schema_version"] == "v2"
    assert len(body["variants"]) == 3
    # Winner is the highest composite
    winners = [v for v in body["variants"] if v["is_winner"]]
    assert len(winners) == 1
    assert winners[0]["variant_type"] == "anchor"
    # Per-variant dimensions present
    assert "dimensions" in winners[0]
    assert "thumb_stop_potential" in winners[0]["dimensions"]
    # Loser carries rejection_reason
    losers = [v for v in body["variants"] if not v["is_winner"]]
    assert all("rejection_reason" in v for v in losers)
    # Selection criteria reflect v2 formula
    assert "raw_score" in body["selection_criteria"]["formula"] or "composite" in body["selection_criteria"]["formula"].lower()


def test_variants_endpoint_falls_back_to_v1_for_legacy(tmp_path, auth_test_client):
    """A legacy session with ImageEvaluated events still returns the v1 shape."""
    ledger = tmp_path / "ledger.jsonl"
    # Write a v1-style ImageEvaluated event
    events = [
        {"event_type": "ImageGenerated", "ad_id": "ad_Y",
         "model_used": "gemini-2.5-flash-image",
         "inputs": {"variant_type": "anchor"},
         "outputs": {"image_path": "out/ad_Y_anchor.png"}},
        {"event_type": "ImageEvaluated", "ad_id": "ad_Y",
         "inputs": {"variant_type": "anchor"},
         "outputs": {"attribute_pass_pct": 0.8, "coherence_avg": 0.5, "composite_score": 0.35}},
    ]
    ledger.write_text("\n".join(json.dumps(e) for e in events))
    client, session_id, ad_id = auth_test_client(ledger, ad_id="ad_Y")
    resp = client.get(f"/api/sessions/{session_id}/ads/{ad_id}/variants")
    assert resp.status_code == 200
    body = resp.json()
    assert body["schema_version"] == "v1"
    assert "composite_score" in body["variants"][0]
```

- [ ] **Step 2: Run, expect failure**

```
.venv/bin/python -m pytest tests/test_app/test_ad_variants_route_v2.py -v
```

- [ ] **Step 3: Rewrite `get_ad_variants`** in `app/api/routes/dashboard.py` — at the top of the function (just after the session ownership check), branch on event type:

```python
@router.get("/{session_id}/ads/{ad_id}/variants")
def get_ad_variants(
    session_id: str, ad_id: str,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user)],
) -> dict[str, Any]:
    init_db()
    session = _get_session(db, session_id, user["user_id"])
    ledger_path = session.ledger_path
    if not ledger_path or not Path(ledger_path).exists():
        raise HTTPException(status_code=404, detail="Session ledger not found")

    from iterate.ledger_reader import read_dicts_filtered
    events = read_dicts_filtered(ledger_path, ad_id=ad_id)
    if not events:
        raise HTTPException(status_code=404, detail="No events for that ad")

    has_v2 = any(e.get("event_type") == "MediaEvaluation" for e in events)
    if has_v2:
        return _build_variants_v2(session_id, ad_id, events)
    return _build_variants_v1(session_id, ad_id, events)  # extracted from old body
```

Then implement `_build_variants_v2`:

```python
def _build_variants_v2(session_id: str, ad_id: str, events: list[dict[str, Any]]) -> dict[str, Any]:
    """v2 shape: per-variant dimensions, gates, raw_score, winner/rejection reasons."""
    rate_per_call = {
        "nano-banana-pro-preview": 0.13,
        "gemini-2.5-flash-image": 0.035,
        "gemini-2.0-flash-preview-image-generation": 0.13,
    }
    variants_by_type: dict[str, dict[str, Any]] = {}
    for ev in events:
        if ev.get("event_type") == "ImageGenerated":
            vt = (ev.get("inputs") or {}).get("variant_type", "")
            outs = ev.get("outputs") or {}
            path = outs.get("image_path", "")
            variants_by_type.setdefault(vt, {})
            variants_by_type[vt]["image_path"] = path or None
            variants_by_type[vt]["image_url"] = (
                f"/api/images/{Path(path).name}" if path else None
            )
            variants_by_type[vt]["model_used"] = ev.get("model_used", "")
            variants_by_type[vt]["predicted_cost_usd"] = rate_per_call.get(ev.get("model_used", ""), 0.0)
        elif ev.get("event_type") == "MediaEvaluation":
            vt = (ev.get("inputs") or {}).get("variant_type", "")
            outs = ev.get("outputs") or {}
            variants_by_type.setdefault(vt, {})
            variants_by_type[vt].update({
                "variant_type": vt,
                "media_type": outs.get("media_type", "image"),
                "dimensions": outs.get("dimensions", {}),
                "penalty_gates": outs.get("penalty_gates", {}),
                "raw_score": outs.get("raw_score", 0.0),
                "penalty_multiplier": outs.get("penalty_multiplier", 1.0),
                "composite_score": outs.get("composite_score", 0.0),
            })

    variants = list(variants_by_type.values())
    if not variants:
        raise HTTPException(status_code=404, detail="No image variants for that ad")

    winner = max(variants, key=lambda v: v.get("composite_score", 0))
    for v in variants:
        v["is_winner"] = (v is winner)
        v.setdefault("variant_type", "unknown")
        v.setdefault("composite_score", 0.0)

    # winner_reason: top 2 distinguishing dimensions
    losers = [v for v in variants if not v["is_winner"]]
    if losers:
        dim_names = list(winner.get("dimensions", {}).keys())
        deltas = {}
        for d in dim_names:
            w_score = winner["dimensions"][d].get("score", 0)
            loser_mean = sum(lo["dimensions"].get(d, {}).get("score", 0) for lo in losers) / len(losers)
            deltas[d] = w_score - loser_mean
        top2 = sorted(deltas, key=deltas.get, reverse=True)[:2]
        winner_reason = {
            "composite_score": winner["composite_score"],
            "distinguishing_dimensions": [
                {"dimension": d, "delta_vs_mean": round(deltas[d], 2)} for d in top2
            ],
        }
        for lo in losers:
            dim_deltas = {
                d: lo["dimensions"].get(d, {}).get("score", 0)
                   - winner["dimensions"].get(d, {}).get("score", 0)
                for d in dim_names
            }
            worst = min(dim_deltas, key=dim_deltas.get)
            lo["rejection_reason"] = {
                "composite_delta": round(lo["composite_score"] - winner["composite_score"], 2),
                "worst_dimension": worst,
                "worst_dimension_delta": round(dim_deltas[worst], 2),
                "worst_dimension_rationale": lo["dimensions"].get(worst, {}).get("rationale", ""),
            }
    else:
        winner_reason = None

    return {
        "session_id": session_id, "ad_id": ad_id,
        "schema_version": "v2",
        "selection_criteria": {
            "formula": "composite = sum(weight * dim_score) / 10 * penalty_mult * 100",
            "winner_variant_type": winner["variant_type"],
            "winner_composite_score": winner["composite_score"],
        },
        "winner_reason": winner_reason,
        "variants": variants,
    }
```

Refactor the existing body into `_build_variants_v1` (no logic changes — wrap the current code in that helper and have it return the same dict plus `"schema_version": "v1"`).

- [ ] **Step 4: Run new tests, verify PASS**

```
.venv/bin/python -m pytest tests/test_app/test_ad_variants_route_v2.py tests/test_app/test_ad_variants_route.py -v
```

Expected: existing v1 tests still pass + 2 new v2 tests pass.

- [ ] **Step 5: Commit**

```
git add app/api/routes/dashboard.py tests/test_app/test_ad_variants_route_v2.py
git commit -m "feat(PI-07): /variants endpoint v2 branch with dimensions + rationales"
```

---
