"""Narrated pipeline replay — chronological decision walkthrough (P4-07, R2-Q10).

Reads the append-only ledger and produces a human-readable narrative of
every decision the system made. Failures are highlighted, not hidden.
Makes system thinking legible for reviewers.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from iterate.ledger import read_events

logger = logging.getLogger(__name__)


@dataclass
class ReplayEvent:
    """A single narrated event."""

    timestamp: str
    event_type: str
    ad_id: str
    narrative: str
    details: dict
    is_failure: bool


@dataclass
class BatchNarrative:
    """Grouped events for one batch."""

    batch_num: int
    events: list[ReplayEvent]
    summary: str
    failures: list[ReplayEvent] = field(default_factory=list)


@dataclass
class PipelineReplay:
    """Full pipeline replay."""

    batches: list[BatchNarrative]
    total_summary: str
    failures: list[ReplayEvent]
    token_summary: dict


# --- Event Parsing ---

_EVENT_PARSERS: dict[str, str] = {}  # populated by parse_event


def parse_event(event: dict) -> ReplayEvent:
    """Convert a raw ledger event to a narrated ReplayEvent.

    Args:
        event: Raw ledger event dict.

    Returns:
        ReplayEvent with human-readable narrative.
    """
    etype = event.get("event_type", "Unknown")
    ad_id = event.get("ad_id", "unknown")
    ts = event.get("timestamp", "")
    inputs = event.get("inputs", {})
    outputs = event.get("outputs", {})
    tokens = event.get("tokens_consumed", 0)
    cycle = event.get("cycle_number", 0)
    is_failure = False

    if etype == "BriefExpanded":
        brief_id = event.get("brief_id", "unknown")
        audience = inputs.get("audience", "unknown")
        goal = inputs.get("campaign_goal", "unknown")
        narrative = f"Brief {brief_id} expanded for {audience} audience ({goal} goal)"

    elif etype == "AdGenerated":
        hook = inputs.get("hook_type", outputs.get("hook_type", ""))
        narrative = f"Ad {ad_id} generated (cycle {cycle})"
        if hook:
            narrative += f", hook: {hook}"
        if tokens:
            narrative += f", {tokens:,} tokens"

    elif etype == "AdEvaluated":
        score = outputs.get("aggregate_score", 0)
        scores = outputs.get("scores", {})
        dims = []
        for d in ("clarity", "value_proposition", "cta", "brand_voice", "emotional_resonance"):
            v = scores.get(d, "?")
            if isinstance(v, dict):
                v = v.get("score", "?")
            dims.append(f"{d[:3]}={v}")
        narrative = f"Ad {ad_id} scored {score}/10 ({', '.join(dims)})"

    elif etype == "AdRegenerated":
        weakest = outputs.get("weakest_dimension", inputs.get("weakest_dimension", "unknown"))
        narrative = f"Ad {ad_id} regenerated (attempt {cycle}): {weakest} targeted for improvement"

    elif etype == "AdPublished":
        score = inputs.get("aggregate_score", outputs.get("aggregate_score", "?"))
        narrative = f"Ad {ad_id} published with score {score}/10"

    elif etype == "AdDiscarded":
        reason = outputs.get("reason", outputs.get("decision", "below threshold"))
        narrative = f"[!] Ad {ad_id} discarded — {reason}"
        is_failure = True

    elif etype == "BatchCompleted":
        batch_num = outputs.get("batch_num", inputs.get("batch_num", "?"))
        gen = outputs.get("generated", 0)
        pub = outputs.get("published", 0)
        disc = outputs.get("discarded", 0)
        regen = outputs.get("regenerated", 0)
        narrative = f"Batch {batch_num} complete: {gen} generated, {pub} published, {disc} discarded, {regen} regenerated"

    elif etype == "VideoGenerated":
        variant = inputs.get("variant_id", "unknown")
        duration = outputs.get("duration", 0)
        narrative = f"Video generated for ad {ad_id}: {variant}, {duration}s"

    elif etype == "VideoBlocked":
        narrative = f"[DEGRADED] Ad {ad_id} video blocked — falling back to image-only"
        is_failure = True

    elif etype == "AgentFailed":
        agent = outputs.get("agent_name", inputs.get("agent", "unknown"))
        error = outputs.get("error", "unknown error")
        narrative = f"[FAILURE] {agent} failed on ad {ad_id}: {error}"
        is_failure = True

    elif etype == "SelfHealingTriggered":
        action = outputs.get("action_taken", "unknown action")
        narrative = f"[HEALING] Quality drift detected — {action}"

    elif etype == "ExplorationTriggered":
        strategy = outputs.get("strategy", inputs.get("strategy", "unknown"))
        narrative = f"[EXPLORE] Plateau detected — trying {strategy}"

    elif etype == "PatternPromoted":
        ptype = outputs.get("pattern_type", "unknown")
        pval = outputs.get("pattern_value", "unknown")
        rate = outputs.get("win_rate", 0)
        narrative = f"[LEARN] Pattern promoted: {ptype}={pval} (win rate: {rate}%)"

    elif etype == "BriefMutated":
        dim = inputs.get("weakest_dimension", "unknown")
        narrative = f"Brief mutated for ad {ad_id}: targeting {dim}"

    else:
        narrative = f"{etype}: ad {ad_id}"

    return ReplayEvent(
        timestamp=ts,
        event_type=etype,
        ad_id=ad_id,
        narrative=narrative,
        details={**inputs, **outputs},
        is_failure=is_failure,
    )


# --- Batch Grouping ---


def group_events_by_batch(events: list[ReplayEvent]) -> list[BatchNarrative]:
    """Group replay events into batches using BatchCompleted markers.

    Args:
        events: List of parsed ReplayEvents in chronological order.

    Returns:
        List of BatchNarrative, one per batch.
    """
    batches: list[BatchNarrative] = []
    current_events: list[ReplayEvent] = []
    batch_num = 1

    for event in events:
        current_events.append(event)

        if event.event_type == "BatchCompleted":
            failures = [e for e in current_events if e.is_failure]
            gen = event.details.get("generated", 0)
            pub = event.details.get("published", 0)
            summary = f"Batch {batch_num}: {gen} generated, {pub} published"

            batches.append(BatchNarrative(
                batch_num=batch_num,
                events=list(current_events),
                summary=summary,
                failures=failures,
            ))
            current_events = []
            batch_num += 1

    # Remaining events without a BatchCompleted marker
    if current_events:
        failures = [e for e in current_events if e.is_failure]
        batches.append(BatchNarrative(
            batch_num=batch_num,
            events=current_events,
            summary=f"Batch {batch_num} (in progress): {len(current_events)} events",
            failures=failures,
        ))

    return batches


# --- Full Replay ---


def generate_replay(ledger_path: str) -> PipelineReplay:
    """Generate a full pipeline replay from a ledger file.

    Args:
        ledger_path: Path to the JSONL ledger.

    Returns:
        PipelineReplay with batches, summary, and failures.
    """
    raw_events = read_events(ledger_path)
    parsed = [parse_event(e) for e in raw_events]
    batches = group_events_by_batch(parsed)

    all_failures = [e for e in parsed if e.is_failure]

    # Compute totals
    total_tokens = sum(e.get("tokens_consumed", 0) for e in raw_events)
    total_generated = sum(1 for e in raw_events if e.get("event_type") == "AdGenerated")
    total_published = sum(1 for e in raw_events if e.get("event_type") == "AdPublished")
    rate = round(total_published / max(total_generated, 1) * 100, 1)
    total_summary = (
        f"Pipeline complete: {total_generated} ads across {len(batches)} batches. "
        f"{total_published} published ({rate}%). "
        f"{len(all_failures)} failures. "
        f"{total_tokens:,} tokens consumed."
    )

    return PipelineReplay(
        batches=batches,
        total_summary=total_summary,
        failures=all_failures,
        token_summary={"total_tokens": total_tokens},
    )


# --- Text Formatters ---


def format_replay_text(replay: PipelineReplay) -> str:
    """Format replay as readable plain text.

    Args:
        replay: PipelineReplay to format.

    Returns:
        Plain text string.
    """
    lines: list[str] = ["=== Pipeline Replay ===", ""]

    for batch in replay.batches:
        lines.append(f"--- Batch {batch.batch_num} ---")
        for event in batch.events:
            ts = event.timestamp[:19] if event.timestamp else ""
            prefix = "[!] " if event.is_failure else ""
            lines.append(f"[{ts}] {prefix}{event.narrative}")
        lines.append(f"\n{batch.summary}")
        lines.append("")

    if replay.failures:
        lines.append("--- Failures ---")
        for f in replay.failures:
            lines.append(f"[!] {f.narrative}")
        lines.append("")

    lines.append(f"=== {replay.total_summary} ===")
    return "\n".join(lines)


def format_replay_markdown(replay: PipelineReplay) -> str:
    """Format replay as Markdown.

    Args:
        replay: PipelineReplay to format.

    Returns:
        Markdown string.
    """
    lines: list[str] = ["# Pipeline Replay", ""]

    for batch in replay.batches:
        lines.append(f"## Batch {batch.batch_num}")
        lines.append("")
        for event in batch.events:
            ts = event.timestamp[:19] if event.timestamp else ""
            if event.is_failure:
                lines.append(f"- **[!]** `{ts}` {event.narrative}")
            else:
                lines.append(f"- `{ts}` {event.narrative}")
        lines.append("")
        lines.append(f"**{batch.summary}**")
        lines.append("")

    if replay.failures:
        lines.append("## Failures")
        lines.append("")
        for f in replay.failures:
            lines.append(f"- **[!]** {f.narrative}")
        lines.append("")

    lines.append("---")
    lines.append(f"**{replay.total_summary}**")
    return "\n".join(lines)
