# Ad-Ops-Autopilot — Celery application
from dotenv import load_dotenv  # noqa: E402
from celery import Celery

from app.config import settings

load_dotenv()  # Inject .env vars (FAL_KEY, GEMINI_API_KEY, etc.) into os.environ

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
