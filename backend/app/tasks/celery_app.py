"""
Celery Application — Background task queue configuration.
"""
from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "cybersentinel",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.tasks.threat_tasks",
        "app.tasks.report_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    beat_schedule={
        "sync-threat-feeds-every-6-hours": {
            "task": "tasks.sync_threat_feeds",
            "schedule": 21600.0,  # 6 hours in seconds
        },
    },
)
