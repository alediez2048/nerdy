"""Retry with exponential backoff for API resilience (P0-08, R3-Q2).

Handles 429 (rate limit), 500, 503. 2^n seconds, max 60s, 3 retries.
"""

from __future__ import annotations

import logging
import time
from typing import Callable, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


def _is_retryable(err: BaseException) -> bool:
    """True if error is 429, 500, or 503."""
    msg = str(err).lower()
    return (
        "429" in msg
        or "resource_exhausted" in msg
        or "500" in msg
        or "503" in msg
        or "internal" in msg
        or "unavailable" in msg
    )


def retry_with_backoff(
    func: Callable[[], T],
    max_retries: int = 3,
    base_delay: float = 2.0,
) -> T:
    """Execute func with exponential backoff on retryable errors.

    Retries on 429 (rate limit), 500, 503. Delay = min(base_delay * 2^n, 60).
    After max_retries: raises the last exception.
    """
    last_err: BaseException | None = None
    for attempt in range(max_retries):
        try:
            return func()
        except BaseException as e:
            last_err = e
            if not _is_retryable(e) or attempt == max_retries - 1:
                raise
            delay = min(base_delay * (2**attempt), 60.0)
            logger.warning(
                "Retryable error (attempt %d/%d), retrying in %.1fs: %s",
                attempt + 1,
                max_retries,
                delay,
                e,
            )
            time.sleep(delay)
    if last_err is not None:
        raise last_err
    raise RuntimeError("retry_with_backoff: unexpected state")
