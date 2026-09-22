from celery import Celery
from celery.schedules import crontab

from app.core.config import get_settings

settings = get_settings()
celery_app = Celery("strategic_intelligence", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.timezone = settings.app_timezone
celery_app.conf.beat_schedule = {
    "collect-news": {
        "task": "app.workers.tasks.collect_news",
        "schedule": settings.collector_interval_minutes * 60.0,
    },
    "morning-digest": {
        "task": "app.workers.tasks.send_morning_digest",
        "schedule": crontab(hour=settings.digest_hour_local, minute=0),
    },
}
