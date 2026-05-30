from __future__ import annotations

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.db.base import (
    engine,
    Base,
    EventModel,
    SessionModel,
    PosTransactionModel,
    AnomalyModel,
    DailyMetricModel,
)
from app.db.session import AsyncSessionLocal


@pytest_asyncio.fixture(scope="session", loop_scope="session", autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(loop_scope="session")
async def clean_db():
    async with AsyncSessionLocal() as session:
        for model in (AnomalyModel, DailyMetricModel, PosTransactionModel, EventModel, SessionModel):
            await session.execute(delete(model))
        await session.commit()


@pytest_asyncio.fixture(loop_scope="session")
async def db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture(loop_scope="session")
async def client(clean_db) -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
