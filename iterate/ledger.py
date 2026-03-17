"""Append-only JSONL decision ledger — single source of truth for pipeline events.

Every generation, evaluation, regeneration, and decision is recorded here.
Foundation for checkpoint-resume (P0-08), token attribution (P1-11),
narrated replay (P4-07), and quality trend visualization (P5-03).

Architectural decisions: R2-Q8 (append-only JSONL), R3-Q2 (checkpoint_id for resume).
"""

from __future__ import annotations

import fcntl
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Union
from uuid import uuid4

REQUIRED_FIELDS = [
    "event_type",
    "ad_id",
    "brief_id",
    "cycle_number",
    "action",
    "tokens_consumed",
    "model_used",
    "seed",
]


class LedgerValidationError(ValueError):
    """Raised when an event fails schema validation."""


def _validate_event(event: dict) -> None:
    """Validate event has all required fields. Raises LedgerValidationError."""
    missing = [f for f in REQUIRED_FIELDS if f not in event]
    if missing:
        raise LedgerValidationError(f"Missing required fields: {', '.join(missing)}")


def log_event(ledger_path: str, event: dict) -> None:
    """Append a single event to the ledger. Auto-injects timestamp and checkpoint_id.

    - Validates schema before writing
    - Copies event dict to avoid mutating caller's data
    - Uses fcntl file locking for concurrent write safety
    - Creates parent directories if needed
    """
    _validate_event(event)
    event = dict(event)
    event["timestamp"] = datetime.now(timezone.utc).isoformat()
    event["checkpoint_id"] = str(uuid4())

    path = Path(ledger_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "a") as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        try:
            f.write(json.dumps(event, default=str) + "\n")
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)


_ledger_logger = logging.getLogger(__name__)


def read_events(ledger_path: str) -> list[dict]:
    """Read all events from the ledger. Returns [] if file does not exist.

    Skips malformed lines (e.g. truncated JSON from mid-stream crashes)
    and logs a warning for each.
    """
    path = Path(ledger_path)
    if not path.exists():
        return []

    events: list[dict] = []
    with open(path) as f:
        for lineno, line in enumerate(f, 1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                events.append(json.loads(stripped))
            except json.JSONDecodeError:
                _ledger_logger.warning("Skipping malformed ledger line %d in %s", lineno, ledger_path)
    return events


LedgerFilterValue = Union[str, int, None]


def read_events_filtered(ledger_path: str, **filters: LedgerFilterValue) -> list[dict]:
    """Read events filtered by any combination of fields (ad_id, brief_id, event_type, etc.)."""
    events = read_events(ledger_path)
    if not filters:
        return events

    return [ev for ev in events if all(ev.get(k) == v for k, v in filters.items())]


def get_ad_lifecycle(ledger_path: str, ad_id: str) -> list[dict]:
    """Return all events for a single ad, in chronological order."""
    return read_events_filtered(ledger_path, ad_id=ad_id)
