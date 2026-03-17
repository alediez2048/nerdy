# Ad-Ops-Autopilot — Pipeline Celery task (PA-04)
# Runs the REAL pipeline (not simulation) with progress publishing.
import logging
import math

from sqlalchemy.orm import Session as DBSession

from app.db import SessionLocal, init_db
from app.models.session import Session as SessionModel
from app.workers.celery_app import celery_app
from app.workers.progress import (
    BATCH_COMPLETE,
    BATCH_START,
    PIPELINE_COMPLETE,
    PIPELINE_ERROR,
    publish_progress,
)

logger = logging.getLogger(__name__)


@celery_app.task(bind=True)
def run_pipeline_session(self, session_id: str) -> dict:
    """Run the real ad generation pipeline with progress publishing."""
    init_db()
    db: DBSession = SessionLocal()
    try:
        session_row = db.query(SessionModel).filter(
            SessionModel.session_id == session_id
        ).first()
        if not session_row:
            raise ValueError(f"Session {session_id} not found")

        session_row.status = "running"
        db.commit()

        # Extract config from session
        config = session_row.config or {}
        ad_count = config.get("ad_count", 10)
        cycle_count = config.get("cycle_count", 3)
        quality_threshold = config.get("quality_threshold", 7.0)
        image_enabled = config.get("image_enabled", True)
        persona_raw = config.get("persona", "auto")
        persona = persona_raw if persona_raw and persona_raw != "auto" else None
        key_message = config.get("key_message", "")
        creative_brief = config.get("creative_brief", "auto")
        copy_on_image = config.get("copy_on_image", False)
        ledger_path = session_row.ledger_path or "data/ledger.jsonl"

        batch_size = min(10, ad_count)
        num_batches = max(1, math.ceil(ad_count / batch_size))

        # Import pipeline modules
        from iterate.pipeline_runner import PipelineConfig, generate_briefs
        from iterate.batch_processor import (
            create_batches,
            process_batch,
            write_batch_checkpoint,
        )

        pipeline_config = {
            "ledger_path": ledger_path,
            "text_threshold": quality_threshold,
            "image_attribute_threshold": 0.8,
            "coherence_threshold": 6.0,
            "max_cycles": cycle_count,
            "global_seed": f"session_{session_id}",
            "improvable_range": [5.5, 7.0],
            "image_enabled": image_enabled,
            "persona": persona,
            "key_message": key_message,
            "creative_brief": creative_brief,
            "copy_on_image": copy_on_image,
        }

        # Generate briefs
        pconfig = PipelineConfig(
            num_batches=num_batches,
            batch_size=batch_size,
            max_cycles=cycle_count,
            ledger_path=ledger_path,
            dry_run=False,
            global_seed=f"session_{session_id}",
            persona=persona,
        )
        briefs = generate_briefs(pconfig)
        batches = create_batches(briefs, batch_size)

        # Track running totals
        total_generated = 0
        total_published = 0
        total_discarded = 0
        total_regenerated = 0
        cost_so_far = 0.0

        for batch_num, batch_briefs in enumerate(batches, 1):
            publish_progress(session_id, {
                "type": BATCH_START,
                "cycle": 1,
                "batch": batch_num,
                "ads_generated": total_generated,
                "ads_evaluated": total_generated,
                "ads_published": total_published,
                "current_score_avg": 7.0,
                "cost_so_far": cost_so_far,
            })

            batch_result = process_batch(
                briefs=batch_briefs,
                batch_num=batch_num,
                config=pipeline_config,
                dry_run=False,
            )

            write_batch_checkpoint(batch_num, batch_result, ledger_path)

            total_generated += batch_result.generated
            total_published += batch_result.published
            total_discarded += batch_result.discarded
            total_regenerated += batch_result.regenerated
            cost_so_far += batch_result.generated * 0.2  # rough estimate

            publish_progress(session_id, {
                "type": BATCH_COMPLETE,
                "cycle": 1,
                "batch": batch_num,
                "ads_generated": total_generated,
                "ads_evaluated": total_generated,
                "ads_published": total_published,
                "current_score_avg": 7.0,
                "cost_so_far": cost_so_far,
            })

            logger.info(
                "Session %s batch %d/%d: generated=%d published=%d",
                session_id, batch_num, len(batches),
                batch_result.generated, batch_result.published,
            )

        # Pipeline complete
        publish_progress(session_id, {
            "type": PIPELINE_COMPLETE,
            "cycle": 1,
            "batch": len(batches),
            "ads_generated": total_generated,
            "ads_evaluated": total_generated,
            "ads_published": total_published,
            "current_score_avg": 7.0,
            "cost_so_far": cost_so_far,
        })

        # Update session in DB
        session_row = db.query(SessionModel).filter(
            SessionModel.session_id == session_id
        ).first()
        if session_row:
            session_row.status = "completed"
            session_row.results_summary = {
                "ads_generated": total_generated,
                "ads_published": total_published,
                "ads_discarded": total_discarded,
                "ads_regenerated": total_regenerated,
                "avg_score": 7.0,
                "cost_so_far": cost_so_far,
            }
            db.commit()

        return {
            "status": "completed",
            "ads_generated": total_generated,
            "ads_published": total_published,
        }

    except Exception as e:
        logger.error("Pipeline failed for session %s: %s", session_id, e)
        publish_progress(session_id, {
            "type": PIPELINE_ERROR,
            "cycle": 0,
            "batch": 0,
            "ads_generated": 0,
            "ads_evaluated": 0,
            "ads_published": 0,
            "current_score_avg": 0.0,
            "cost_so_far": 0.0,
            "error": str(e),
        })
        session_row = db.query(SessionModel).filter(
            SessionModel.session_id == session_id
        ).first()
        if session_row:
            session_row.status = "failed"
            db.commit()
        raise
    finally:
        db.close()
