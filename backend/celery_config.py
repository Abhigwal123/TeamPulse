"""
Celery configuration for asynchronous task processing
"""
import os
from celery import Celery

# Celery configuration
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')

# Create Celery instance
celery = Celery(
    'scheduling_tasks',
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
    include=['celery_tasks', 'app.services.celery_tasks']
)

# Celery configuration
celery.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 minutes max per task
    task_soft_time_limit=240,  # 4 minutes soft limit
    worker_prefetch_multiplier=1,
    result_expires=3600,  # Results expire after 1 hour
)

# Task routing
celery.conf.task_routes = {
    'celery_tasks.execute_scheduling_task': {'queue': 'scheduling'},
}




