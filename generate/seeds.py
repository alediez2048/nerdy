"""Per-ad deterministic seed chain (R3-Q4). Identity-derived, not position-derived."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Optional

import yaml


def get_ad_seed(global_seed: str, brief_id: str, cycle_number: int) -> int:
    """Derive a deterministic integer seed for an ad.

    Same inputs always produce the same seed. Different cycle_number or brief_id
    produces different seed. Skipping an ad does NOT affect other ads' seeds.
    """
    raw = f"{global_seed}:{brief_id}:{cycle_number}"
    return int(hashlib.sha256(raw.encode()).hexdigest()[:8], 16)


def load_global_seed(config_path: Optional[str] = None) -> str:
    """Load global seed: GLOBAL_SEED env var, then config.yaml, then default."""
    env_seed = os.environ.get("GLOBAL_SEED")
    if env_seed:
        return env_seed

    path = Path(config_path) if config_path else Path("data/config.yaml")
    if path.exists():
        with open(path, encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
        seed = cfg.get("global_seed")
        if seed:
            return str(seed)

    return "default-global-seed"
