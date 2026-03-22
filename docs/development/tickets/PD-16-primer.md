# PD-16: Self-Healing Pipeline — Targeted Regeneration + Brief Adherence Feedback

## Goal
Wire the existing iterate/ modules into the active pipeline so the system detects quality drops, diagnoses the weakest dimension, applies targeted fixes, and re-evaluates — all without human intervention. Then add brief adherence feedback so the pipeline also self-corrects when ads drift from the session's creative brief.

## Why This Matters
- Assignment rubric: +7 bonus points for "self-healing / automatic quality improvement"
- Currently the pipeline is single-shot: generate → evaluate → publish or discard. No regeneration, no diagnosis, no learning.
- All the iterate/ components exist (built in P1) but aren't wired in — PD-06 identified this gap.

## What We Have (Built but Not Wired)

| Module | Purpose | Status |
|--------|---------|--------|
| `iterate/quality_ratchet.py` | Threshold only goes up across batches | Built, not wired |
| `iterate/pareto_selection.py` | Prevents one dimension from collapsing during regen | Built, not wired |
| `generate/model_router.py` | Routes to Flash (cheap) or Pro (expensive) by score | Built, routing decision logged but not enforced |
| `iterate/brief_mutation.py` | Modifies briefs when stuck after N cycles | Built, not wired |
| `evaluate/brief_adherence.py` | Scores ads against session brief (PD-12) | Built and wired for scoring, not yet used for feedback |

## Level 1: Targeted Regeneration Loop (~3 hrs)

### What Changes in `iterate/batch_processor.py`

Current flow (single-shot):
```
expand_brief → generate_ad → evaluate → route → publish/discard
```

New flow (self-healing):
```
expand_brief → generate_ad → evaluate → score too low?
  ├─ YES (cycle 1-2): diagnose weakest dim → targeted regen → re-evaluate
  ├─ YES (cycle 3): escalate to Pro model → regen → re-evaluate
  ├─ YES (cycle 4+): mutate brief → start fresh → evaluate
  └─ NO: publish
```

### Implementation

```python
# batch_processor.py — replace single-shot evaluation block

max_cycles = config.get("max_cycles", 3)
quality_threshold = config.get("text_threshold", 7.0)

for cycle in range(max_cycles):
    if cycle == 0:
        ad = generate_ad(expanded, seed=brief_seed, creative_brief=creative_brief)
    elif cycle < 3:
        # Targeted regeneration: inject weakness-specific guidance
        from iterate.regen_strategies import build_regen_prompt
        ad = generate_ad(
            expanded,
            seed=brief_seed + cycle,
            creative_brief=creative_brief,
            regen_guidance=build_regen_prompt(weakest_dim, prev_rationale),
        )
    else:
        # Brief mutation: rework the brief entirely
        from iterate.brief_mutation import mutate_brief
        expanded = mutate_brief(expanded, weakest_dim)
        ad = generate_ad(expanded, seed=brief_seed + cycle, creative_brief=creative_brief)

    evaluation = evaluate_ad(ad.to_evaluator_input(), ...)

    log_event(ledger_path, {
        "event_type": "AdEvaluated",
        "cycle_number": cycle,
        ...
    })

    if evaluation.aggregate_score >= quality_threshold:
        # Passes — publish
        break

    # Diagnose: find weakest dimension
    weakest_dim = min(evaluation.dimension_scores, key=evaluation.dimension_scores.get)
    prev_rationale = evaluation.rationales.get(weakest_dim, "")

    log_event(ledger_path, {
        "event_type": "AdRegenerated",
        "cycle_number": cycle,
        "outputs": {
            "weakest_dimension": weakest_dim,
            "score_before": evaluation.aggregate_score,
            "strategy": "targeted_regen" if cycle < 3 else "brief_mutation",
        },
    })

# After loop: publish or discard
if evaluation.aggregate_score >= quality_threshold:
    publish(ad)
else:
    discard(ad)
```

### Quality Ratchet Integration

```python
from iterate.quality_ratchet import QualityRatchet

# Initialize per-batch
ratchet = QualityRatchet(window=config.get("ratchet_window", 5))

# After each batch
ratchet.update(batch_avg_score)
effective_threshold = max(quality_threshold, ratchet.threshold)
```

The ratchet ensures the publish threshold never drops — if the pipeline starts producing 8.0+ ads consistently, it won't accept a 7.1 anymore.

### Pareto Selection Integration

```python
from iterate.pareto_selection import select_pareto_optimal

# During regeneration — prevent dimension collapse
# Don't accept a regen that improves CTA from 4→8 but drops Brand Voice from 7→3
if not select_pareto_optimal(prev_scores, new_scores):
    # New scores are dominated — the regen made things worse
    # Revert to previous version
    ad = prev_ad
```

### Model Escalation

```python
from generate.model_router import route_ad

routing = route_ad(ad_id, evaluation.aggregate_score, ...)

if routing.decision == "escalate" and cycle >= 2:
    # Actually use Pro model for regeneration
    ad = generate_ad(expanded, model="gemini-2.0-pro", ...)
```

Currently `route_ad` returns the decision but the pipeline ignores it and always uses Flash. This wires the escalation.

## Level 2: Brief Adherence Feedback (~2 hrs)

### What Changes

After the copy quality loop, run brief adherence scoring. If adherence is low on specific dimensions, inject corrective guidance and regenerate.

### Implementation

```python
# After ad passes copy quality threshold

from evaluate.brief_adherence import score_brief_adherence

adherence = score_brief_adherence(ad.to_evaluator_input(), config, ad_id=ad.ad_id)

# Check for critical adherence failures
needs_adherence_fix = False
fix_guidance = []

if adherence.scores.get("audience_match", 10) < 5:
    fix_guidance.append(
        f"CRITICAL: Ad is not targeting {config.get('audience')}. "
        f"Use language appropriate for {config.get('audience')}."
    )
    needs_adherence_fix = True

if adherence.scores.get("persona_fit", 10) < 5:
    fix_guidance.append(
        f"CRITICAL: Tone does not match {config.get('persona')} persona. "
        f"Adjust emotional register to match this persona's needs."
    )
    needs_adherence_fix = True

if adherence.scores.get("message_delivery", 10) < 4:
    key_msg = config.get("key_message", "")
    if key_msg:
        fix_guidance.append(
            f"CRITICAL: Key message '{key_msg}' is not present in the ad. "
            f"The key message must be central to the copy."
        )
        needs_adherence_fix = True

if needs_adherence_fix:
    # Regenerate with adherence guidance injected
    ad = generate_ad(
        expanded,
        seed=brief_seed + 100,  # different seed for adherence regen
        creative_brief=creative_brief,
        regen_guidance="\n".join(fix_guidance),
    )
    # Re-evaluate both quality and adherence
    evaluation = evaluate_ad(ad.to_evaluator_input(), ...)
    adherence = score_brief_adherence(ad.to_evaluator_input(), config, ad_id=ad.ad_id)

    log_event(ledger_path, {
        "event_type": "AdherenceRegenerated",
        "ad_id": ad.ad_id,
        "outputs": {
            "fix_guidance": fix_guidance,
            "adherence_before": original_adherence.scores,
            "adherence_after": adherence.scores,
        },
    })
```

### Adherence Thresholds

| Dimension | Threshold | Action if below |
|-----------|-----------|----------------|
| Audience Match | < 5 | Inject audience-specific language guidance |
| Goal Alignment | < 5 | Inject goal-specific CTA/tone guidance |
| Persona Fit | < 5 | Inject persona description and emotional register |
| Message Delivery | < 4 | Force key message into prompt |
| Format Adherence | < 5 | Re-inject creative brief format constraints |

Only trigger adherence regen when scores are critically low (< 5, not < 7) — we don't want to burn tokens on marginal cases.

## New Ledger Events

| Event | When | Data |
|-------|------|------|
| `AdRegenerated` | After each regen cycle | weakest_dim, score_before, strategy, cycle_number |
| `AdherenceRegenerated` | After adherence fix | fix_guidance, scores before/after |
| `RatchetUpdated` | After each batch | threshold_before, threshold_after, batch_avg |
| `ModelEscalated` | When switching to Pro | reason, score_at_escalation |

## Dashboard Impact

The existing Iteration Cycles tab already reads `AdEvaluated` events with before/after scores — the self-healing loop will populate this tab with real regeneration data instead of the empty state most sessions show today.

New metrics visible:
- **Regen cycles per ad** — how many attempts before publish
- **Which dimensions trigger regen most** — identifies systematic weaknesses
- **Escalation rate** — how often Pro model is needed
- **Adherence fix rate** — how often brief drift is detected and corrected

## Files Modified

| File | Change |
|------|--------|
| `iterate/batch_processor.py` | Replace single-shot with regeneration loop |
| `iterate/feedback_loop.py` | **New** — orchestrator tying ratchet + pareto + routing + adherence |
| `generate/ad_generator.py` | Accept `regen_guidance` parameter |
| `app/workers/tasks/pipeline_task.py` | Pass `max_cycles` config through |

## Files Used (Already Built, Just Wired In)

| File | What it does |
|------|-------------|
| `iterate/quality_ratchet.py` | Monotonically increasing threshold |
| `iterate/pareto_selection.py` | Prevent dimension collapse |
| `generate/model_router.py` | Flash → Pro escalation |
| `iterate/brief_mutation.py` | Rework stuck briefs |
| `evaluate/brief_adherence.py` | Brief compliance scoring (PD-12) |

## Acceptance Criteria

### Level 1
- [ ] Ads scoring below 7.0 are regenerated (up to `max_cycles` times)
- [ ] Weakest dimension is identified and logged per regen cycle
- [ ] Quality ratchet tracks real batch averages (no more hardcoded 7.0)
- [ ] Model escalation fires when score is in improvable range after 2+ cycles
- [ ] Pareto check prevents dimension collapse during regen
- [ ] Iteration Cycles dashboard tab populates with real before/after data
- [ ] Existing tests still pass

### Level 2
- [ ] Brief adherence runs after quality passes
- [ ] Critical adherence failures (< 5) trigger targeted regen with guidance
- [ ] `AdherenceRegenerated` events logged with before/after scores
- [ ] Adherence regen limited to 1 additional cycle (no infinite loops)
- [ ] Works for both image and video pipeline paths

## Dependencies
- PD-12 (brief adherence scorer) — already complete
- PD-06 (pipeline iteration wiring) — PD-16 supersedes PD-06 by including adherence feedback

## Estimate
- Level 1: ~3 hours
- Level 2: ~2 hours
- **Total: ~5 hours**

## Status: ⏳ NOT STARTED
