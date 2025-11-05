"""
Celery Worker Entry Point
Run with: celery -A celery_worker.celery worker --loglevel=info
Or from backend/: celery -A backend.celery_worker.celery worker --loglevel=info
"""
import sys
import os

# Add backend directory to path for imports
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app import create_app
from app.extensions import init_celery

# Create Flask app and initialize Celery
flask_app = create_app()
celery = init_celery(flask_app)

if celery:
    # Autodiscover tasks from app.services.celery_tasks
    celery.autodiscover_tasks(['app.services.celery_tasks'], force=True)
    
    # Also import tasks from celery_tasks module if it exists
    try:
        import celery_tasks
        celery.autodiscover_tasks(['celery_tasks'], force=True)
    except ImportError:
        pass

# Export celery for celery command
__all__ = ['celery', 'flask_app']



