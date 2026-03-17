"""Persona-specific hook library — query and selection (PB-02).

Loads proven hooks from data/hooks_library.json and provides
seed-based, persona-filtered selection for brief expansion injection.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

HOOKS_PATH = Path("data/hooks_library.json")

_hooks_cache: list[dict] | None = None


def load_hooks() -> list[dict]:
    """Load all hooks from hooks_library.json. Cached after first call."""
    global _hooks_cache
    if _hooks_cache is not None:
        return _hooks_cache
    with open(HOOKS_PATH) as f:
        data = json.load(f)
    _hooks_cache = data.get("hooks", [])
    return _hooks_cache


def get_hooks_for_persona(
    persona: str, n: int = 3, seed: int = 0
) -> list[dict]:
    """Return up to n hooks for a persona, with seed-based diversity.

    First filters by exact persona match. If fewer than n results,
    falls back to category match (hooks whose category relates to the persona).

    Args:
        persona: Persona key (e.g., "athlete_recruit").
        n: Max hooks to return.
        seed: Deterministic seed for shuffling.

    Returns:
        List of hook dicts, up to n items.
    """
    all_hooks = load_hooks()

    # Exact persona match
    matched = [h for h in all_hooks if h.get("persona") == persona]

    # Fallback: also include hooks whose category matches the persona key
    if len(matched) < n:
        category_key = persona.replace("_", "")
        extras = [
            h for h in all_hooks
            if h.get("category", "").replace("_", "") == category_key
            and h not in matched
        ]
        matched.extend(extras)

    # Seed-based shuffle for diversity
    rng = random.Random(seed)
    rng.shuffle(matched)

    return matched[:n]


def get_hooks_for_category(
    category: str, n: int = 3, seed: int = 0
) -> list[dict]:
    """Return up to n hooks for a category.

    Args:
        category: Category key (e.g., "scholarship", "test_anxiety").
        n: Max hooks to return.
        seed: Deterministic seed for shuffling.

    Returns:
        List of hook dicts, up to n items.
    """
    all_hooks = load_hooks()
    matched = [h for h in all_hooks if h.get("category") == category]

    rng = random.Random(seed)
    rng.shuffle(matched)

    return matched[:n]


def get_all_personas() -> list[str]:
    """Return list of unique persona keys in the hook library."""
    all_hooks = load_hooks()
    return sorted(set(h.get("persona", "") for h in all_hooks if h.get("persona")))


def get_all_categories() -> list[str]:
    """Return list of unique category keys in the hook library."""
    all_hooks = load_hooks()
    return sorted(set(h.get("category", "") for h in all_hooks if h.get("category")))
