from celery import Celery

from app.config import settings

celery_app = Celery(
    "restaurant",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    result_expires=3600,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    beat_schedule={
        "daily-sales-report-midnight": {
            "task": "tasks.generate_daily_sales_report",
            "schedule": 86400.0,
        },
    },
)
