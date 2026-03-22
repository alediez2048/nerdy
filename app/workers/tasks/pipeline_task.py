# Ad-Ops-Autopilot — Pipeline Celery task (PA-04, PC-03)
# Routes to image, copy-only, or video pipeline based on session_type.
import json
import logging
import math
import time
from pathlib import Path

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


def _debug_log(hypothesis_id: str, location: str, message: str, data: dict) -> None:
    # region agent log
    try:
        debug_path = Path("/app/.cursor/debug-c163a9.log")
        debug_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "sessionId": "c163a9",
            "runId": "pre-fix",
            "hypothesisId": hypothesis_id,
            "location": location,
            "message": message,
            "data": data,
            "timestamp": int(time.time() * 1000),
        }
        with debug_path.open("a") as f:
            f.write(json.dumps(payload) + "\n")
    except Exception:
        pass
    # endregion


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

    def _compute_avg_score() -> float:
        """Compute real average score from AdPublished events in session ledger."""
        try:
            from iterate.ledger import read_events as _read
            events = _read(ledger_path)
            scores = [
                e.get("outputs", {}).get("aggregate_score", 0.0)
                for e in events
                if e.get("event_type") == "AdPublished"
                and isinstance(e.get("outputs", {}).get("aggregate_score"), (int, float))
            ]
            return round(sum(scores) / len(scores), 2) if scores else 0.0
        except Exception:
            return 0.0

    for batch_num, batch_briefs in enumerate(batches, 1):
        current_score_avg = _compute_avg_score()
        publish_progress(session_id, {
            "type": BATCH_START,
            "cycle": 1,
            "batch": batch_num,
            "ads_generated": total_generated,
            "ads_evaluated": total_generated,
            "ads_published": total_published,
            "current_score_avg": current_score_avg,
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
        try:
            from evaluate.cost_reporter import sum_session_display_cost_usd
            from iterate.ledger import read_events

            cost_so_far = round(sum_session_display_cost_usd(read_events(ledger_path)), 4)
        except Exception:
            cost_so_far += batch_result.generated * 0.2

        current_score_avg = _compute_avg_score()
        publish_progress(session_id, {
            "type": BATCH_COMPLETE,
            "cycle": 1,
            "batch": batch_num,
            "ads_generated": total_generated,
            "ads_evaluated": total_generated,
            "ads_published": total_published,
            "current_score_avg": current_score_avg,
            "cost_so_far": cost_so_far,
        })

        logger.info(
            "Session %s batch %d/%d: generated=%d published=%d",
            session_id, batch_num, len(batches),
            batch_result.generated, batch_result.published,
        )

    final_avg_score = _compute_avg_score()
    publish_progress(session_id, {
        "type": PIPELINE_COMPLETE,
        "cycle": 1,
        "batch": len(batches),
        "ads_generated": total_generated,
        "ads_evaluated": total_generated,
        "ads_published": total_published,
        "current_score_avg": final_avg_score,
        "cost_so_far": cost_so_far,
    })

    return {
        "ads_generated": total_generated,
        "ads_published": total_published,
        "ads_discarded": total_discarded,
        "ads_regenerated": total_regenerated,
        "avg_score": final_avg_score,
        "cost_so_far": cost_so_far,
    }


def _run_video_pipeline(
    session_id: str,
    config: dict,
    ledger_path: str,
    db: DBSession,
) -> dict:
    """Run the video ad generation pipeline (PC-03 + Fal.ai migration)."""
    from generate_video.factory import build_video_client
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
    from generate.ad_generator import generate_ad
    from generate.brief_expansion import expand_brief
    from generate.seeds import get_ad_seed
    from iterate.ledger import log_event
    from iterate.pipeline_runner import PipelineConfig, generate_briefs

    video_count = config.get("video_count", 3)
    persona_raw = config.get("persona", "auto")
    persona = persona_raw if persona_raw and persona_raw != "auto" else None
    key_message = config.get("key_message", "")
    audience_raw = config.get("audience")
    campaign_goal_raw = config.get("campaign_goal")

    # region agent log
    _debug_log(
        "H1",
        "app/workers/tasks/pipeline_task.py:_run_video_pipeline:start",
        "video pipeline start",
        {
            "session_id": session_id,
            "video_count": video_count,
            "persona": persona_raw,
            "audience": audience_raw,
            "campaign_goal": campaign_goal_raw,
            "ledger_path": ledger_path,
        },
    )
    # endregion

    video_provider = config.get("video_provider")
    client_kwargs: dict = {}
    if video_provider == "fal":
        fal_model = (config.get("video_fal_model") or "").strip()
        if fal_model:
            client_kwargs["model"] = fal_model
    client = build_video_client(provider=video_provider, **client_kwargs)
    # region agent log
    _debug_log(
        "H7",
        "app/workers/tasks/pipeline_task.py:_run_video_pipeline:client",
        "video client built",
        {
            "session_id": session_id,
            "resolved_provider": getattr(client, "model_used", "unknown"),
            "requested_provider": video_provider,
        },
    )
    # endregion

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
        "video_variants_generated": 0,
        "videos_selected": 0,
        "videos_blocked": 0,
        "cost_so_far": 0.0,
    })

    # videos_generated = video ads that produced ≥1 variant (user-facing "videos")
    # video_variants_generated = Fal API jobs (anchor + alt per ad)
    videos_generated = 0
    video_variants_generated = 0
    videos_selected = 0
    videos_blocked = 0
    cost_so_far = 0.0

    for i, brief in enumerate(briefs):
        brief_id = brief.get("brief_id", str(i + 1).zfill(3))
        seed = get_ad_seed(f"session_{session_id}", brief_id, 0)
        ad_id = f"ad_{brief_id}_c0_{seed}"

        # region agent log
        _debug_log(
            "H2",
            "app/workers/tasks/pipeline_task.py:_run_video_pipeline:brief",
            "video brief before spec build",
            {
                "session_id": session_id,
                "ad_id": ad_id,
                "brief_id": brief.get("brief_id"),
                "brief_keys": sorted(list(brief.keys())),
                "has_copy": bool(brief.get("copy")),
                "copy_keys": sorted(list((brief.get("copy") or {}).keys())),
            },
        )
        # endregion

        if should_skip_video_ad(ad_id, ledger_path):
            logger.info("Skipping already-processed video ad %s", ad_id)
            continue

        publish_progress(session_id, {
            "type": VIDEO_AD_START,
            "ad_index": i + 1,
            "ad_id": ad_id,
            "videos_total": video_count,
            "videos_generated": videos_generated,
            "video_variants_generated": video_variants_generated,
            "videos_selected": videos_selected,
            "cost_so_far": cost_so_far,
        })

        try:
            expanded = expand_brief(brief, persona=persona, ledger_path=ledger_path)
            ad = generate_ad(
                expanded,
                seed=seed,
                cycle_number=0,
                ledger_path=ledger_path,
                creative_brief=config.get("creative_brief", "auto"),
            )
            ad_id = ad.ad_id
            ad_copy = ad.to_evaluator_input()

            # Evaluate copy quality (was missing in video pipeline)
            try:
                from evaluate.evaluator import evaluate_ad
                copy_eval = evaluate_ad(
                    ad_copy,
                    campaign_goal=config.get("campaign_goal", "conversion"),
                    audience=config.get("audience", "parents"),
                    ledger_path=ledger_path,
                    persona=persona,
                )
                log_event(ledger_path, {
                    "event_type": "AdEvaluated",
                    "ad_id": ad_id,
                    "brief_id": brief.get("brief_id", str(i + 1).zfill(3)),
                    "cycle_number": 0,
                    "action": "evaluation",
                    "tokens_consumed": copy_eval.tokens_consumed,
                    "model_used": "gemini-2.0-flash",
                    "seed": str(seed),
                    "inputs": {},
                    "outputs": {
                        "aggregate_score": copy_eval.aggregate_score,
                        "scores": {
                            dim: {"score": copy_eval.dimension_scores.get(dim, 0), "rationale": copy_eval.rationales.get(dim, "")}
                            for dim in copy_eval.dimension_scores
                        },
                    },
                })
            except Exception as e:
                logger.warning("Copy evaluation failed for video ad %s: %s", ad_id, e)

            spec = build_video_spec(
                expanded_brief=brief,
                session_config=config,
                ad_copy=ad_copy,
            )

            if getattr(spec, "spec_extraction_tokens", 0) > 0:
                log_event(ledger_path, {
                    "event_type": "VideoSpecExtracted",
                    "ad_id": ad_id,
                    "brief_id": brief.get("brief_id", "unknown"),
                    "cycle_number": 0,
                    "action": "video-spec-extraction",
                    "tokens_consumed": spec.spec_extraction_tokens,
                    "model_used": "gemini-2.0-flash",
                    "seed": str(seed),
                    "inputs": {},
                    "outputs": {},
                })

            publish_progress(session_id, {
                "type": VIDEO_GENERATING,
                "ad_index": i + 1,
                "ad_id": ad_id,
                "videos_total": video_count,
                "videos_generated": videos_generated,
                "video_variants_generated": video_variants_generated,
                "cost_so_far": cost_so_far,
            })

            variants = generate_video_variants(
                spec=spec,
                ad_id=ad_id,
                seed=seed,
                output_dir=output_dir,
                ledger_path=ledger_path,
                veo_client=client,
            )
            video_variants_generated += len(variants)
            if variants:
                videos_generated += 1

            publish_progress(session_id, {
                "type": VIDEO_EVALUATING,
                "ad_index": i + 1,
                "ad_id": ad_id,
                "videos_total": video_count,
                "videos_generated": videos_generated,
                "video_variants_generated": video_variants_generated,
                "cost_so_far": cost_so_far,
            })

            eval_results = {}
            coherence_results = {}
            for v in variants:
                ev = evaluate_video_attributes(
                    v.video_path,
                    {
                        "duration": v.duration,
                        "audio_mode": v.audio_mode,
                        "aspect_ratio": v.aspect_ratio,
                        "prompt_used": v.prompt_used,
                    },
                    v.ad_id,
                    v.variant_type,
                )
                co = check_video_coherence(
                    ad_copy,
                    v.video_path,
                    v.ad_id,
                    v.variant_type,
                )
                eval_results[v.variant_type] = ev
                coherence_results[v.variant_type] = co

                log_event(ledger_path, {
                    "event_type": "VideoEvaluated",
                    "ad_id": ad_id,
                    "brief_id": ad_id.split("_c")[0] if "_c" in ad_id else ad_id,
                    "cycle_number": 0,
                    "action": f"video_{v.variant_type}_evaluated",
                    "tokens_consumed": ev.tokens_consumed + co.tokens_consumed,
                    "model_used": "gemini-2.0-flash",
                    "seed": str(v.seed),
                    "outputs": {
                        "variant_type": v.variant_type,
                        "attributes": ev.attributes,
                        "attribute_pass_pct": ev.attribute_pass_pct,
                        "coherence_scores": co.dimensions,
                        "coherence_avg": co.avg_score,
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
                        "attribute_pass_pct": ev.attribute_pass_pct,
                        "coherence_avg": co.avg_score,
                    },
                })
                videos_selected += 1

                # PD-12: Brief adherence scoring for video ads
                try:
                    from evaluate.brief_adherence import score_brief_adherence
                    adherence = score_brief_adherence(
                        ad_copy=ad_copy,
                        session_config=config,
                        ad_id=ad_id,
                        video_path=winner.video_path,
                    )
                    log_event(ledger_path, {
                        "event_type": "BriefAdherenceScored",
                        "ad_id": ad_id,
                        "brief_id": ad_id.split("_c")[0] if "_c" in ad_id else ad_id,
                        "cycle_number": 0,
                        "action": "brief_adherence",
                        "tokens_consumed": adherence.tokens_consumed,
                        "model_used": "gemini-2.0-flash",
                        "seed": "0",
                        "outputs": {
                            "scores": adherence.scores,
                            "avg_score": adherence.avg_score,
                            "rationales": adherence.rationales,
                        },
                    })
                except Exception as e:
                    logger.warning("Brief adherence scoring failed for %s: %s", ad_id, e)

                # PD-14: Video quality scoring
                try:
                    from evaluate.video_scorer import score_video
                    vid_scores = score_video(
                        video_path=winner.video_path,
                        ad_copy=ad_copy,
                        ad_id=ad_id,
                        session_config=config,
                    )
                    log_event(ledger_path, {
                        "event_type": "VideoScored",
                        "ad_id": ad_id,
                        "brief_id": ad_id.split("_c")[0] if "_c" in ad_id else ad_id,
                        "cycle_number": 0,
                        "action": "video_scored",
                        "tokens_consumed": vid_scores.tokens_consumed,
                        "model_used": "gemini-2.0-flash",
                        "seed": "0",
                        "outputs": {
                            "video_path": winner.video_path,
                            "video_scores": vid_scores.scores,
                            "video_avg_score": vid_scores.avg_score,
                            "rationales": vid_scores.rationales,
                        },
                    })
                except Exception as e:
                    logger.warning("Video scoring failed for %s: %s", ad_id, e)
            else:
                block_reason = (
                    "no_variants_generated"
                    if not variants
                    else "no_winner_from_evaluation"
                )
                log_event(ledger_path, {
                    "event_type": "VideoBlocked",
                    "ad_id": ad_id,
                    "brief_id": ad_id.split("_c")[0] if "_c" in ad_id else ad_id,
                    "cycle_number": 0,
                    "action": "video_blocked",
                    "tokens_consumed": 0,
                    "model_used": getattr(client, "model_used", "unknown"),
                    "seed": "0",
                    "outputs": {"reason": block_reason},
                })
                videos_blocked += 1

        except Exception as e:
            logger.error("Video pipeline error for ad %s: %s", ad_id, e)
            # region agent log
            _debug_log(
                "H3",
                "app/workers/tasks/pipeline_task.py:_run_video_pipeline:ad-except",
                "video ad exception",
                {
                    "session_id": session_id,
                    "ad_id": ad_id,
                    "error_type": type(e).__name__,
                    "error": str(e),
                },
            )
            # endregion
            videos_blocked += 1

        try:
            from evaluate.cost_reporter import sum_session_display_cost_usd
            from iterate.ledger import read_events

            cost_so_far = round(sum_session_display_cost_usd(read_events(ledger_path)), 4)
        except Exception:
            pass

        publish_progress(session_id, {
            "type": VIDEO_AD_COMPLETE,
            "ad_index": i + 1,
            "ad_id": ad_id,
            "videos_total": video_count,
            "videos_generated": videos_generated,
            "video_variants_generated": video_variants_generated,
            "videos_selected": videos_selected,
            "videos_blocked": videos_blocked,
            "cost_so_far": cost_so_far,
        })

    publish_progress(session_id, {
        "type": VIDEO_PIPELINE_COMPLETE,
        "videos_total": video_count,
        "videos_generated": videos_generated,
        "video_variants_generated": video_variants_generated,
        "videos_selected": videos_selected,
        "videos_blocked": videos_blocked,
        "cost_so_far": cost_so_far,
    })

    return {
        "videos_generated": videos_generated,
        "video_variants_generated": video_variants_generated,
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

        # region agent log
        _debug_log(
            "H5",
            "app/workers/tasks/pipeline_task.py:run_pipeline_session:dispatch",
            "pipeline dispatch",
            {
                "session_id": session_id,
                "session_type": session_type,
                "status_before": session_row.status,
                "ledger_path": ledger_path,
            },
        )
        # endregion

        if session_type == "video":
            result = _run_video_pipeline(session_id, config, ledger_path, db)
            summary = {
                "videos_generated": result.get("videos_generated", 0),
                "video_variants_generated": result.get("video_variants_generated", 0),
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

        # Display-aligned cost (video: excludes non-winning variant Fal charges when VideoSelected exists)
        try:
            from iterate.ledger import read_events
            from evaluate.cost_reporter import sum_session_display_cost_usd

            summary["cost_so_far"] = round(sum_session_display_cost_usd(read_events(ledger_path)), 4)
        except Exception:
            pass  # Keep the estimate if ledger read fails

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
        # region agent log
        _debug_log(
            "H3",
            "app/workers/tasks/pipeline_task.py:run_pipeline_session:except",
            "top-level pipeline exception",
            {
                "session_id": session_id,
                "error_type": type(e).__name__,
                "error": str(e),
            },
        )
        # endregion
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
