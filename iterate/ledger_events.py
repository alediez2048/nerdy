"""Typed ledger event dataclasses — PH-01 (write-path seam).

Every event written to the append-only JSONL ledger has a corresponding
frozen dataclass here. Construction enforces the 8 required fields from
`iterate.ledger.REQUIRED_FIELDS`; `event_type` is derived from the class
name, eliminating typos at the source.

The on-disk JSONL format is preserved bit-for-bit — these dataclasses
serialize through `LedgerWriter` (which calls `log_event` underneath).

See `docs/development/tickets/PH-01-primer.md` for the design decisions
and `docs/deliverables/decisionlog.md` §9 for the append-only invariant.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class LedgerEvent:
    """Base for every ledger event.

    Carries the 8 required fields enforced by `iterate.ledger._validate_event`,
    plus the conventional `inputs`/`outputs` dicts most events use. Subclasses
    add event-specific top-level fields via `extra` or by declaring new
    dataclass fields.

    `event_type` is derived from the subclass name, not stored as a field —
    this prevents `"event_type": "AdGennerated"` typos at the source.
    """

    brief_id: str
    cycle_number: int
    action: str
    tokens_consumed: int
    model_used: str
    seed: str
    ad_id: str | None = None
    inputs: dict[str, Any] = field(default_factory=dict)
    outputs: dict[str, Any] = field(default_factory=dict)
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def event_type(self) -> str:
        return type(self).__name__

    def to_jsonl(self) -> str:
        """Serialize to a single JSON line (no trailing newline).

        Uses the same field ordering as `ledger_writer._serialize` so the
        output is consistent with the on-disk JSONL format.
        """
        from iterate.ledger_writer import _serialize  # local import avoids circularity

        return json.dumps(_serialize(self), separators=(",", ":"))


# --- Generation phase ---------------------------------------------------------


@dataclass(frozen=True)
class BriefExpanded(LedgerEvent):
    """Brief expansion produced an enriched semantic brief (R3-Q5)."""


@dataclass(frozen=True)
class AdGenerated(LedgerEvent):
    """Ad copy generated (or regenerated) for a brief."""


@dataclass(frozen=True)
class AdRouted(LedgerEvent):
    """Tiered routing decided whether to escalate to Pro tier."""


@dataclass(frozen=True)
class AspectRatioGenerated(LedgerEvent):
    """An additional aspect-ratio image variant was generated."""


@dataclass(frozen=True)
class VariantWin(LedgerEvent):
    """A copy variant won its A/B comparison."""


@dataclass(frozen=True)
class ImageVariantWin(LedgerEvent):
    """An image variant won its A/B comparison."""


# --- Evaluation phase ---------------------------------------------------------


@dataclass(frozen=True)
class AdEvaluated(LedgerEvent):
    """5-dimension CoT scoring completed for a copy ad."""


@dataclass(frozen=True)
class BriefAdherenceScored(LedgerEvent):
    """Brief-adherence scorer (PD-12) completed for an ad."""


@dataclass(frozen=True)
class WeightsRecalibrated(LedgerEvent):
    """Dimension weights were recalibrated post-hoc."""


@dataclass(frozen=True)
class PerformanceIngested(LedgerEvent):
    """External performance data (CTR, CPA, ROAS) ingested for an ad."""


@dataclass(frozen=True)
class VariantSelected(LedgerEvent):
    """The cost tracker recorded which variant was selected."""


# --- Image phase --------------------------------------------------------------


@dataclass(frozen=True)
class VisualSpecExtracted(LedgerEvent):
    """Visual spec extracted from copy + brief for image generation."""


@dataclass(frozen=True)
class ImageGenerated(LedgerEvent):
    """An image was generated for an ad (any variant)."""


@dataclass(frozen=True)
class ImageEvaluated(LedgerEvent):
    """Visual attribute checklist completed for an image."""


@dataclass(frozen=True)
class ImageScored(LedgerEvent):
    """Image quality scored (post-evaluation aggregation)."""


@dataclass(frozen=True)
class ImageBlocked(LedgerEvent):
    """Image generation hit the per-ad attempt cap and was marked blocked."""


# --- Video phase --------------------------------------------------------------


@dataclass(frozen=True)
class VideoSpecExtracted(LedgerEvent):
    """Video spec extracted from copy + brief."""


@dataclass(frozen=True)
class VideoGenerated(LedgerEvent):
    """A video variant was generated."""


@dataclass(frozen=True)
class VideoGenerationFailed(LedgerEvent):
    """Video generation API call failed."""


@dataclass(frozen=True)
class VideoEvaluated(LedgerEvent):
    """Video attribute / coherence checks completed."""


@dataclass(frozen=True)
class VideoSelected(LedgerEvent):
    """The winning video variant was chosen (display-cost relevant)."""


@dataclass(frozen=True)
class VideoScored(LedgerEvent):
    """Video quality score recorded."""


@dataclass(frozen=True)
class VideoBlocked(LedgerEvent):
    """Video generation gave up after retries — ad downgraded or dropped."""


# --- Pipeline lifecycle -------------------------------------------------------


@dataclass(frozen=True)
class AdPublished(LedgerEvent):
    """Ad passed all gates and was added to the published library."""


@dataclass(frozen=True)
class AdDiscarded(LedgerEvent):
    """Ad failed gates and was discarded after max regen cycles."""


@dataclass(frozen=True)
class AdEscalated(LedgerEvent):
    """Ad escalated to a higher model tier (Flash → Pro)."""


@dataclass(frozen=True)
class BriefMutated(LedgerEvent):
    """Brief was mutated after consecutive regen failures."""


@dataclass(frozen=True)
class BatchCompleted(LedgerEvent):
    """A batch (10 ads by default) finished processing.

    Currently logged with `ad_id="batch_<n>"` and `brief_id="batch_<n>"` —
    these are synthetic IDs to satisfy validation, preserved here for
    byte-identical on-disk format. A future phase may introduce a
    separate `BatchEvent` base that doesn't carry ad-scoped fields.
    """


# --- Test-only events (kept for read-back of fixture ledgers) -----------------


@dataclass(frozen=True)
class ContextDistilled(LedgerEvent):
    """Context distillation (R3-Q9). Currently only emitted in tests."""


@dataclass(frozen=True)
class StyleExperiment(LedgerEvent):
    """Style experiment event. Currently only emitted in tests."""


@dataclass(frozen=True)
class AdRegenerated(LedgerEvent):
    """Marker emitted in some legacy ledger fixtures."""


# --- Unified media quality evaluator (PI-02+) ---------------------------------


@dataclass(frozen=True)
class MediaEvaluation(LedgerEvent):
    """Unified per-variant media quality evaluation (PI-02). Schema v2.

    Replaces ImageEvaluated, ImageScored, VideoEvaluated, VideoCoherenceChecked,
    VideoScored. The outputs dict carries the full rubric: per-dimension
    {score, weight, rationale}, per-gate {triggered, rationale},
    raw_score / penalty_multiplier / composite_score, and schema_version.
    """

    event_type: str = "MediaEvaluation"


@dataclass(frozen=True)
class MediaEvaluationFailed(LedgerEvent):
    """Explicit failure event for a single variant (PI-02).

    Emitted when the evaluator cannot produce a MediaEvaluation — e.g.
    file missing, upload too large, LLM JSON unparseable. Selection skips
    failed variants; if all variants for an ad fail, the ad is
    regenerated via the existing P1-08 brief-mutation flow.
    """

    event_type: str = "MediaEvaluationFailed"


# --- Registry -----------------------------------------------------------------

EVENT_TYPES: dict[str, type[LedgerEvent]] = {
    cls.__name__: cls
    for cls in [
        BriefExpanded,
        AdGenerated,
        AdRouted,
        AspectRatioGenerated,
        VariantWin,
        ImageVariantWin,
        AdEvaluated,
        BriefAdherenceScored,
        WeightsRecalibrated,
        PerformanceIngested,
        VariantSelected,
        VisualSpecExtracted,
        ImageGenerated,
        ImageEvaluated,
        ImageScored,
        ImageBlocked,
        VideoSpecExtracted,
        VideoGenerated,
        VideoGenerationFailed,
        VideoEvaluated,
        VideoSelected,
        VideoScored,
        VideoBlocked,
        AdPublished,
        AdDiscarded,
        AdEscalated,
        BriefMutated,
        BatchCompleted,
        ContextDistilled,
        StyleExperiment,
        AdRegenerated,
        MediaEvaluation,
        MediaEvaluationFailed,
    ]
}
"""Maps `event_type` string → concrete dataclass. Consumed by `LedgerReader.read_typed_events()`."""


def parse_event(line: str) -> LedgerEvent:
    """Parse a single JSONL line produced by `LedgerEvent.to_jsonl()`.

    Returns a typed subclass when the `event_type` is registered; falls back
    to the base `LedgerEvent` for unknown types (forward-compatibility).
    """
    from iterate.ledger_reader import _parse_event  # local import avoids circularity

    return _parse_event(json.loads(line))
