"""Checkpoint-resume pipeline state (P0-08, R3-Q2).

Reads the ledger to determine which ads have completed which stages.
Enables resume from last checkpoint without duplicate work.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from iterate.ledger import read_events


@dataclass
class PipelineState:
    """Reconstructed pipeline state from ledger."""

    generated_ids: set[str] = field(default_factory=set)
    evaluated_pairs: set[tuple[str, int]] = field(default_factory=set)
    regenerated_pairs: set[tuple[str, int]] = field(default_factory=set)
    published_ids: set[str] = field(default_factory=set)
    discarded_ids: set[str] = field(default_factory=set)
    started_brief_ids: set[str] = field(default_factory=set)


def get_pipeline_state(ledger_path: str) -> PipelineState:
    """Read ledger and determine pipeline state.

    Returns:
        PipelineState with:
        - generated_ids: ad_ids with AdGenerated
        - evaluated_pairs: (ad_id, cycle_number) with AdEvaluated
        - regenerated_pairs: (ad_id, cycle_number) with AdRegenerated
        - published_ids: ad_ids with AdPublished
        - discarded_ids: ad_ids with AdDiscarded
        - started_brief_ids: brief_ids that appear in any event
    """
    events = read_events(ledger_path)
    state = PipelineState()

    for ev in events:
        event_type = ev.get("event_type")
        ad_id = ev.get("ad_id")
        brief_id = ev.get("brief_id")
        cycle = ev.get("cycle_number", 0)

        if brief_id is not None:
            state.started_brief_ids.add(str(brief_id))

        if ad_id is None:
            continue

        ad_id = str(ad_id)

        if event_type == "AdGenerated":
            state.generated_ids.add(ad_id)
        elif event_type == "AdEvaluated":
            state.evaluated_pairs.add((ad_id, cycle))
        elif event_type == "AdRegenerated":
            state.regenerated_pairs.add((ad_id, cycle))
        elif event_type == "AdPublished":
            state.published_ids.add(ad_id)
        elif event_type == "AdDiscarded":
            state.discarded_ids.add(ad_id)

    return state


def get_last_checkpoint(ledger_path: str) -> str | None:
    """Return the most recent checkpoint_id, or None if ledger is empty."""
    events = read_events(ledger_path)
    if not events:
        return None
    return events[-1].get("checkpoint_id")


def should_skip_ad(
    state: PipelineState,
    ad_id: str,
    stage: str,
    cycle_number: int = 0,
) -> bool:
    """Return True if the ad has already completed this stage (prevents double-processing).

    Stages: generate, evaluate, regenerate, publish
    """
    if stage == "generate":
        return ad_id in state.generated_ids
    if stage == "evaluate":
        return (ad_id, cycle_number) in state.evaluated_pairs
    if stage == "regenerate":
        return (ad_id, cycle_number) in state.regenerated_pairs
    if stage == "publish":
        return ad_id in state.published_ids or ad_id in state.discarded_ids
    return False
