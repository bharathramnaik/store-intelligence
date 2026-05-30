from __future__ import annotations

import time
import uuid
from typing import Any

import structlog
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger("store_intelligence")


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        trace_id = str(uuid.uuid4())
        request.state.trace_id = trace_id
        start = time.perf_counter()

        store_id = request.path_params.get("store_id", "")
        log = logger.bind(
            trace_id=trace_id,
            endpoint=str(request.url.path),
            method=request.method,
            store_id=store_id,
        )

        try:
            response = await call_next(request)
            latency_ms = round((time.perf_counter() - start) * 1000, 2)
            event_count = getattr(request.state, "event_count", 0)
            log.info(
                "request_completed",
                latency_ms=latency_ms,
                status_code=response.status_code,
                event_count=event_count,
            )
            response.headers["X-Trace-Id"] = trace_id
            return response
        except Exception as exc:
            latency_ms = round((time.perf_counter() - start) * 1000, 2)
            log.error("request_failed", latency_ms=latency_ms, error=str(exc))
            raise
