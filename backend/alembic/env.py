"""Alembic migration environment configuration.

TAG: [SPEC-001] [DATABASE] [ALEMBIC]
REQ: REQ-002 - Alembic Migration Setup
REQ: REQ-007 - Migration Safety Enhancement

This module configures Alembic to work with async SQLAlchemy
and loads database URL from application settings.
"""

import asyncio
import os
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Import your Base and all models here
# All models must be imported for Alembic autogenerate to detect them
from app.models import (  # noqa: F401
    Agent,
    Base,
    Edge,
    ExecutionLog,
    Node,
    NodeExecution,
    Schedule,
    Tool,
    User,
    Workflow,
    WorkflowExecution,
)

# This is the Alembic Config object
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Add your model's MetaData object here for 'autogenerate' support
target_metadata = Base.metadata


def get_url() -> str:
    """Get database URL from application settings.

    Returns the async database URL for migrations.
    """
    from app.core.config import settings

    if settings.DATABASE_URL is None:
        raise ValueError(
            "DATABASE_URL is not set. Please configure it in your .env file."
        )

    url = str(settings.DATABASE_URL)
    # Ensure async driver
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    return url


def check_production_safety() -> None:
    """Prevent accidental production migrations.

    Raises:
        RuntimeError: If running in production without explicit confirmation.

    Environment Variables:
        ENVIRONMENT: Current environment (e.g., "production", "development")
        CONFIRM_PRODUCTION_MIGRATION: Must be "true" to allow production migrations

    Example:
        To run migrations in production:
        export ENVIRONMENT=production
        export CONFIRM_PRODUCTION_MIGRATION=true
        alembic upgrade head
    """
    env = os.getenv("ENVIRONMENT", "").lower()

    if env == "production":
        confirm = os.getenv("CONFIRM_PRODUCTION_MIGRATION", "").lower()
        if confirm != "true":
            raise RuntimeError(
                "Production migration requires CONFIRM_PRODUCTION_MIGRATION=true. "
                "This prevents accidental migrations to production database. "
                "To proceed, set the environment variable and try again."
            )


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well. By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Run migrations with the given connection."""
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in 'online' mode with async engine.

    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = get_url()

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    This function checks production safety before executing migrations
    to prevent accidental changes to production databases.
    """
    check_production_safety()
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
