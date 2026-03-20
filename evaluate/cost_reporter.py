"""Cross-format cost reporter — token and USD cost attribution (P3-05).

Groups API costs by model, format (text/image/video), and task
across the entire pipeline. Applies per-model cost rates for
estimated USD costs.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field

from iterate.ledger import read_events

logger = logging.getLogger(__name__)

# Per-model cost rates (USD per 1K tokens or per call for non-token models)
MODEL_COST_RATES: dict[str, float] = {
    "gemini-2.0-flash": 0.01 / 1000,          # $0.01 per 1K tokens
    "gemini-2.0-pro": 0.05 / 1000,            # $0.05 per 1K tokens
    "gemini-2.0-flash-preview-image-generation": 0.13,  # ~$0.13 per image call
    "gemini-3.1-flash-image": 0.035,           # ~$0.035 per image call
    "veo-3.1-fast": 0.90,                      # ~$0.90 per 6-sec video
    # Video provider aliases (actual model_used values from video clients)
    "veo": 0.90,                               # Google Veo
    "fal": 0.50,                               # Fal.ai
    "fal-ai/veo3": 0.90,                       # Fal.ai Veo3
    "fal-ai/kling-video/v2.1/standard": 0.50,  # Fal.ai Kling
    "kling": 0.50,                             # Kling 2.6
    "kling-2.6": 0.50,                         # Kling 2.6 alternate
}

# Event types that use per-call pricing (not per-token)
PER_CALL_EVENT_TYPES = {
    "ImageGenerated", "ImageRegenerated", "AspectRatioGenerated",
    "VideoGenerated", "VideoEvaluated", "VideoSelected",
    "VideoCoherenceChecked",
}

# Map event types to creative format
_FORMAT_MAP: dict[str, str] = {
    "AdGenerated": "text",
    "BriefExpanded": "text",
    "AdEvaluated": "text",
    "AdRegenerated": "text",
    "ContextDistilled": "text",
    "AdRouted": "text",
    "ImageGenerated": "image",
    "ImageEvaluated": "image",
    "ImageRegenerated": "image",
    "AspectRatioGenerated": "image",
    "VideoGenerated": "video",
    "VideoEvaluated": "video",
}

# Map event types to task
_TASK_MAP: dict[str, str] = {
    "AdGenerated": "generation",
    "BriefExpanded": "generation",
    "AdEvaluated": "evaluation",
    "AdRegenerated": "regeneration",
    "ContextDistilled": "generation",
    "AdRouted": "routing",
    "ImageGenerated": "generation",
    "ImageEvaluated": "evaluation",
    "ImageRegenerated": "regeneration",
    "AspectRatioGenerated": "generation",
    "VideoGenerated": "generation",
    "VideoEvaluated": "evaluation",
}

# Legacy alias (use PER_CALL_EVENT_TYPES above instead)
_PER_CALL_EVENTS = PER_CALL_EVENT_TYPES


def compute_event_cost(event: dict) -> float:
    """Compute the USD cost of a single ledger event.

    Uses per-call pricing for image/video events, per-token for text.
    Falls back to credits from outputs if tokens_consumed is 0.
    """
    event_type = event.get("event_type", "")
    model = event.get("model_used", "unknown")
    tokens = event.get("tokens_consumed", 0)
    rate = MODEL_COST_RATES.get(model, 0.01 / 1000)

    if event_type in PER_CALL_EVENT_TYPES:
        # Per-call pricing for image/video
        # Check for credits in outputs (video events store credits there)
        outputs = event.get("outputs", {})
        credits = outputs.get("credits", 0) or outputs.get("credits_consumed", 0)
        if credits and credits > 0:
            return credits * 0.001  # credits to USD
        return rate  # one API call at the model's per-call rate
    else:
        # Per-token pricing for text events
        return rate * tokens


@dataclass
class ModelCostEntry:
    """Cost entry for one model/task/format combination."""

    model_name: str
    task: str
    format: str
    total_tokens: int
    call_count: int
    estimated_cost_usd: float


@dataclass
class CrossFormatCostReport:
    """Full cost report across all formats."""

    entries: list[ModelCostEntry]
    total_cost_usd: float
    cost_by_format: dict[str, float] = field(default_factory=dict)
    cost_by_model: dict[str, float] = field(default_factory=dict)
    cost_by_task: dict[str, float] = field(default_factory=dict)


def generate_cost_report(ledger_path: str) -> CrossFormatCostReport:
    """Generate a cross-format cost report from the ledger.

    Reads all events, groups by model/format/task, and applies
    per-model cost rates.

    Args:
        ledger_path: Path to the JSONL ledger.

    Returns:
        CrossFormatCostReport with full breakdown.
    """
    events = read_events(ledger_path)

    # Accumulate: (model, task, format) -> {tokens, calls}
    buckets: dict[tuple[str, str, str], dict] = defaultdict(
        lambda: {"tokens": 0, "calls": 0}
    )

    for event in events:
        event_type = event.get("event_type", "")
        if event_type not in _FORMAT_MAP:
            continue

        model = event.get("model_used", "unknown")
        tokens = event.get("tokens_consumed", 0)
        fmt = _FORMAT_MAP[event_type]
        task = _TASK_MAP.get(event_type, "other")

        key = (model, task, fmt)
        buckets[key]["tokens"] += tokens
        buckets[key]["calls"] += 1

    # Build entries with cost estimates
    entries: list[ModelCostEntry] = []
    cost_by_format: dict[str, float] = defaultdict(float)
    cost_by_model: dict[str, float] = defaultdict(float)
    cost_by_task: dict[str, float] = defaultdict(float)

    for (model, task, fmt), stats in buckets.items():
        rate = MODEL_COST_RATES.get(model, 0.01 / 1000)

        # Image/video models: per-call pricing
        if any(et in _PER_CALL_EVENTS for et, f in _FORMAT_MAP.items() if f == fmt) and fmt in ("image", "video"):
            cost = rate * stats["calls"]
        else:
            cost = rate * stats["tokens"]

        entry = ModelCostEntry(
            model_name=model,
            task=task,
            format=fmt,
            total_tokens=stats["tokens"],
            call_count=stats["calls"],
            estimated_cost_usd=round(cost, 6),
        )
        entries.append(entry)
        cost_by_format[fmt] += cost
        cost_by_model[model] += cost
        cost_by_task[task] += cost

    total = sum(e.estimated_cost_usd for e in entries)

    return CrossFormatCostReport(
        entries=entries,
        total_cost_usd=round(total, 6),
        cost_by_format=dict(cost_by_format),
        cost_by_model=dict(cost_by_model),
        cost_by_task=dict(cost_by_task),
    )


def format_cost_report(report: CrossFormatCostReport) -> str:
    """Format cost report as human-readable text.

    Args:
        report: The cost report to format.

    Returns:
        Multi-line string summary.
    """
    lines = ["=== Cross-Format Cost Report ===", ""]

    lines.append("By Format:")
    for fmt, cost in sorted(report.cost_by_format.items()):
        lines.append(f"  {fmt:>8s}: ${cost:.4f}")
    lines.append("")

    lines.append("By Model:")
    for model, cost in sorted(report.cost_by_model.items()):
        lines.append(f"  {model}: ${cost:.4f}")
    lines.append("")

    lines.append("By Task:")
    for task, cost in sorted(report.cost_by_task.items()):
        lines.append(f"  {task:>14s}: ${cost:.4f}")
    lines.append("")

    lines.append(f"Total: ${report.total_cost_usd:.4f}")
    return "\n".join(lines)
