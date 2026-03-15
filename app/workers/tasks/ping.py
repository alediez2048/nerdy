# Ad-Ops-Autopilot — Ping task for Celery health check
from app.workers.celery_app import celery_app


@celery_app.task
def ping() -> str:
    """Simple task to verify Celery worker is running."""
    return "pong"
