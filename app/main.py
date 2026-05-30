from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.core.logging import logger, LoggingMiddleware
from app.core.errors import global_exception_handler, db_exception_handler
from app.db.base import engine, Base
from app.db.session import get_db_context
from app.ingestion import router as ingestion_router
from app.metrics import router as metrics_router
from app.funnel import router as funnel_router
from app.heatmap import router as heatmap_router
from app.anomalies import router as anomalies_router
from app.health import router as health_router
from app.correlation import correlate_pos_transactions


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def periodic_correlation() -> None:
    while True:
        try:
            async with get_db_context() as db:
                await correlate_pos_transactions(db)
        except Exception as exc:
            logger.error("correlation_task_failed", error=str(exc))
        await asyncio.sleep(60)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    logger.info("startup_complete")
    task = asyncio.create_task(periodic_correlation())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    await engine.dispose()


app = FastAPI(
    title="Store Intelligence API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(LoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_exception_handler(Exception, global_exception_handler)
app.add_exception_handler(SQLAlchemyError, db_exception_handler)

app.include_router(ingestion_router)
app.include_router(metrics_router)
app.include_router(funnel_router)
app.include_router(heatmap_router)
app.include_router(anomalies_router)
app.include_router(health_router)


@app.get("/")
async def root() -> dict:
    return {"service": "store-intelligence", "version": "0.1.0"}
