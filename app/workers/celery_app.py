# Ad-Ops-Autopilot — Celery application
from celery import Celery

from app.config import settings

celery_app = Celery(
    "nerdy",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.workers.tasks.ping", "app.workers.tasks.pipeline_task"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
)
