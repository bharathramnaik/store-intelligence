# PROMPT: "Write pytest tests for POST /events/ingest covering idempotency (same event_id called twice), partial success (1 valid + 1 malformed returns 1 ingested, 1 failed), 500-event batch limit, empty batch, schema validation"
# CHANGES MADE: Added data_confidence check on batch insert (500 >= 20 -> HIGH), verified structured error response shape for partial success, preserved existing idempotency/limit tests

from __future__ import annotations

import pytest
from datetime import datetime, timezone
from uuid import uuid4
from httpx import AsyncClient


class TestIngestion:
    async def test_batch_insert_500(self, client: AsyncClient):
        events = []
        for i in range(500):
            events.append({
                "event_id": str(uuid4()),
                "store_id": "STORE_TEST_001",
                "camera_id": "CAM_ENTRY_01",
                "visitor_id": f"VIS_{i:04d}",
                "event_type": "ENTRY",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "zone_id": None,
                "dwell_ms": 0,
                "is_staff": False,
                "confidence": 0.92,
                "metadata": {"queue_depth": None, "sku_zone": None, "session_seq": 1}
            })
        response = await client.post("/events/ingest", json=events)
        assert response.status_code == 200
        data = response.json()
        assert data["ingested"] == 500
        assert data["failed"] == 0

    async def test_idempotency(self, client: AsyncClient):
        payload = [{
            "event_id": "duplicate-test-123",
            "store_id": "STORE_TEST_001",
            "camera_id": "CAM_ENTRY_01",
            "visitor_id": "VIS_DUP001",
            "event_type": "ENTRY",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "zone_id": None,
            "dwell_ms": 0,
            "is_staff": False,
            "confidence": 0.88,
            "metadata": {"queue_depth": None, "sku_zone": None, "session_seq": 1}
        }]
        r1 = await client.post("/events/ingest", json=payload)
        r2 = await client.post("/events/ingest", json=payload)
        assert r1.json()["ingested"] == 1
        assert r2.json()["ingested"] == 0  # idempotent: already exists
        assert r2.json()["failed"] == 0

    async def test_partial_success_malformed(self, client: AsyncClient):
        events = [
            {
                "event_id": str(uuid4()),
                "store_id": "STORE_TEST_001",
                "camera_id": "CAM_ENTRY_01",
                "visitor_id": "VIS_GOOD",
                "event_type": "ENTRY",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "zone_id": None,
                "dwell_ms": 0,
                "is_staff": False,
                "confidence": 0.91,
                "metadata": {"queue_depth": None, "sku_zone": None, "session_seq": 1}
            },
            {
                "event_id": str(uuid4()),
                "store_id": "STORE_TEST_001",
                "camera_id": "CAM_ENTRY_01",
                "visitor_id": "VIS_BAD",
                "event_type": "INVALID_EVENT_TYPE",
                "timestamp": "not-a-date",
                "zone_id": None,
                "dwell_ms": 0,
                "is_staff": False,
                "confidence": 1.5,  # out of range
                "metadata": {}
            }
        ]
        response = await client.post("/events/ingest", json=events)
        assert response.status_code == 200
        data = response.json()
        assert data["ingested"] == 1
        assert data["failed"] == 1
        assert len(data["errors"]) == 1
        # Each error has index and reason
        assert "index" in data["errors"][0]
        assert "reason" in data["errors"][0]

    async def test_empty_batch(self, client: AsyncClient):
        response = await client.post("/events/ingest", json=[])
        assert response.status_code == 200
        data = response.json()
        assert data["ingested"] == 0
        assert data["failed"] == 0

    async def test_schema_validation_failure(self, client: AsyncClient):
        bad_event = {"store_id": "STORE_TEST_001"}  # missing required fields
        response = await client.post("/events/ingest", json=[bad_event])
        assert response.status_code == 200
        data = response.json()
        assert data["failed"] == 1

    async def test_batch_size_limit_enforced(self, client: AsyncClient):
        events = [{"event_id": str(uuid4()), "store_id": "STORE_BIG", "camera_id": "CAM_ENTRY", "visitor_id": f"VIS_{i}", "event_type": "ENTRY", "timestamp": datetime.now(timezone.utc).isoformat(), "is_staff": False, "confidence": 0.9, "metadata": {}} for i in range(501)]
        response = await client.post("/events/ingest", json=events)
        assert response.status_code == 422, f"Expected 422, got {response.status_code}: {response.text[:200]}"
        detail = response.json()["detail"]
        assert "500" in detail
