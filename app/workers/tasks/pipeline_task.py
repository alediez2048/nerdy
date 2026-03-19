# Ad-Ops-Autopilot — Pipeline Celery task (PA-04, PC-03)
# Routes to image or video pipeline based on session_type.
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
    VIDEO_AD_COMPLETE,
    VIDEO_AD_START,
    VIDEO_EVALUATING,
    VIDEO_GENERATING,
    VIDEO_PIPELINE_COMPLETE,
    VIDEO_PIPELINE_START,
    publish_progress,
)

logger = logging.getLogger(__name__)


def _run_image_pipeline(
    session_id: str,
    config: dict,
    ledger_path: str,
    db: DBSession,
) -> dict:
    """Run the image ad generation pipeline (original PA-04 flow)."""
    ad_count = config.get("ad_count", 10)
    cycle_count = config.get("cycle_count", 3)
    quality_threshold = config.get("quality_threshold", 7.0)
    image_enabled = config.get("image_enabled", True)
    persona_raw = config.get("persona", "auto")
    persona = persona_raw if persona_raw and persona_raw != "auto" else None
    key_message = config.get("key_message", "")
    creative_brief = config.get("creative_brief", "auto")
    copy_on_image = config.get("copy_on_image", False)
    aspect_ratio_single = config.get("aspect_ratio")
    aspect_ratios = (
        [aspect_ratio_single]
        if aspect_ratio_single
        else config.get("aspect_ratios", ["1:1"])
    )

    batch_size = min(10, ad_count)
    num_batches = max(1, math.ceil(ad_count / batch_size))

    from iterate.batch_processor import (
        create_batches,
        process_batch,
        write_batch_checkpoint,
    )
    from iterate.pipeline_runner import PipelineConfig, generate_briefs

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
        "aspect_ratios": aspect_ratios,
    }

    audience_raw = config.get("audience")
    campaign_goal_raw = config.get("campaign_goal")

    pconfig = PipelineConfig(
        num_batches=num_batches,
        batch_size=batch_size,
        max_cycles=cycle_count,
        ledger_path=ledger_path,
        dry_run=False,
        global_seed=f"session_{session_id}",
        persona=persona,
        audience=(
            audience_raw if audience_raw and audience_raw != "auto" else None
        ),
        campaign_goal=(
            campaign_goal_raw
            if campaign_goal_raw and campaign_goal_raw != "auto"
            else None
        ),
        key_message=key_message,
    )
    briefs = generate_briefs(pconfig)
    batches = create_batches(briefs, batch_size)

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
        cost_so_far += batch_result.generated * 0.2

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

    return {
        "ads_generated": total_generated,
        "ads_published": total_published,
        "ads_discarded": total_discarded,
        "ads_regenerated": total_regenerated,
        "avg_score": 7.0,
        "cost_so_far": cost_so_far,
    }


def _run_video_pipeline(
    session_id: str,
    config: dict,
    ledger_path: str,
    db: DBSession,
) -> dict:
    """Run the video ad generation pipeline (PC-03)."""
    import os

    from generate_video.kling_client import KlingClient
    from generate_video.orchestrator import (
        generate_video_variants,
        select_best_video,
        should_skip_video_ad,
    )
    from generate_video.video_spec import build_video_spec

    from evaluate.video_evaluator import (
        check_video_coherence,
        compute_composite_score,
        evaluate_video_attributes,
    )
    from iterate.ledger import log_event
    from iterate.pipeline_runner import PipelineConfig, generate_briefs

    video_count = config.get("video_count", 3)
    persona_raw = config.get("persona", "auto")
    persona = persona_raw if persona_raw and persona_raw != "auto" else None
    key_message = config.get("key_message", "")
    audience_raw = config.get("audience")
    campaign_goal_raw = config.get("campaign_goal")

    kling_api_key = os.environ.get("KLING_API_KEY", "")
    client = KlingClient(api_key=kling_api_key)

    output_dir = f"output/videos/session_{session_id}"

    pconfig = PipelineConfig(
        num_batches=1,
        batch_size=video_count,
        max_cycles=1,
        ledger_path=ledger_path,
        dry_run=False,
        global_seed=f"session_{session_id}",
        persona=persona,
        audience=(
            audience_raw if audience_raw and audience_raw != "auto" else None
        ),
        campaign_goal=(
            campaign_goal_raw
            if campaign_goal_raw and campaign_goal_raw != "auto"
            else None
        ),
        key_message=key_message,
    )
    briefs = generate_briefs(pconfig)[:video_count]

    publish_progress(session_id, {
        "type": VIDEO_PIPELINE_START,
        "videos_total": video_count,
        "videos_generated": 0,
        "videos_selected": 0,
        "videos_blocked": 0,
        "cost_so_far": 0.0,
    })

    videos_generated = 0
    videos_selected = 0
    videos_blocked = 0
    cost_so_far = 0.0

    for i, brief in enumerate(briefs):
        ad_id = f"ad_brief_{brief.get('brief_id', str(i + 1).zfill(3))}_c0"

        if should_skip_video_ad(ad_id, ledger_path):
            logger.info("Skipping already-processed video ad %s", ad_id)
            continue

        publish_progress(session_id, {
            "type": VIDEO_AD_START,
            "ad_index": i + 1,
            "ad_id": ad_id,
            "videos_total": video_count,
            "videos_generated": videos_generated,
            "videos_selected": videos_selected,
            "cost_so_far": cost_so_far,
        })

        try:
            spec = build_video_spec(
                expanded_brief=brief,
                session_config=config,
                ad_copy=brief.get("copy", {}),
            )

            publish_progress(session_id, {
                "type": VIDEO_GENERATING,
                "ad_index": i + 1,
                "ad_id": ad_id,
                "videos_total": video_count,
                "videos_generated": videos_generated,
                "cost_so_far": cost_so_far,
            })

            from generate.seeds import get_ad_seed
            seed = get_ad_seed(f"session_{session_id}", ad_id, 0)

            variants = generate_video_variants(
                spec=spec,
                ad_id=ad_id,
                seed=seed,
                output_dir=output_dir,
                ledger_path=ledger_path,
                kling_client=client,
            )
            videos_generated += len(variants)

            publish_progress(session_id, {
                "type": VIDEO_EVALUATING,
                "ad_index": i + 1,
                "ad_id": ad_id,
                "videos_total": video_count,
                "videos_generated": videos_generated,
                "cost_so_far": cost_so_far,
            })

            eval_results = {}
            coherence_results = {}
            for v in variants:
                ev = evaluate_video_attributes(
                    v.video_path, v.ad_id, ledger_path
                )
                co = check_video_coherence(
                    v.video_path,
                    brief.get("copy", {}).get("primary_text", ""),
                    v.ad_id,
                    ledger_path,
                )
                eval_results[v.variant_type] = ev
                coherence_results[v.variant_type] = co

                log_event(ledger_path, {
                    "event_type": "VideoEvaluated",
                    "ad_id": ad_id,
                    "brief_id": ad_id.split("_c")[0] if "_c" in ad_id else ad_id,
                    "cycle_number": 0,
                    "action": f"video_{v.variant_type}_evaluated",
                    "tokens_consumed": 0,
                    "model_used": "gemini-2.0-flash",
                    "seed": str(v.seed),
                    "outputs": {
                        "variant_type": v.variant_type,
                        "attributes": ev.attributes,
                        "attribute_pass_pct": ev.pass_percentage,
                        "coherence_scores": co.scores,
                        "coherence_avg": co.average,
                    },
                })

            winner = select_best_video(variants, eval_results, coherence_results)

            if winner:
                ev = eval_results[winner.variant_type]
                co = coherence_results[winner.variant_type]
                composite = compute_composite_score(ev, co)
                log_event(ledger_path, {
                    "event_type": "VideoSelected",
                    "ad_id": ad_id,
                    "brief_id": ad_id.split("_c")[0] if "_c" in ad_id else ad_id,
                    "cycle_number": 0,
                    "action": "video_selected",
                    "tokens_consumed": 0,
                    "model_used": winner.model_used,
                    "seed": str(winner.seed),
                    "outputs": {
                        "winner_video_path": winner.video_path,
                        "winner_variant": winner.variant_type,
                        "composite_score": composite,
                        "attribute_pass_pct": ev.pass_percentage,
                        "coherence_avg": co.average,
                    },
                })
                videos_selected += 1
                cost_so_far += winner.credits_consumed * 0.001
            else:
                log_event(ledger_path, {
                    "event_type": "VideoBlocked",
                    "ad_id": ad_id,
                    "brief_id": ad_id.split("_c")[0] if "_c" in ad_id else ad_id,
                    "cycle_number": 0,
                    "action": "video_blocked",
                    "tokens_consumed": 0,
                    "model_used": "kling-v2.6-pro",
                    "seed": "0",
                    "outputs": {"reason": "all_variants_failed_thresholds"},
                })
                videos_blocked += 1

        except Exception as e:
            logger.error("Video pipeline error for ad %s: %s", ad_id, e)
            videos_blocked += 1

        publish_progress(session_id, {
            "type": VIDEO_AD_COMPLETE,
            "ad_index": i + 1,
            "ad_id": ad_id,
            "videos_total": video_count,
            "videos_generated": videos_generated,
            "videos_selected": videos_selected,
            "videos_blocked": videos_blocked,
            "cost_so_far": cost_so_far,
        })

    publish_progress(session_id, {
        "type": VIDEO_PIPELINE_COMPLETE,
        "videos_total": video_count,
        "videos_generated": videos_generated,
        "videos_selected": videos_selected,
        "videos_blocked": videos_blocked,
        "cost_so_far": cost_so_far,
    })

    return {
        "videos_generated": videos_generated,
        "videos_selected": videos_selected,
        "videos_blocked": videos_blocked,
        "cost_so_far": cost_so_far,
    }


@celery_app.task(bind=True)
def run_pipeline_session(self, session_id: str) -> dict:
    """Run the ad generation pipeline — routes by session_type."""
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

        config = session_row.config or {}
        ledger_path = session_row.ledger_path or "data/ledger.jsonl"
        session_type = config.get("session_type", "image")

        if session_type == "video":
            result = _run_video_pipeline(session_id, config, ledger_path, db)
            summary = {
                "videos_generated": result.get("videos_generated", 0),
                "videos_selected": result.get("videos_selected", 0),
                "videos_blocked": result.get("videos_blocked", 0),
                "cost_so_far": result.get("cost_so_far", 0.0),
            }
        else:
            result = _run_image_pipeline(session_id, config, ledger_path, db)
            summary = {
                "ads_generated": result.get("ads_generated", 0),
                "ads_published": result.get("ads_published", 0),
                "ads_discarded": result.get("ads_discarded", 0),
                "ads_regenerated": result.get("ads_regenerated", 0),
                "avg_score": result.get("avg_score", 7.0),
                "cost_so_far": result.get("cost_so_far", 0.0),
            }

        session_row = db.query(SessionModel).filter(
            SessionModel.session_id == session_id
        ).first()
        if session_row:
            session_row.status = "completed"
            session_row.results_summary = summary
            db.commit()

        return {"status": "completed", **summary}

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
