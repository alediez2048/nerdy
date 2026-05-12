"""Full pipeline runner — capstone orchestrator (P1-20).

Runs the complete ad generation pipeline end-to-end: brief expansion,
copy generation, image generation (3 variants), evaluation, Pareto
selection, targeted regen, quality ratchet, and assembly/export.

Supports dry_run mode for testing without API calls.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from iterate.batch_processor import BatchResult

logger = logging.getLogger(__name__)

# Brief templates for generating diverse ad briefs
_PRODUCTS = [
    "SAT prep tutoring",
    "ACT prep tutoring",
    "AP Calculus tutoring",
    "AP English tutoring",
    "College admissions counseling",
    "Math tutoring",
    "Science tutoring",
    "Essay writing coaching",
    "Study skills coaching",
    "Test anxiety support",
]

_AUDIENCES = ["parents", "students"]
_CAMPAIGN_GOALS = ["awareness", "conversion"]


@dataclass
class PipelineConfig:
    """Configuration for a full pipeline run."""

    num_batches: int = 5
    batch_size: int = 10
    max_cycles: int = 3
    text_threshold: float = 7.0
    image_attribute_threshold: float = 0.8
    coherence_threshold: float = 6.0
    ledger_path: str = "data/ledger.jsonl"
    output_dir: str = "output/ads"
    dry_run: bool = False
    global_seed: str = "nerdy_p1_20"
    persona: str | None = None
    audience: str | None = None
    campaign_goal: str | None = None
    key_message: str = ""
    # PH-03 — session-specific fields previously inlined in pipeline_task only.
    image_enabled: bool = True
    creative_brief: str = "auto"
    copy_on_image: bool = False
    aspect_ratios: list[str] = field(default_factory=lambda: ["1:1"])


@dataclass
class RunSummary:
    """Summary of a complete pipeline run."""

    total_briefs: int = 0
    batches_completed: int = 0
    total_generated: int = 0
    total_published: int = 0
    total_discarded: int = 0
    total_regenerated: int = 0
    total_escalated: int = 0
    batch_results: list[BatchResult] = field(default_factory=list)


def generate_briefs(config: PipelineConfig) -> list[dict[str, Any]]:
    """Generate ad briefs driven by session config.

    When the session specifies audience and campaign_goal, all briefs use
    those values (the user chose them). Products still rotate for variety.
    When audience/goal are not set (CLI mode), falls back to the original
    alternating behaviour.

    Args:
        config: Pipeline configuration.

    Returns:
        List of brief dicts ready for pipeline processing.
    """
    total = config.num_batches * config.batch_size
    briefs: list[dict[str, Any]] = []

    session_audience = config.audience
    session_goal = config.campaign_goal

    for i in range(total):
        product = _PRODUCTS[i % len(_PRODUCTS)]
        audience = session_audience or _AUDIENCES[i % len(_AUDIENCES)]
        goal = session_goal or _CAMPAIGN_GOALS[(i // 2) % len(_CAMPAIGN_GOALS)]

        default_msg = f"Expert {product} — personalized 1-on-1 sessions"
        brief: dict[str, Any] = {
            "brief_id": f"brief_{i + 1:03d}",
            "product": product,
            "audience": audience,
            "campaign_goal": goal,
            "key_message": config.key_message or default_msg,
            "platform": "facebook",
        }
        if config.persona:
            brief["persona"] = config.persona
        briefs.append(brief)

    return briefs


def run_pipeline(config: PipelineConfig) -> RunSummary:
    """Execute the full pipeline end-to-end.

    Thin shim over :class:`iterate.pipeline_orchestrator.PipelineOrchestrator`
    (PH-03). Kept as a module-level function so existing CLI imports and
    tests continue to work; new code should construct an orchestrator
    directly and pass a ``ProgressSink``.
    """
    from iterate.pipeline_orchestrator import PipelineOrchestrator

    return PipelineOrchestrator().run(config)
