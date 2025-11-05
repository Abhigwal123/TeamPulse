"""
Database connection and session management
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from ..core.config import settings

# Create database engine
# Handle SQLite vs MySQL connection args
connect_args = {}
if "sqlite" in settings.DATABASE_URL.lower():
    connect_args = {"check_same_thread": False}
elif "mysql" in settings.DATABASE_URL.lower():
    # MySQL connection - try to set up but don't fail if driver missing
    try:
        import MySQLdb
    except ImportError:
        # If MySQLdb is not available and we're using MySQL, fallback to SQLite for development
        import os
        fallback_url = os.getenv("FALLBACK_DATABASE_URL", "sqlite:///./scheduling_system.db")
        if fallback_url:
            settings.DATABASE_URL = fallback_url
            connect_args = {"check_same_thread": False}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    echo=settings.DEBUG
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for models
Base = declarative_base()


def get_db():
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
