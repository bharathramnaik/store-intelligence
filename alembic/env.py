
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
    from sqlalchemy import text
    import asyncio

    engine = create_async_engine(connectable, poolclass=pool.NullPool)

    async def run():
        async with engine.begin() as conn:
            await conn.run_sync(context.configure, connection=conn, target_metadata=target_metadata)
            await conn.run_sync(context.run_migrations)

    asyncio.run(run())

run_migrations_online()
