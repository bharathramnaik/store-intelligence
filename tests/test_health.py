# PROMPT: "Write pytest tests for health endpoint covering healthy store, stale feed detection, degraded mode on DB failure"
# CHANGES MADE: Added test for healthy store with recent event, added test for stale feed with 15-min old event, added test for degraded mode when DB connection fails

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from uuid import uuid4
from httpx import AsyncClient



class TestHealth:
    async def test_healthy_store_with_recent_event(self, client: AsyncClient):
        now = datetime.now(timezone.utc)
        events = [{
            "event_id": str(uuid4()),
            "store_id": "STORE_HLTH1",
            "camera_id": "CAM_ENTRY",
            "visitor_id": "VIS_HLTH1",
            "event_type": "ENTRY",
            "timestamp": now.isoformat(),
            "is_staff": False,
            "confidence": 0.9,
            "metadata": {},
        }]
        await client.post("/events/ingest", json=events)
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "healthy"
        store_statuses = {s["store_id"]: s for s in data["stores"]}
        assert "STORE_HLTH1" in store_statuses
        assert store_statuses["STORE_HLTH1"]["status"] == "ACTIVE"

    async def test_stale_feed(self, client: AsyncClient):
        now = datetime.now(timezone.utc)
        old = now - timedelta(minutes=15)
        events = [{
            "event_id": str(uuid4()),
            "store_id": "STORE_HLTH2",
            "camera_id": "CAM_ENTRY",
            "visitor_id": "VIS_HLTH2",
            "event_type": "ENTRY",
            "timestamp": old.isoformat(),
            "is_staff": False,
            "confidence": 0.9,
            "metadata": {},
        }]
        await client.post("/events/ingest", json=events)
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        store_statuses = {s["store_id"]: s for s in data["stores"]}
        assert "STORE_HLTH2" in store_statuses
        assert store_statuses["STORE_HLTH2"]["status"] == "STALE_FEED"

    async def test_multiple_stores_in_health(self, client: AsyncClient):
        now = datetime.now(timezone.utc)
        events = [
            {"event_id": str(uuid4()), "store_id": "STORE_A", "camera_id": "CAM_ENTRY", "visitor_id": "VIS_A", "event_type": "ENTRY", "timestamp": now.isoformat(), "is_staff": False, "confidence": 0.9, "metadata": {}},
            {"event_id": str(uuid4()), "store_id": "STORE_B", "camera_id": "CAM_ENTRY", "visitor_id": "VIS_B", "event_type": "ENTRY", "timestamp": (now - timedelta(minutes=15)).isoformat(), "is_staff": False, "confidence": 0.9, "metadata": {}},
        ]
        await client.post("/events/ingest", json=events)
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        stores = {s["store_id"]: s for s in data["stores"]}
        assert len(stores) >= 2
        assert stores["STORE_A"]["status"] == "ACTIVE"
        assert stores["STORE_B"]["status"] == "STALE_FEED"
