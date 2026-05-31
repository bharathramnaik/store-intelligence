
from __future__ import annotations
from logging.config import fileConfig
from sqlalchemy import pool
from alembic import context
from app.db.base import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

def run_migrations_online() -> None:
    from app.core.config import settings
    connectable = settings.database_url
    from sqlalchemy.ext.asyncio import create_async_engine
    import asyncio

    engine = create_async_engine(connectable, poolclass=pool.NullPool)

    async def run():
        async with engine.begin() as conn:
            def do_run_migrations(connection):
                context.configure(connection=connection, target_metadata=target_metadata)
                context.run_migrations()
            await conn.run_sync(do_run_migrations)

    asyncio.run(run())

run_migrations_online()
