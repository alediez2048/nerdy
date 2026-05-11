"""Typed ledger reader — PH-01 (read-path seam).

Reading the ledger has two surfaces:

1. **Dict surface** (`read_events`, `read_events_filtered`, `get_ad_lifecycle`)
   — already implemented in `iterate.ledger`. Existing consumers keep using
   these unchanged.

2. **Typed surface** (`read_typed_events`, `read_typed_events_filtered`) —
   parses each raw dict into the appropriate `LedgerEvent` subclass from the
   `EVENT_TYPES` registry. Unknown event types fall back to the base
   `LedgerEvent`. New consumers (PH-02 CostAttributor, PH-04 EvaluationPipeline)
   opt into this for safer field access.

The reader does NOT change on-disk format and does NOT mutate the ledger.
"""

from __future__ import annotations

from typing import Any, Iterable

from iterate.ledger import (
    LedgerFilterValue,
    read_events,
    read_events_filtered,
)
from iterate.ledger_events import EVENT_TYPES, LedgerEvent


# --- Public helpers (re-export the existing dict surface for discoverability) -


def read_dicts(ledger_path: str) -> list[dict]:
    """Return all events as raw dicts (alias for `iterate.ledger.read_events`)."""
    return read_events(ledger_path)


def read_dicts_filtered(ledger_path: str, **filters: LedgerFilterValue) -> list[dict]:
    """Return events filtered by exact-match fields, as raw dicts."""
    return read_events_filtered(ledger_path, **filters)


# --- Typed surface (PH-01 addition) -------------------------------------------


def _parse_event(raw: dict[str, Any]) -> LedgerEvent:
    """Materialize a typed event from a raw ledger dict.

    Unknown `event_type` values fall back to the base `LedgerEvent` so
    that future event types added to the on-disk format don't crash
    older readers.

    Top-level fields outside the base schema and outside the known
    subclass fields are collected into `extra` so nothing is lost.
    """
    event_type = raw.get("event_type", "")
    cls = EVENT_TYPES.get(event_type, LedgerEvent)
    is_unknown_type = cls is LedgerEvent and event_type and event_type not in EVENT_TYPES

    # Fields the dataclass knows about (all subclasses inherit the base).
    known = {
        "ad_id",
        "brief_id",
        "cycle_number",
        "action",
        "tokens_consumed",
        "model_used",
        "seed",
        "inputs",
        "outputs",
    }

    kwargs: dict[str, Any] = {k: raw.get(k) for k in known if k in raw}

    # Provide safe defaults for fields the on-disk format might omit.
    kwargs.setdefault("brief_id", raw.get("brief_id", ""))
    kwargs.setdefault("cycle_number", raw.get("cycle_number", 0))
    kwargs.setdefault("action", raw.get("action", ""))
    kwargs.setdefault("tokens_consumed", raw.get("tokens_consumed", 0))
    kwargs.setdefault("model_used", raw.get("model_used", ""))
    kwargs.setdefault("seed", raw.get("seed", ""))
    kwargs.setdefault("inputs", raw.get("inputs", {}) or {})
    kwargs.setdefault("outputs", raw.get("outputs", {}) or {})

    # Anything else — timestamps, checkpoint_id, event-specific top-level
    # fields — goes into `extra` so it round-trips for re-serialization.
    # For UNKNOWN event types, we preserve `event_type` in extra so type
    # identity isn't lost on round-trip (known types derive it from class name).
    reserved = known if is_unknown_type else known | {"event_type"}
    extra = {k: v for k, v in raw.items() if k not in reserved}
    kwargs["extra"] = extra

    return cls(**kwargs)


def read_typed_events(ledger_path: str) -> list[LedgerEvent]:
    """Return all ledger events as typed `LedgerEvent` subclasses.

    Backwards-compatible: any unknown event_type yields a base
    `LedgerEvent` so older readers don't break when new event types
    are introduced.
    """
    return [_parse_event(raw) for raw in read_events(ledger_path)]


def read_typed_events_filtered(
    ledger_path: str, **filters: LedgerFilterValue
) -> list[LedgerEvent]:
    """Typed equivalent of `read_events_filtered`."""
    return [_parse_event(raw) for raw in read_events_filtered(ledger_path, **filters)]


def iter_typed_events(ledger_path: str) -> Iterable[LedgerEvent]:
    """Lazy variant for callers that don't need to materialize the full list."""
    for raw in read_events(ledger_path):
        yield _parse_event(raw)


class LedgerReader:
    """Stateful reader pinned to a single ledger file path.

    Useful when a consumer (e.g. `CostAttributor`) needs to issue
    several queries against the same ledger and benefit from the
    underlying mtime/size cache in `iterate.ledger`.
    """

    __slots__ = ("ledger_path",)

    def __init__(self, ledger_path: str) -> None:
        self.ledger_path = ledger_path

    def events(self) -> list[LedgerEvent]:
        return read_typed_events(self.ledger_path)

    def events_filtered(self, **filters: LedgerFilterValue) -> list[LedgerEvent]:
        return read_typed_events_filtered(self.ledger_path, **filters)

    def ad_lifecycle(self, ad_id: str) -> list[LedgerEvent]:
        return self.events_filtered(ad_id=ad_id)
