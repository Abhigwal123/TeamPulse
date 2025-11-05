"""
Alembic environment configuration
"""

from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context
import os
import sys

# Add the app directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.database.connection import Base
# Import all models so Alembic can detect them
# Note: Import the Flask-SQLAlchemy models (they use db.Model)
from app import db
from app.models import (
    User, Tenant, Department, ScheduleDefinition, SchedulePermission,
    ScheduleJobLog, EmployeeMapping, CachedSheetData, CachedSchedule, SyncLog
)
# Import schedule model that uses Base (SQLAlchemy declarative base)
try:
    from app.models.schedule import Schedule
except ImportError:
    pass
# Note: ScheduleTask has incompatible FK (references users.id but User uses userID)
# We'll skip it for this migration since we're only adding CachedSchedule and SyncLog

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def get_url():
    """Get database URL from environment or config"""
    return os.getenv("DATABASE_URL", config.get_main_option("sqlalchemy.url"))


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = get_url()
    # SQLite-specific configuration
    dialect_opts = {}
    if "sqlite" in url.lower():
        dialect_opts = {"paramstyle": "named"}
    
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts=dialect_opts,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    configuration = config.get_section(config.config_ini_section)
    url = get_url()
    configuration["sqlalchemy.url"] = url
    
    # Use NullPool for SQLite to avoid connection issues
    pool_class = pool.NullPool if "sqlite" in url.lower() else pool.StaticPool
    
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool_class,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
