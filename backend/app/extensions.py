from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_cors import CORS


# Core extensions singletons
db = SQLAlchemy()
jwt = JWTManager()
cors = CORS()


celery = None  # type: ignore[assignment]


def init_celery(app):
    global celery
    if celery is not None:
        return celery

    # Import Celery lazily to avoid hard dependency for API-only runs
    try:
        from celery import Celery  # type: ignore
    except Exception as e:
        # Celery not available in this process (e.g., while upgrading); skip init
        return None

    broker_url = app.config.get("CELERY_BROKER_URL")
    result_backend = app.config.get("CELERY_RESULT_BACKEND")

    celery = Celery(app.import_name, broker=broker_url, backend=result_backend)

    # Pass Flask config and context to Celery tasks
    celery.conf.update(app.config)

    TaskBase = celery.Task

    class ContextTask(TaskBase):
        abstract = True

        def __call__(self, *args, **kwargs):
            with app.app_context():
                return TaskBase.__call__(self, *args, **kwargs)

    celery.Task = ContextTask
    return celery


