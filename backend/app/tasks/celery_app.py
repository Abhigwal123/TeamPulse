"""
Celery application configuration with optional disable mode.

If environment variable ENABLE_CELERY is not set to "true", this module
exposes a MockCelery that runs tasks synchronously via .delay().
"""

import os
from ..core.config import settings
from celery import Celery

CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", getattr(settings, "CELERY_BROKER_URL", "redis://localhost:6379/0"))
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", getattr(settings, "CELERY_RESULT_BACKEND", "redis://localhost:6379/1"))

class _MockTask:
    def __init__(self, fn):
        self._fn = fn

    def delay(self, *args, **kwargs):
        return self._fn(*args, **kwargs)

    __call__ = delay


class MockCelery:
    def task(self, *dargs, **dkwargs):
        def _decorator(fn):
            return _MockTask(fn)
        return _decorator


celery = Celery(
    "scheduling_saas",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
    include=["app.tasks.tasks", "app.tasks.google_sync"],
)

def init_celery(flask_app):
    celery.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="Asia/Kolkata",
        enable_utc=True,
        task_track_started=True,
        worker_prefetch_multiplier=1,
        worker_max_tasks_per_child=1000,
        result_expires=3600,
    )
    
    # Configure beat schedule for periodic tasks
    celery.conf.beat_schedule = {
        'periodic-google-sheet-sync': {
            'task': 'app.tasks.google_sync.sync_google_sheets_daily',
            'schedule': 600.0,  # every 10 minutes (task will skip if data is fresh)
        },
    }

    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with flask_app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    return celery

