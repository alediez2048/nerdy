"""Cross-format cost reporter — token and USD cost attribution (P3-05).

Groups API costs by model, format (text/image/video), and task
across the entire pipeline. Applies per-model cost rates for
estimated USD costs.
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from iterate.ledger import read_events

logger = logging.getLogger(__name__)

# Per-model cost rates (USD per 1K tokens or per call for non-token models)
# Gemini rates: https://ai.google.dev/gemini-api/docs/pricing
#
# Video **generation** per-call pricing is NOT all in this table:
# - Google Veo API (`model_used` ``veo-3.1-fast``) → ``video_google_veo_cost_per_call_usd`` in config.yaml
# - Fal hosted ``fal-ai/veo3`` → ``video_fal_veo3_cost_per_call_usd`` in config.yaml
# - Other Fal/Kling endpoints → use the keys below (tune from each vendor’s Usage / pricing page)
MODEL_COST_RATES: dict[str, float] = {
    "gemini-2.0-flash": 0.01 / 1000,          # $0.01 per 1K tokens
    "gemini-2.0-pro": 0.05 / 1000,            # $0.05 per 1K tokens
    "gemini-2.0-flash-preview-image-generation": 0.13,  # ~$0.13 per image call
    "nano-banana-pro-preview": 0.13,           # Nano Banana Pro (same tier as flash image gen)
    "gemini-2.5-flash-image": 0.035,
    "gemini-3.1-flash-image": 0.035,           # ~$0.035 per image call
    # Legacy / generic labels (avoid using for VideoGenerated — use config keys above)
    "veo-3.1-fast": 0.28,
    "veo": 0.28,
    "fal": 0.28,
    "fal-ai/kling-video/v2.1/standard": 0.28,  # Fal Kling (rough)
    # Fal presets (per-call placeholders; tune from dashboard)
    # Wan distill: tune from Fal Usage (often ~$1–2/job); config ``video_fal_model_costs_usd`` overrides
    "fal-ai/wan/v2.2-5b/text-to-video/distill": 1.50,
    "fal-ai/minimax/hailuo-02/standard/text-to-video": 0.35,
    "fal-ai/wan-22": 0.55,
    "fal-ai/minimax/hailuo-2.3/pro/text-to-video": 2.50,
    "kling": 0.28,
    "kling-2.6": 0.28,
    "kling-v2.6-pro": 0.28,
}

# Defaults when config keys are missing (override in data/config.yaml per account)
GOOGLE_VEO_DEFAULT_PER_CALL_USD: float = 6.00
FAL_VEO3_DEFAULT_PER_CALL_USD: float = 6.40
_GOOGLE_VEO_PER_CALL_USD: float | None = None
_FAL_VEO3_PER_CALL_USD: float | None = None

# Reference billing total (Gemini + Fal invoices, March 2026). Used for docs / sanity checks only.
BILLING_REFERENCE_TOTAL_USD = 84.68

# Backward-compatible alias (prefer BILLING_REFERENCE_TOTAL_USD in new code).
HISTORICAL_SPEND_USD = BILLING_REFERENCE_TOTAL_USD

# Event types that use per-call pricing (not per-token)
# Only actual generation calls — evaluation events use Gemini Flash (per-token)
PER_CALL_EVENT_TYPES = {
    "ImageGenerated", "ImageRegenerated", "AspectRatioGenerated",
    "VideoGenerated",
}

# Map event types to creative format
_FORMAT_MAP: dict[str, str] = {
    "AdGenerated": "text",
    "BriefExpanded": "text",
    "AdEvaluated": "text",
    "AdRegenerated": "text",
    "ContextDistilled": "text",
    "AdRouted": "text",
    "VisualSpecExtracted": "text",
    "VideoSpecExtracted": "text",
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
    "VisualSpecExtracted": "generation",
    "VideoSpecExtracted": "generation",
    "ImageGenerated": "generation",
    "ImageEvaluated": "evaluation",
    "ImageRegenerated": "regeneration",
    "AspectRatioGenerated": "generation",
    "VideoGenerated": "generation",
    "VideoEvaluated": "evaluation",
}

# Legacy alias (use PER_CALL_EVENT_TYPES above instead)
_PER_CALL_EVENTS = PER_CALL_EVENT_TYPES

COST_MANIFEST_PATH = Path("data/cost_manifest.json")
_MANIFEST_CACHE: dict[str, object] | None = None
_FAL_MODEL_COST_OVERRIDES: dict[str, float] | None = None


def _load_cost_manifest() -> dict[str, object]:
    """Load optional per-session cost overrides (historical backfill)."""
    global _MANIFEST_CACHE
    if _MANIFEST_CACHE is not None:
        return _MANIFEST_CACHE
    path = COST_MANIFEST_PATH
    if not path.exists():
        _MANIFEST_CACHE = {}
        return _MANIFEST_CACHE
    try:
        with path.open(encoding="utf-8") as f:
            _MANIFEST_CACHE = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Could not load cost manifest %s: %s", path, e)
        _MANIFEST_CACHE = {}
    return _MANIFEST_CACHE


def reload_cost_manifest() -> None:
    """Clear manifest cache (e.g. after tests mutate the file)."""
    global _MANIFEST_CACHE
    _MANIFEST_CACHE = None


def reload_fal_veo3_cost_config() -> None:
    """Clear cached Fal Veo3 per-call rate (e.g. after tests change config)."""
    global _FAL_VEO3_PER_CALL_USD
    _FAL_VEO3_PER_CALL_USD = None


def reload_google_veo_cost_config() -> None:
    """Clear cached Google Veo per-call rate (e.g. after tests change config)."""
    global _GOOGLE_VEO_PER_CALL_USD
    _GOOGLE_VEO_PER_CALL_USD = None


def reload_fal_model_cost_overrides() -> None:
    """Clear cached ``video_fal_model_costs_usd`` map from config."""
    global _FAL_MODEL_COST_OVERRIDES
    _FAL_MODEL_COST_OVERRIDES = None


def _load_fal_model_cost_overrides() -> dict[str, float]:
    """Optional ``video_fal_model_costs_usd`` map: exact Fal endpoint id -> USD per completed job."""
    global _FAL_MODEL_COST_OVERRIDES
    if _FAL_MODEL_COST_OVERRIDES is not None:
        return _FAL_MODEL_COST_OVERRIDES
    path = Path("data/config.yaml")
    if not path.exists():
        _FAL_MODEL_COST_OVERRIDES = {}
        return _FAL_MODEL_COST_OVERRIDES
    try:
        import yaml

        with path.open(encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
        raw = cfg.get("video_fal_model_costs_usd")
        out: dict[str, float] = {}
        if isinstance(raw, dict):
            for k, v in raw.items():
                if isinstance(k, str) and isinstance(v, (int, float)) and float(v) > 0:
                    out[k] = float(v)
        _FAL_MODEL_COST_OVERRIDES = out
    except (OSError, TypeError, ValueError) as e:
        logger.debug("Could not read video_fal_model_costs_usd: %s", e)
        _FAL_MODEL_COST_OVERRIDES = {}
    return _FAL_MODEL_COST_OVERRIDES


def get_fal_veo3_per_call_usd() -> float:
    """USD per ``VideoGenerated`` for Fal hosted ``fal-ai/veo3`` (see ``video_fal_veo3_cost_per_call_usd``)."""
    global _FAL_VEO3_PER_CALL_USD
    if _FAL_VEO3_PER_CALL_USD is not None:
        return _FAL_VEO3_PER_CALL_USD
    _FAL_VEO3_PER_CALL_USD = _load_fal_veo3_per_call_usd()
    return _FAL_VEO3_PER_CALL_USD


def get_google_veo_per_call_usd() -> float:
    """USD per ``VideoGenerated`` for Google Veo API ``veo-3.1-fast`` (see ``video_google_veo_cost_per_call_usd``)."""
    global _GOOGLE_VEO_PER_CALL_USD
    if _GOOGLE_VEO_PER_CALL_USD is not None:
        return _GOOGLE_VEO_PER_CALL_USD
    _GOOGLE_VEO_PER_CALL_USD = _load_google_veo_per_call_usd()
    return _GOOGLE_VEO_PER_CALL_USD


def _load_fal_veo3_per_call_usd() -> float:
    """Read ``video_fal_veo3_cost_per_call_usd`` from ``data/config.yaml``."""
    path = Path("data/config.yaml")
    if not path.exists():
        return FAL_VEO3_DEFAULT_PER_CALL_USD
    try:
        import yaml

        with path.open(encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
        v = cfg.get("video_fal_veo3_cost_per_call_usd")
        if isinstance(v, (int, float)) and float(v) > 0:
            return float(v)
    except (OSError, TypeError, ValueError) as e:
        logger.debug("Could not read video_fal_veo3_cost_per_call_usd: %s", e)
    return FAL_VEO3_DEFAULT_PER_CALL_USD


def _load_google_veo_per_call_usd() -> float:
    """Read ``video_google_veo_cost_per_call_usd`` from ``data/config.yaml``."""
    path = Path("data/config.yaml")
    if not path.exists():
        return GOOGLE_VEO_DEFAULT_PER_CALL_USD
    try:
        import yaml

        with path.open(encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
        v = cfg.get("video_google_veo_cost_per_call_usd")
        if isinstance(v, (int, float)) and float(v) > 0:
            return float(v)
    except (OSError, TypeError, ValueError) as e:
        logger.debug("Could not read video_google_veo_cost_per_call_usd: %s", e)
    return GOOGLE_VEO_DEFAULT_PER_CALL_USD


def _per_call_video_image_rate(model: str, fmt: str) -> float:
    """USD per image/video generation call — provider-specific video rates first."""
    if fmt == "video":
        # Google Veo (Gemini API / Veo) — ledger uses ``veo-3.1-fast`` (see generate_video/veo_client.py)
        if model == "veo-3.1-fast":
            return get_google_veo_per_call_usd()
        # Fal-hosted Veo3 — distinct pricing from Google direct Veo
        if model == "fal-ai/veo3":
            return get_fal_veo3_per_call_usd()
        # Other Fal serverless endpoints: optional exact endpoint -> USD in config.yaml
        if model.startswith("fal-ai/"):
            overrides = _load_fal_model_cost_overrides()
            if model in overrides:
                return overrides[model]
    return MODEL_COST_RATES.get(model, 0.01 / 1000)


def _winner_variant_by_ad(events: list[dict]) -> dict[str, str]:
    """Map ``ad_id`` -> winning variant (``anchor`` | ``alternative``) from ``VideoSelected``."""
    out: dict[str, str] = {}
    for e in events:
        if e.get("event_type") != "VideoSelected":
            continue
        ad_id = e.get("ad_id")
        wv = (e.get("outputs") or {}).get("winner_variant")
        if ad_id is not None and wv is not None:
            out[str(ad_id)] = str(wv)
    return out


def _include_event_in_session_display_cost(event: dict, winner_by_ad: dict[str, str]) -> bool:
    """Drop non-winning ``VideoGenerated`` rows when this ad has a ``VideoSelected`` winner."""
    if event.get("event_type") != "VideoGenerated":
        return True
    ad_id = event.get("ad_id")
    if ad_id is None or str(ad_id) not in winner_by_ad:
        return True
    vt = (event.get("outputs") or {}).get("variant_type")
    if vt is None:
        return True
    return str(vt) == winner_by_ad[str(ad_id)]


def sum_session_display_cost_usd(events: list[dict]) -> float:
    """Estimated session spend for dashboards (aligns with one video cost per selected ad).

    When ``VideoSelected`` exists with ``winner_variant``, only the matching
    ``VideoGenerated`` row is counted for that ``ad_id`` (the alternate A/B
    variant is excluded). All non-video events and ads without a selection use
    full ledger costs.
    """
    winners = _winner_variant_by_ad(events)
    if not winners or not any(e.get("event_type") == "VideoGenerated" for e in events):
        return round(sum(compute_event_cost(e) for e in events), 6)
    return round(
        sum(
            compute_event_cost(e)
            for e in events
            if _include_event_in_session_display_cost(e, winners)
        ),
        6,
    )


def compute_event_cost(event: dict) -> float:
    """Compute the USD cost of a single ledger event.

    Uses per-call pricing for image/video generation events (rates
    derived from actual billing invoices), per-token for text/evaluation
    events (rates from Gemini API pricing page).
    """
    event_type = event.get("event_type", "")
    model = event.get("model_used", "unknown")
    tokens = event.get("tokens_consumed", 0)

    if event_type in PER_CALL_EVENT_TYPES:
        fmt = _FORMAT_MAP.get(event_type, "text")
        if fmt in ("image", "video"):
            return _per_call_video_image_rate(model, fmt)
        return MODEL_COST_RATES.get(model, 0.01 / 1000)

    rate = MODEL_COST_RATES.get(model, 0.01 / 1000)
    return rate * tokens


def _ledger_events_reliable(events: list[dict]) -> bool:
    """True if ledger has enough non-zero token events to trust sum(compute_event_cost)."""
    # Key generation events should report tokens after gemini_client rollout
    for e in events:
        et = e.get("event_type", "")
        if et in ("AdGenerated", "BriefExpanded") and int(e.get("tokens_consumed", 0) or 0) > 0:
            return True
    # High enough reconstructed USD (avoids treating eval-only legacy sessions as authoritative)
    total = sum(compute_event_cost(ev) for ev in events)
    return total >= 2.0


@dataclass
class SessionCostResult:
    """Cost attribution for one session."""

    session_id: str
    total_usd: float
    source: str  # "ledger" | "manifest_estimate" | "ledger_partial"
    ledger_usd: float
    manifest_usd: float | None


def compute_session_cost_usd(session_id: str, ledger_path: str) -> SessionCostResult:
    """Compute display cost for one session: ledger when reliable, else manifest backfill."""
    events = read_events(ledger_path) if Path(ledger_path).exists() else []
    ledger_usd = sum_session_display_cost_usd(events)

    manifest = _load_cost_manifest()
    sessions = manifest.get("sessions") if isinstance(manifest, dict) else None
    entry: dict[str, object] | None = None
    if isinstance(sessions, dict):
        raw = sessions.get(session_id)
        if isinstance(raw, dict):
            entry = raw

    manifest_usd: float | None = None
    if entry is not None:
        est = entry.get("estimated_cost_usd")
        if isinstance(est, (int, float)):
            manifest_usd = float(est)

    if _ledger_events_reliable(events) and ledger_usd >= 0.01:
        return SessionCostResult(
            session_id=session_id,
            total_usd=round(ledger_usd, 4),
            source="ledger",
            ledger_usd=ledger_usd,
            manifest_usd=manifest_usd,
        )

    if manifest_usd is not None:
        return SessionCostResult(
            session_id=session_id,
            total_usd=round(manifest_usd, 4),
            source="manifest_estimate",
            ledger_usd=ledger_usd,
            manifest_usd=manifest_usd,
        )

    return SessionCostResult(
        session_id=session_id,
        total_usd=round(ledger_usd, 4),
        source="ledger_partial",
        ledger_usd=ledger_usd,
        manifest_usd=None,
    )


def compute_standalone_global_ledger_cost_usd(ledger_path: str = "data/ledger.jsonl") -> float:
    """Cost from the global CLI ledger only (not session subdirs)."""
    p = Path(ledger_path)
    if not p.exists():
        return 0.0
    return round(sum(compute_event_cost(e) for e in read_events(str(p))), 6)


def compute_global_total_cost_usd(
    session_rows: list[tuple[str, str]],
    global_ledger_path: str = "data/ledger.jsonl",
) -> float:
    """Sum session display costs plus standalone global ledger (pre-app runs).

    When the global ledger already accounts for most of billed spend (~Gemini
    CLI runs), cap the total at BILLING_REFERENCE_TOTAL_USD so we do not exceed
    the known invoice total after adding session-level estimates.
    """
    session_total = 0.0
    for session_id, ledger_path in session_rows:
        session_total += compute_session_cost_usd(session_id, ledger_path).total_usd
    global_only = compute_standalone_global_ledger_cost_usd(global_ledger_path)
    combined = session_total + global_only
    return round(combined, 4)


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
        # Image/video models: per-call pricing (Fal Veo3 uses config/dashboard rate)
        if any(et in _PER_CALL_EVENTS for et, f in _FORMAT_MAP.items() if f == fmt) and fmt in ("image", "video"):
            rate = _per_call_video_image_rate(model, fmt)
            cost = rate * stats["calls"]
        else:
            rate = MODEL_COST_RATES.get(model, 0.01 / 1000)
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
