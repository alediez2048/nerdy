"""Result-level cache with version-based invalidation (P1-12, R3-Q7).

Cache key: sha256(ad_text + evaluator_prompt_version). Identical ad text
evaluated by the same prompt version returns instantly from cache. When the
evaluator prompt changes, all cached scores are automatically invalidated.

Storage: JSONL file (consistent with ledger's append-only pattern).
Last match wins on lookup (append-only means newer entries override).
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def compute_cache_key(ad_text: str, prompt_version: str) -> str:
    """Compute deterministic cache key from ad text and prompt version.

    Args:
        ad_text: The full ad text being evaluated.
        prompt_version: The evaluator prompt version string.

    Returns:
        SHA-256 hex digest of the combined input.
    """
    raw = f"{ad_text}||{prompt_version}"
    return hashlib.sha256(raw.encode()).hexdigest()


def get_cached_result(
    cache_path: str, ad_text: str, prompt_version: str
) -> dict[str, Any] | None:
    """Look up a cached evaluation result.

    Args:
        cache_path: Path to the cache JSONL file.
        ad_text: The ad text to look up.
        prompt_version: The prompt version to match.

    Returns:
        Cached result dict on hit, None on miss.
    """
    path = Path(cache_path)
    if not path.exists():
        return None

    key = compute_cache_key(ad_text, prompt_version)
    result = None

    with open(path) as f:
        for line in f:
            stripped = line.strip()
            if not stripped:
                continue
            try:
                entry = json.loads(stripped)
                if entry.get("cache_key") == key:
                    result = entry.get("result")  # last match wins
            except json.JSONDecodeError:
                continue

    return result


def store_result(
    cache_path: str,
    ad_text: str,
    prompt_version: str,
    result: dict[str, Any],
) -> None:
    """Store an evaluation result in the cache.

    Args:
        cache_path: Path to the cache JSONL file.
        ad_text: The ad text that was evaluated.
        prompt_version: The evaluator prompt version.
        result: The evaluation result dict to cache.
    """
    path = Path(cache_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    key = compute_cache_key(ad_text, prompt_version)
    entry = {
        "cache_key": key,
        "ad_text_hash": hashlib.sha256(ad_text.encode()).hexdigest()[:16],
        "prompt_version": prompt_version,
        "result": result,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    with open(path, "a") as f:
        f.write(json.dumps(entry) + "\n")

    logger.debug("Cached result for key %s (version=%s)", key[:12], prompt_version)


def invalidate_cache(cache_path: str) -> int:
    """Clear all cache entries.

    Args:
        cache_path: Path to the cache JSONL file.

    Returns:
        Number of entries cleared.
    """
    path = Path(cache_path)
    if not path.exists():
        return 0

    # Count entries before clearing
    count = 0
    with open(path) as f:
        for line in f:
            if line.strip():
                count += 1

    # Truncate the file
    with open(path, "w") as f:
        pass  # empty the file

    logger.info("Invalidated cache: %d entries cleared from %s", count, cache_path)
    return count


def get_cache_stats(cache_path: str) -> dict[str, Any]:
    """Return cache statistics for debugging and dashboard.

    Args:
        cache_path: Path to the cache JSONL file.

    Returns:
        Dict with total_entries, prompt_versions, oldest_entry, newest_entry.
    """
    path = Path(cache_path)
    if not path.exists():
        return {
            "total_entries": 0,
            "prompt_versions": [],
            "oldest_entry": None,
            "newest_entry": None,
        }

    entries: list[dict] = []
    with open(path) as f:
        for line in f:
            stripped = line.strip()
            if stripped:
                try:
                    entries.append(json.loads(stripped))
                except json.JSONDecodeError:
                    continue

    if not entries:
        return {
            "total_entries": 0,
            "prompt_versions": [],
            "oldest_entry": None,
            "newest_entry": None,
        }

    versions = sorted(set(e.get("prompt_version", "") for e in entries))
    timestamps = [e.get("created_at", "") for e in entries if e.get("created_at")]

    return {
        "total_entries": len(entries),
        "prompt_versions": versions,
        "oldest_entry": min(timestamps) if timestamps else None,
        "newest_entry": max(timestamps) if timestamps else None,
    }
