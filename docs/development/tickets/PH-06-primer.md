# PH-06 Primer: ImageModelRouter Extraction

**For:** New Agent session
**Project:** Ad-Ops-Autopilot
**Date:** May 2026
**Phase plan:** [`PH-00-phase-plan.md`](PH-00-phase-plan.md)
**Depends on:** None (independent — can run in parallel with PH-01..PH-05)
**Branch:** `feature/PH-06-image-router`

---

## What Is This Ticket?

`generate/image_generator.py:_call_image_api` has **four sibling callers in the same file**:
- `generate_variants`
- `generate_extra_ratios`
- `generate_image_routed`
- `generate_variants_routed`

Each one re-derives the "which model do we use here?" decision (Nano Banana Pro for the anchor variant, Nano Banana 2 for siblings, with a budget threshold that falls everything back to NB2). The routing logic is inline in a 50-line function that also builds prompts and handles API errors — testing routing requires mocking the API.

---

## What This Ticket Must Accomplish

### Goal

A pure-function **ImageModelRouter** module:

```python
choice: ModelChoice = image_model_router.choose_model(
    variant_role: VariantRole,    # ANCHOR | SIBLING | ASPECT_RATIO_EXTRA
    budget_remaining_usd: float,
    persona: Persona | None,
) -> ModelChoice
# ModelChoice = {model_name, predicted_cost_usd, rationale}
```

`image_generator.py` calls the router *before* calling the API. The four sibling functions all funnel through this one router. Routing is unit-testable without any API calls or mocks.

A bonus side-effect: `predicted_cost_usd` surfaces *before* the spend, enabling future budget-gate features.

### Deliverables Checklist

#### A. Design (grilling session — BEFORE implementation)
- [ ] Run `gitnexus_context({name: "_call_image_api"})` to confirm the four wrappers and their differences
- [ ] Decide the `VariantRole` enum values
- [ ] Decide whether persona affects model choice today (it may not — the audit said budget is the only current signal)
- [ ] Decide where rates live — config.yaml only (consistent with PH-02 decision)

#### B. Implementation
- [ ] Create `generate/image_model_router.py` with the router + `ModelChoice` dataclass + `VariantRole` enum
- [ ] Update each of the 4 wrappers in `image_generator.py` to: (1) compute `VariantRole`, (2) call the router, (3) pass `choice.model_name` to `_call_image_api`
- [ ] `_call_image_api` no longer makes routing decisions — it just calls the named model

#### C. Testing
- [ ] All existing image-generation tests pass
- [ ] New unit tests on the router: anchor → NB Pro; sibling → NB2; low budget → NB2 across the board; rationale string non-empty
- [ ] No new mocks of the Gemini image API in the router tests

---

## Acceptance Criteria

- [ ] `generate/image_model_router.py` exists with pure-function `choose_model`
- [ ] `_call_image_api` contains no `if model == ... else ...` routing logic
- [ ] Router tests run in <1 second without any network mocks
- [ ] Image generation behavior is unchanged for a fixture session (same models picked for same inputs)
- [ ] DEVLOG entry committed

---

## Key Files

| File | Action |
|------|--------|
| `generate/image_model_router.py` | **NEW** |
| `generate/image_generator.py` | Wrappers call router; `_call_image_api` simplifies |
| `generate/ab_image_variants.py` | If it has duplicate routing, migrate it too |
| `data/config.yaml` | Rate map confirmed as source of truth |
| `tests/test_generation/test_image_model_router.py` | **NEW** — pure unit tests |

---

## Out of Scope for PH-06

- Changing model choices (e.g. switching anchor from NB Pro to a new model)
- A user-facing budget cap
- Per-persona routing (out unless grilling concludes it's already implicitly there)

---

## Verification Before Merge

Standard gate. Smallest blast radius of all PH tickets — quick to verify.
