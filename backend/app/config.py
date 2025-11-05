import os
from datetime import timedelta


class Config:
    """Base configuration class"""
    
    # Security
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-jwt-secret-change-in-production")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)
    JWT_BLACKLIST_ENABLED = True
    JWT_BLACKLIST_TOKEN_CHECKS = ['access']
    
    # Database (SQLite default)
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///scheduling_system.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # CORS - Include all common development ports
    BACKEND_CORS_ORIGINS = os.getenv(
        "BACKEND_CORS_ORIGINS", 
        "http://localhost:3000,http://localhost:3001,http://localhost:5173,http://localhost:5174,http://127.0.0.1:5173,http://127.0.0.1:5174"
    ).split(",")
    
    # Celery / Redis
    CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")
    
    # Google credentials and Sheets
    GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "service-account-creds.json")
    GOOGLE_INPUT_URL = os.getenv(
        "GOOGLE_INPUT_URL",
        "https://docs.google.com/spreadsheets/d/1S1TpLejxD-k93HoKRpjm81XubHyoCgaAPXfYqx5ESW0/edit?gid=219808289#gid=219808289",
    )
    GOOGLE_OUTPUT_URL = os.getenv(
        "GOOGLE_OUTPUT_URL",
        "https://docs.google.com/spreadsheets/d/1Imm6TJDWsoVXpf0ykMrPj4rGPfP1noagBdgoZc5Hhxg/edit?usp=sharing",
    )
    GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID", "YOUR_SHEET_ID_HERE")
    GOOGLE_INPUT_TAB = os.getenv("GOOGLE_INPUT_TAB", "Input")
    GOOGLE_OUTPUT_TAB = os.getenv("GOOGLE_OUTPUT_TAB", "Output")
    
    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    
    # Pagination
    DEFAULT_PAGE_SIZE = 20
    MAX_PAGE_SIZE = 100


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///dev_scheduling_system.db")


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///prod_scheduling_system.db")


class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False


# Configuration mapping
config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig
}






