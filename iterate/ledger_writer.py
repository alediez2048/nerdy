"""Typed ledger writer — PH-01 (write-path seam).

`LedgerWriter` wraps `iterate.ledger.log_event`. Callers build a typed
`LedgerEvent` subclass and pass it to `writer.record(event)`; the writer
serializes it to the same dict shape `log_event` already validates and
writes, so the on-disk JSONL format is bit-for-bit unchanged.

Why wrap and not replace `log_event`:
- Preserves `fcntl` file locking, `_validate_event` enforcement, and
  the existing reader cache invalidation.
- Migration is mechanical: every caller swaps one `log_event(path, {...})`
  for `LedgerWriter(path).record(EventClass(...))`.
- Old callers that still use `log_event` directly keep working during
  the incremental migration.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from iterate.ledger import log_event
from iterate.ledger_events import LedgerEvent


_LEGACY_KEY_ORDER = (
    "event_type",
    "ad_id",
    "brief_id",
    "cycle_number",
    "action",
    "tokens_consumed",
    "model_used",
    "seed",
    "inputs",
    "outputs",
)


def _serialize(event: LedgerEvent) -> dict[str, Any]:
    """Convert a typed event to the dict shape `log_event` expects.

    Preserves the legacy key ordering used by hand-built dicts in pre-PH-01
    callers so that the JSONL on-disk output is byte-identical for the
    same logical event. `extra` fields are flattened in after `outputs`,
    preserving the order callers used pre-migration.
    """
    raw = asdict(event)
    extra = raw.pop("extra", {}) or {}
    raw["event_type"] = event.event_type

    payload: dict[str, Any] = {}
    for key in _LEGACY_KEY_ORDER:
        if key in raw:
            payload[key] = raw.pop(key)
    # any remaining keys (subclass-specific fields) — keep insertion order
    payload.update(raw)
    payload.update(extra)
    return payload


class LedgerWriter:
    """Stateful writer pinned to a single ledger file path.

    Construct once per pipeline run (or per session). All `record()`
    calls append to the same file, going through `log_event` for
    validation, locking, and cache invalidation.
    """

    __slots__ = ("ledger_path",)

    def __init__(self, ledger_path: str) -> None:
        self.ledger_path = ledger_path

    def record(self, event: LedgerEvent) -> None:
        """Append a typed event to the ledger.

        Raises `iterate.ledger.LedgerValidationError` if any required
        field is missing (should be impossible for events constructed
        via the dataclasses, but the check is preserved end-to-end).
        """
        log_event(self.ledger_path, _serialize(event))
