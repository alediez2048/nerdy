"""Pipeline orchestrator — PH-03.

One implementation of the image / copy ad-generation pipeline,
reachable from any entry point (CLI, Celery worker, future webhook,
ad-hoc scripts). Progress reporting is pluggable via the
:class:`ProgressSink` protocol so each entry point picks a sink that
matches its medium (stdout / Redis / Null).

The video pipeline in ``app.workers.tasks.pipeline_task._run_video_pipeline``
is intentionally out of scope here — it has a per-ad rather than
batch-loop shape and a different progress event vocabulary. A future
phase may converge it.
"""

from __future__ import annotations

import logging
from typing import Any

from app.workers.progress import (
    BATCH_COMPLETE,
    BATCH_START,
    PIPELINE_COMPLETE,
)
from iterate.batch_processor import (
    BatchResult,
    PipelineResult,
    create_batches,
    process_batch,
    write_batch_checkpoint,
)
from iterate.pipeline_runner import PipelineConfig, RunSummary, generate_briefs
from iterate.progress_sinks import NullProgressSink, ProgressSink

logger = logging.getLogger(__name__)


def _compute_avg_score(ledger_path: str) -> float:
    """Average aggregate score across published ads in the ledger.

    Uses the typed reader from PH-01 so a schema change to AdPublished
    fails loud at import time, not silently here.
    """
    try:
        from iterate.ledger_events import AdPublished
        from iterate.ledger_reader import iter_typed_events

        scores: list[float] = []
        for ev in iter_typed_events(ledger_path):
            if not isinstance(ev, AdPublished):
                continue
            agg = ev.outputs.get("aggregate_score")
            if isinstance(agg, (int, float)):
                scores.append(float(agg))
        return round(sum(scores) / len(scores), 2) if scores else 0.0
    except Exception:
        logger.debug("avg-score compute failed for %s", ledger_path, exc_info=True)
        return 0.0


def _compute_cost_so_far(ledger_path: str) -> float:
    """Display cost summed over the ledger so far (matches dashboard cost)."""
    try:
        from evaluate.cost_reporter import sum_session_display_cost_usd
        from iterate.ledger_reader import read_dicts

        return round(sum_session_display_cost_usd(read_dicts(ledger_path)), 4)
    except Exception:
        logger.debug("cost-so-far compute failed for %s", ledger_path, exc_info=True)
        return 0.0


def _build_batch_processor_config(config: PipelineConfig) -> dict[str, Any]:
    """Build the dict that ``process_batch`` expects from the dataclass config.

    Centralises the previously-duplicated config-normalisation code
    that lived inline in ``pipeline_runner.run_pipeline`` and
    ``app/workers/tasks/pipeline_task._run_image_pipeline``.
    """
    return {
        "ledger_path": config.ledger_path,
        "text_threshold": config.text_threshold,
        "image_attribute_threshold": config.image_attribute_threshold,
        "coherence_threshold": config.coherence_threshold,
        "max_cycles": config.max_cycles,
        "global_seed": config.global_seed,
        "improvable_range": [5.5, 7.0],
        "image_enabled": config.image_enabled,
        "persona": config.persona,
        "key_message": config.key_message,
        "creative_brief": config.creative_brief,
        "copy_on_image": config.copy_on_image,
        "aspect_ratios": config.aspect_ratios,
    }


class PipelineOrchestrator:
    """Single source of truth for the image/copy pipeline batch loop.

    Two entry points use this today: ``run_pipeline.py:main`` (CLI) via
    ``pipeline_runner.run_pipeline`` and
    ``app.workers.tasks.pipeline_task._run_image_pipeline`` (Celery).
    A third entry point would be a new sink + a ~15-line wrapper.
    """

    __slots__ = ("progress_sink",)

    def __init__(self, *, progress_sink: ProgressSink | None = None) -> None:
        self.progress_sink = progress_sink or NullProgressSink()

    def run(self, config: PipelineConfig) -> RunSummary:
        logger.info(
            "Starting pipeline: %d batches x %d ads, %d cycles, dry_run=%s",
            config.num_batches, config.batch_size, config.max_cycles, config.dry_run,
        )

        briefs = generate_briefs(config)
        batches = create_batches(briefs, config.batch_size)
        processor_config = _build_batch_processor_config(config)

        totals = {"generated": 0, "published": 0, "discarded": 0, "regenerated": 0}
        batch_results: list[BatchResult] = []
        cost_so_far = 0.0
        avg_score = 0.0

        for batch_num, batch_briefs in enumerate(batches, 1):
            avg_score = _compute_avg_score(config.ledger_path)
            self.progress_sink.emit(BATCH_START, {
                "cycle": 1,
                "batch": batch_num,
                "ads_generated": totals["generated"],
                "ads_evaluated": totals["generated"],
                "ads_published": totals["published"],
                "current_score_avg": avg_score,
                "cost_so_far": cost_so_far,
            })

            batch_result = process_batch(
                briefs=batch_briefs,
                batch_num=batch_num,
                config=processor_config,
                dry_run=config.dry_run,
            )
            write_batch_checkpoint(batch_num, batch_result, config.ledger_path)

            batch_results.append(batch_result)
            totals["generated"] += batch_result.generated
            totals["published"] += batch_result.published
            totals["discarded"] += batch_result.discarded
            totals["regenerated"] += batch_result.regenerated

            cost_so_far = _compute_cost_so_far(config.ledger_path)
            avg_score = _compute_avg_score(config.ledger_path)

            self.progress_sink.emit(BATCH_COMPLETE, {
                "cycle": 1,
                "batch": batch_num,
                "ads_generated": totals["generated"],
                "ads_evaluated": totals["generated"],
                "ads_published": totals["published"],
                "current_score_avg": avg_score,
                "cost_so_far": cost_so_far,
            })

            logger.info(
                "Batch %d: generated=%d, published=%d, discarded=%d",
                batch_num, batch_result.generated, batch_result.published,
                batch_result.discarded,
            )

        pipeline_result = PipelineResult.from_batches(batch_results)
        summary = RunSummary(
            total_briefs=len(briefs),
            batches_completed=pipeline_result.batches_completed,
            total_generated=pipeline_result.total_generated,
            total_published=pipeline_result.total_published,
            total_discarded=pipeline_result.total_discarded,
            total_regenerated=pipeline_result.total_regenerated,
            total_escalated=pipeline_result.total_escalated,
            batch_results=batch_results,
        )

        self.progress_sink.emit(PIPELINE_COMPLETE, {
            "cycle": 1,
            "batch": len(batches),
            "ads_generated": summary.total_generated,
            "ads_evaluated": summary.total_generated,
            "ads_published": summary.total_published,
            "current_score_avg": avg_score,
            "cost_so_far": cost_so_far,
        })

        logger.info(
            "Pipeline complete: %d briefs, %d generated, %d published, %d discarded",
            summary.total_briefs, summary.total_generated,
            summary.total_published, summary.total_discarded,
        )

        return summary
