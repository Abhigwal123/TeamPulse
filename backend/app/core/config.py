"""
Application configuration settings
"""

import os
from typing import Optional, List
from pydantic_settings import BaseSettings
from pydantic import validator


class Settings(BaseSettings):
    """Application settings"""
    
    # Application
    APP_NAME: str = "Smart Scheduling SaaS"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = False
    API_V1_STR: str = "/api/v1"
    
    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    ALGORITHM: str = "HS256"
    
    # Database
    DATABASE_URL: str = "sqlite:///./scheduling.db"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # RabbitMQ
    RABBITMQ_URL: str = "amqp://guest:guest@localhost:5672//"
    
    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"
    
    # Google Cloud
    GOOGLE_CREDENTIALS_FILE: Optional[str] = None
    GOOGLE_CLOUD_PROJECT_ID: Optional[str] = None
    GOOGLE_CLOUD_STORAGE_BUCKET: Optional[str] = None
    
    # CORS
    BACKEND_CORS_ORIGINS: Optional[str] = None
    
    # File Upload
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_FILE_TYPES: Optional[str] = None
    
    # Task Processing
    TASK_TIMEOUT: int = 300  # 5 minutes
    MAX_CONCURRENT_TASKS: int = 5
    
    @property
    def cors_origins(self) -> List[str]:
        """Get CORS origins as a list"""
        if self.BACKEND_CORS_ORIGINS is None:
            return [
                "http://localhost:3000",
                "http://localhost:3001",
                "https://localhost:3000",
                "https://localhost:3001",
            ]
        if isinstance(self.BACKEND_CORS_ORIGINS, str):
            if not self.BACKEND_CORS_ORIGINS or self.BACKEND_CORS_ORIGINS.strip() == "":
                return [
                    "http://localhost:3000",
                    "http://localhost:3001",
                    "https://localhost:3000",
                    "https://localhost:3001",
                ]
            if not self.BACKEND_CORS_ORIGINS.startswith("["):
                return [i.strip() for i in self.BACKEND_CORS_ORIGINS.split(",") if i.strip()]
            # Try to parse as JSON if it starts with [
            try:
                import json
                parsed = json.loads(self.BACKEND_CORS_ORIGINS)
                if isinstance(parsed, list):
                    return parsed
            except:
                pass
        if isinstance(self.BACKEND_CORS_ORIGINS, list):
            return self.BACKEND_CORS_ORIGINS
        # Default fallback
        return [
            "http://localhost:3000",
            "http://localhost:3001",
            "https://localhost:3000",
            "https://localhost:3001",
        ]
    
    @property
    def allowed_file_types(self) -> List[str]:
        """Get allowed file types as a list"""
        if self.ALLOWED_FILE_TYPES is None:
            return [".xlsx", ".xls"]
        if isinstance(self.ALLOWED_FILE_TYPES, str):
            if not self.ALLOWED_FILE_TYPES or self.ALLOWED_FILE_TYPES.strip() == "":
                return [".xlsx", ".xls"]
            if not self.ALLOWED_FILE_TYPES.startswith("["):
                return [i.strip() for i in self.ALLOWED_FILE_TYPES.split(",") if i.strip()]
            # Try to parse as JSON
            try:
                import json
                parsed = json.loads(self.ALLOWED_FILE_TYPES)
                if isinstance(parsed, list):
                    return parsed
            except:
                pass
        if isinstance(self.ALLOWED_FILE_TYPES, list):
            return self.ALLOWED_FILE_TYPES
        return [".xlsx", ".xls"]
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Ignore extra fields from .env file


# Global settings instance
settings = Settings()
