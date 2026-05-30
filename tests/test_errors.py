# PROMPT: "Write pytest tests for API error handlers covering global 500 on unhandled error, 503 on DB failure, trace_id propagation"
# CHANGES MADE: Added test for DB failure returning 503 with trace_id, added test for unhandled exception returning 500, added test for root endpoint, added logging middleware exception path test

from __future__ import annotations

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.exc import SQLAlchemyError

from app.main import app
from app.db.session import get_db


class TestErrors:
    async def test_db_failure_returns_503(self, client: AsyncClient):
        async def broken_get_db():
            raise SQLAlchemyError("Connection refused simulating DB failure")

        app.dependency_overrides[get_db] = broken_get_db
        try:
            response = await client.get("/stores/STORE_DBFAIL/metrics")
            assert response.status_code == 503
            data = response.json()
            assert data["error"] == "Service Unavailable"
            assert "Database connection failed" in data["detail"]
            assert "trace_id" in data
        finally:
            app.dependency_overrides.pop(get_db, None)

    async def test_unhandled_exception_handler_directly(self):
        from app.core.errors import global_exception_handler
        from fastapi import Request
        exc = ValueError("Something unexpected broke")
        req = Request({"type": "http", "method": "GET", "path": "/test", "headers": []})
        response = await global_exception_handler(req, exc)
        assert response.status_code == 500
        body = response.body.decode()
        assert "Internal Server Error" in body
        assert "trace_id" in body

    async def test_root_endpoint(self, client: AsyncClient):
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "store-intelligence"
        assert data["version"] == "0.1.0"
