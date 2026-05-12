"""Progress sinks — PH-03 (pipeline orchestrator).

The `PipelineOrchestrator` emits typed progress events at batch
boundaries. Where those events go is a ``ProgressSink`` decision:

- :class:`NullProgressSink` — drops everything (default; used in tests and
  CLI when progress isn't wanted as structured output).
- :class:`StdoutProgressSink` — logs each event via the standard logger
  (CLI-friendly).
- :class:`RedisProgressSink` — publishes via
  :func:`app.workers.progress.publish_progress` so the SSE endpoint can
  forward to the frontend.

Adding a new entry point — webhook, scheduled run, debugging tool — is
a new sink, not a new copy of the batch loop.
"""

from __future__ import annotations

import logging
from typing import Any, Protocol


class ProgressSink(Protocol):
    """How the orchestrator reports per-batch progress.

    ``event_type`` matches the constants in ``app.workers.progress``
    (``batch_start``, ``batch_complete``, ``pipeline_complete``,
    ``pipeline_error``). ``payload`` carries batch counters,
    cost-so-far, and current average score.
    """

    def emit(self, event_type: str, payload: dict[str, Any]) -> None: ...


class NullProgressSink:
    """No-op sink. Use in tests and when progress events are uninteresting."""

    def emit(self, event_type: str, payload: dict[str, Any]) -> None:  # noqa: D401
        return None


class StdoutProgressSink:
    """Log each event through the standard logger.

    Useful for CLI runs where the existing ``logger.info`` output is
    enough — the structured payload appears alongside other pipeline
    logs at INFO level.
    """

    __slots__ = ("logger",)

    def __init__(self, logger: logging.Logger | None = None) -> None:
        self.logger = logger or logging.getLogger("pipeline.progress")

    def emit(self, event_type: str, payload: dict[str, Any]) -> None:
        self.logger.info("[%s] %s", event_type, payload)


class RedisProgressSink:
    """Publish each event to the Redis pub/sub channel for a session.

    Wraps :func:`app.workers.progress.publish_progress`. The function
    import is lazy so this module can be imported without pulling in
    Redis / app.config at module load time (keeps the orchestrator
    importable by CLI smoke tests that don't run a worker).
    """

    __slots__ = ("session_id",)

    def __init__(self, session_id: str) -> None:
        self.session_id = session_id

    def emit(self, event_type: str, payload: dict[str, Any]) -> None:
        from app.workers.progress import publish_progress

        publish_progress(self.session_id, {"type": event_type, **payload})
