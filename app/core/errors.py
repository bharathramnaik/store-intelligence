from __future__ import annotations

import uuid

from fastapi import Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.core.logging import logger


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    trace_id = getattr(request.state, "trace_id", str(uuid.uuid4()))
    logger.error("unhandled_exception", trace_id=trace_id, error=str(exc), exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal Server Error", "trace_id": trace_id},
    )


async def db_exception_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    trace_id = getattr(request.state, "trace_id", str(uuid.uuid4()))
    logger.error("database_unavailable", trace_id=trace_id, error=str(exc))
    return JSONResponse(
        status_code=503,
        content={"error": "Service Unavailable", "detail": "Database connection failed", "trace_id": trace_id},
    )
