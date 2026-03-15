# Ad-Ops-Autopilot — Pipeline Celery task (PA-04)
import time

from sqlalchemy.orm import Session as DBSession

from app.db import SessionLocal, init_db
from app.models.session import Session as SessionModel
from app.workers.celery_app import celery_app
from app.workers.progress import (
    AD_EVALUATED,
    AD_GENERATED,
    AD_PUBLISHED,
    BATCH_COMPLETE,
    BATCH_START,
    CYCLE_COMPLETE,
    CYCLE_START,
    PIPELINE_COMPLETE,
    PIPELINE_ERROR,
    publish_progress,
)


@celery_app.task(bind=True)
def run_pipeline_session(self, session_id: str) -> dict:
    """Simulate pipeline with progress publishing at stage boundaries."""
    init_db()
    db: DBSession = SessionLocal()
    try:
        session_row = db.query(SessionModel).filter(SessionModel.session_id == session_id).first()
        if not session_row:
            raise ValueError(f"Session {session_id} not found")
        session_row.status = "running"
        db.commit()

        ads_generated = 0
        ads_evaluated = 0
        ads_published = 0
        cost_so_far = 0.0
        scores: list[float] = []

        for cycle in range(1, 3):
            publish_progress(
                session_id,
                {
                    "type": CYCLE_START,
                    "cycle": cycle,
                    "batch": 0,
                    "ads_generated": ads_generated,
                    "ads_evaluated": ads_evaluated,
                    "ads_published": ads_published,
                    "current_score_avg": sum(scores) / len(scores) if scores else 0.0,
                    "cost_so_far": cost_so_far,
                },
            )
            time.sleep(0.2)

            for batch in range(1, 3):
                publish_progress(
                    session_id,
                    {
                        "type": BATCH_START,
                        "cycle": cycle,
                        "batch": batch,
                        "ads_generated": ads_generated,
                        "ads_evaluated": ads_evaluated,
                        "ads_published": ads_published,
                        "current_score_avg": sum(scores) / len(scores) if scores else 0.0,
                        "cost_so_far": cost_so_far,
                    },
                )
                time.sleep(0.1)

                for _ in range(2):
                    ads_generated += 1
                    cost_so_far += 0.01
                    publish_progress(
                        session_id,
                        {
                            "type": AD_GENERATED,
                            "cycle": cycle,
                            "batch": batch,
                            "ads_generated": ads_generated,
                            "ads_evaluated": ads_evaluated,
                            "ads_published": ads_published,
                            "current_score_avg": sum(scores) / len(scores) if scores else 0.0,
                            "cost_so_far": cost_so_far,
                        },
                    )
                    time.sleep(0.05)

                for _ in range(2):
                    ads_evaluated += 1
                    score = 7.2 + (cycle * 0.3)
                    scores.append(score)
                    publish_progress(
                        session_id,
                        {
                            "type": AD_EVALUATED,
                            "cycle": cycle,
                            "batch": batch,
                            "ads_generated": ads_generated,
                            "ads_evaluated": ads_evaluated,
                            "ads_published": ads_published,
                            "current_score_avg": sum(scores) / len(scores),
                            "cost_so_far": cost_so_far,
                        },
                    )
                    time.sleep(0.05)

                for _ in range(1):
                    ads_published += 1
                    publish_progress(
                        session_id,
                        {
                            "type": AD_PUBLISHED,
                            "cycle": cycle,
                            "batch": batch,
                            "ads_generated": ads_generated,
                            "ads_evaluated": ads_evaluated,
                            "ads_published": ads_published,
                            "current_score_avg": sum(scores) / len(scores),
                            "cost_so_far": cost_so_far,
                        },
                    )
                    time.sleep(0.05)

                publish_progress(
                    session_id,
                    {
                        "type": BATCH_COMPLETE,
                        "cycle": cycle,
                        "batch": batch,
                        "ads_generated": ads_generated,
                        "ads_evaluated": ads_evaluated,
                        "ads_published": ads_published,
                        "current_score_avg": sum(scores) / len(scores),
                        "cost_so_far": cost_so_far,
                    },
                )
                time.sleep(0.1)

            publish_progress(
                session_id,
                {
                    "type": CYCLE_COMPLETE,
                    "cycle": cycle,
                    "batch": 0,
                    "ads_generated": ads_generated,
                    "ads_evaluated": ads_evaluated,
                    "ads_published": ads_published,
                    "current_score_avg": sum(scores) / len(scores) if scores else 0.0,
                    "cost_so_far": cost_so_far,
                },
            )
            time.sleep(0.2)

        publish_progress(
            session_id,
            {
                "type": PIPELINE_COMPLETE,
                "cycle": 2,
                "batch": 2,
                "ads_generated": ads_generated,
                "ads_evaluated": ads_evaluated,
                "ads_published": ads_published,
                "current_score_avg": sum(scores) / len(scores) if scores else 0.0,
                "cost_so_far": cost_so_far,
            },
        )

        session_row = db.query(SessionModel).filter(SessionModel.session_id == session_id).first()
        if session_row:
            session_row.status = "completed"
            session_row.results_summary = {
                "ads_generated": ads_generated,
                "ads_published": ads_published,
                "avg_score": sum(scores) / len(scores) if scores else 0.0,
                "cost_so_far": cost_so_far,
            }
            db.commit()

        return {"status": "completed", "ads_published": ads_published}

    except Exception as e:
        publish_progress(
            session_id,
            {
                "type": PIPELINE_ERROR,
                "cycle": 0,
                "batch": 0,
                "ads_generated": 0,
                "ads_evaluated": 0,
                "ads_published": 0,
                "current_score_avg": 0.0,
                "cost_so_far": 0.0,
                "error": str(e),
            },
        )
        session_row = db.query(SessionModel).filter(SessionModel.session_id == session_id).first()
        if session_row:
            session_row.status = "failed"
            db.commit()
        raise
    finally:
        db.close()
