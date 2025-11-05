"""
Celery worker bootstrap that binds Flask app context.

Run with:
  celery -A app.tasks.worker.celery worker -l info
"""

from app.tasks.celery_app import celery, init_celery
from flask_app import app

# Bind Flask context to Celery tasks
init_celery(app)

__all__ = ["celery"]










