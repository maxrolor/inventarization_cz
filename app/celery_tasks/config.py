import os
from dotenv import load_dotenv
from .beat_schedule import beat_schedule

load_dotenv()


class CeleryConfig:
    broker_url = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    result_backend = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")
    broker_connection_retry_on_startup = True

    task_serializer = "json"
    result_serializer = "json"
    accept_content = ["json"]
    timezone = "Europe/Moscow"
    enable_utc = True

    task_track_started = True
    task_time_limit = 30 * 60
    task_soft_time_limit = 25 * 60
    worker_prefetch_multiplier = 1
    task_acks_late = True

    # Beat
    beat_schedule = beat_schedule
    beat_scheduler = "celery.beat:PersistentScheduler"  # или "redbeat.RedBeatScheduler"