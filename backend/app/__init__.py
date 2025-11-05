# Multi-Tenant Scheduling System - Flask Backend
# Main Application Factory
from flask import Flask, jsonify
from app.config import Config
from dotenv import load_dotenv
import os
from app.extensions import db, jwt, cors, init_celery
from app.utils.logger import configure_logging
from app.routes.common_routes import common_bp
from app.routes.auth import auth_bp
from app.routes.sysadmin_routes import sysadmin_bp
from app.routes.clientadmin_routes import clientadmin_bp
from app.routes.schedulemanager_routes import schedulemanager_bp
from app.routes.employee_routes import employee_bp
from app.routes.tenant_routes import tenant_bp
from app.routes.user_routes import user_bp
from app.routes.department_routes import department_bp
from app.routes.schedule_definition_routes import schedule_definition_bp
from app.routes.schedule_permission_routes import schedule_permission_bp
from app.routes.schedule_job_log_routes import schedule_job_log_bp
from app.routes.google_sheets_routes import google_sheets_bp
from app.services.celery_tasks import bind_celery, register_periodic_tasks, register_schedule_execution_task


def register_blueprints(app: Flask) -> None:
    # Register more specific routes FIRST to avoid conflicts
    app.register_blueprint(employee_bp, url_prefix="/api/v1/employee")  # Register BEFORE general /api/v1 routes
    app.register_blueprint(auth_bp, url_prefix="/api/v1/auth")
    # Register role-specific blueprints BEFORE common_bp to avoid route conflicts
    # Use full path to include blueprint-specific prefix
    app.register_blueprint(sysadmin_bp, url_prefix="/api/v1/sysadmin")
    app.register_blueprint(clientadmin_bp, url_prefix="/api/v1/clientadmin")
    app.register_blueprint(schedulemanager_bp, url_prefix="/api/v1/schedulemanager")
    # Register common_bp last to avoid conflicts with specific routes
    app.register_blueprint(common_bp, url_prefix="/api/v1")
    # ERD-based routes
    app.register_blueprint(tenant_bp, url_prefix="/api/v1/tenants")
    app.register_blueprint(user_bp, url_prefix="/api/v1/users")
    app.register_blueprint(department_bp, url_prefix="/api/v1/departments")
    app.register_blueprint(schedule_definition_bp, url_prefix="/api/v1/schedule-definitions")
    app.register_blueprint(schedule_permission_bp, url_prefix="/api/v1/schedule-permissions")
    app.register_blueprint(schedule_job_log_bp, url_prefix="/api/v1/schedule-job-logs")
    app.register_blueprint(google_sheets_bp, url_prefix="/api/v1/sheets")
    
    # Register schedule routes
    from app.routes.schedule_routes import schedule_bp
    app.register_blueprint(schedule_bp, url_prefix="/api/v1/schedule")


def create_app(config_object: type[Config] | None = None):
    configure_logging()

    # Load environment variables from .env if present
    try:
        load_dotenv()
    except Exception:
        pass

    app = Flask(__name__)
    app.config.from_object(config_object or Config)

    # Fallbacks to ensure Celery uses Redis and Google URLs are present
    app.config.setdefault("CELERY_BROKER_URL", os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"))
    app.config.setdefault("CELERY_RESULT_BACKEND", os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0"))
    app.config.setdefault("GOOGLE_INPUT_URL", os.getenv("GOOGLE_INPUT_URL", "https://docs.google.com/spreadsheets/d/1S1TpLejxD-k93HoKRpjm81XubHyoCgaAPXfYqx5ESW0/edit?gid=219808289#gid=219808289"))
    app.config.setdefault("GOOGLE_OUTPUT_URL", os.getenv("GOOGLE_OUTPUT_URL", "https://docs.google.com/spreadsheets/d/1Imm6TJDWsoVXpf0ykMrPj4rGPfP1noagBdgoZc5Hhxg/edit?usp=sharing"))
    app.config.setdefault("GOOGLE_APPLICATION_CREDENTIALS", os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "service-account-creds.json"))

    # Initialize CORS with origins from config
    cors_origins = app.config.get("BACKEND_CORS_ORIGINS", [])
    if isinstance(cors_origins, str):
        cors_origins = [origin.strip() for origin in cors_origins.split(",") if origin.strip()]
    elif isinstance(cors_origins, list):
        cors_origins = [origin.strip() for origin in cors_origins if origin.strip()]
    
    # Default development origins - explicitly include http://localhost:5174
    default_dev_origins = [
        "http://localhost:5174",
        "http://localhost:5173",
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:5173",
    ]
    
    # Merge with configured origins, ensuring http://localhost:5174 is always included
    if not cors_origins:
        cors_origins = default_dev_origins
    else:
        # Add default origins if not already present
        for origin in default_dev_origins:
            if origin not in cors_origins:
                cors_origins.append(origin)
    
    import logging
    logger = logging.getLogger(__name__)
    
    # Configure CORS with explicit origins (cannot use "*" with supports_credentials)
    logger.info(f"CORS configured with origins: {cors_origins}")
    cors.init_app(
        app,
        origins=cors_origins,
        supports_credentials=True,
        methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        allow_headers=["Content-Type", "Authorization", "Accept", "X-Requested-With"],
        expose_headers=["Content-Type", "Authorization"],
        max_age=3600
    )
    
    # Note: Flask-CORS handles OPTIONS automatically, but we ensure it works correctly
    # The before_request handler is removed to avoid conflicts with Flask-CORS
    
    # Add global after_request handler to ensure CORS headers on all responses
    @app.after_request
    def after_request(response):
        # Ensure CORS headers are present on all responses
        from flask import request
        origin = request.headers.get('Origin')
        
        # Only set CORS headers if origin is in allowed list
        if origin and (origin in cors_origins or 'localhost:5174' in origin):
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
        
        if 'Access-Control-Allow-Methods' not in response.headers:
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
        
        if 'Access-Control-Allow-Headers' not in response.headers:
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, Accept, X-Requested-With"
        
        return response
    db.init_app(app)
    jwt.init_app(app)

    register_blueprints(app)
    
    # Add root endpoint
    @app.route("/")
    def index():
        """Root endpoint showing API information"""
        return jsonify({
            "message": "Smart Scheduling API is running",
            "version": "2.0.0",
            "health": "/api/v1/health",
            "routes": "/api/v1/routes",
            "auth": {
                "register_get_help": "/api/v1/auth/register",
                "register_post": "/api/v1/auth/register",
                "login_post": "/api/v1/auth/login"
            },
            "documentation": "See /api/v1/routes for all available endpoints"
        })

    # Create DB tables and initialize default data
    with app.app_context():
        try:
            db.create_all()
            # Initialize default users on first run
            from app.utils.db import seed_initial_data, seed_schedule_definitions
            seed_initial_data(app)
            # Initialize default schedule definitions on first run
            seed_schedule_definitions(app)
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Database initialization warning: {e}")

    # Init Celery and bind tasks
    celery_app = init_celery(app)
    if celery_app is not None:
        bind_celery(celery_app)
        register_periodic_tasks(celery_app)

    return app

# Legacy factory removed to prevent side-effects