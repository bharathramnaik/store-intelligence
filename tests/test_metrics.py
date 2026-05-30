# PROMPT: "Write pytest tests for store metrics covering empty store, all-staff clip, zero purchases, re-entry session"
# CHANGES MADE: Added explicit empty store test with all zeros, added all-staff exclusion test, added zero purchase conversion rate test, added re-entry deduplication test

from __future__ import annotations

import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4
from httpx import AsyncClient


class TestMetrics:
    async def test_empty_store_returns_zeros(self, client: AsyncClient, db):
        response = await client.get("/stores/STORE_EMPTY/metrics")
        assert response.status_code == 200
        data = response.json()
        assert data["unique_visitors"] == 0
        assert data["conversion_rate"] == 0.0
        assert data["queue_depth"] == 0
        assert data["abandonment_rate"] == 0.0
        assert data["avg_dwell_per_zone"] == {}

    async def test_all_staff_clip_excluded(self, client: AsyncClient, db):
        now = datetime.now(timezone.utc)
        events = []
        for i in range(3):
            events.append({
                "event_id": str(uuid4()),
                "store_id": "STORE_STAFF",
                "camera_id": "CAM_ENTRY_01",
                "visitor_id": f"VIS_STF{i}",
                "event_type": "ENTRY",
                "timestamp": now.isoformat(),
                "is_staff": True,
                "confidence": 0.95,
                "metadata": {}
            })
        await client.post("/events/ingest", json=events)
        response = await client.get("/stores/STORE_STAFF/metrics")
        assert response.status_code == 200
        data = response.json()
        assert data["unique_visitors"] == 0
        assert data["conversion_rate"] == 0.0

    async def test_zero_purchases_conversion_zero(self, client: AsyncClient, db):
        now = datetime.now(timezone.utc)
        events = [{
            "event_id": str(uuid4()),
            "store_id": "STORE_NO_BUY",
            "camera_id": "CAM_ENTRY_01",
            "visitor_id": "VIS_NOBUY1",
            "event_type": "ENTRY",
            "timestamp": now.isoformat(),
            "is_staff": False,
            "confidence": 0.9,
            "metadata": {}
        }]
        await client.post("/events/ingest", json=events)
        response = await client.get("/stores/STORE_NO_BUY/metrics")
        assert response.status_code == 200
        data = response.json()
        assert data["unique_visitors"] == 1
        assert data["conversion_rate"] == 0.0

    async def test_reentry_deduplicated(self, client: AsyncClient, db):
        now = datetime.now(timezone.utc)
        events = [
            {
                "event_id": str(uuid4()),
                "store_id": "STORE_REENTRY",
                "camera_id": "CAM_ENTRY_01",
                "visitor_id": "VIS_REENTRY1",
                "event_type": "ENTRY",
                "timestamp": (now - timedelta(hours=2)).isoformat(),
                "is_staff": False,
                "confidence": 0.9,
                "metadata": {}
            },
            {
                "event_id": str(uuid4()),
                "store_id": "STORE_REENTRY",
                "camera_id": "CAM_ENTRY_01",
                "visitor_id": "VIS_REENTRY1",
                "event_type": "EXIT",
                "timestamp": (now - timedelta(hours=1)).isoformat(),
                "is_staff": False,
                "confidence": 0.9,
                "metadata": {}
            },
            {
                "event_id": str(uuid4()),
                "store_id": "STORE_REENTRY",
                "camera_id": "CAM_ENTRY_01",
                "visitor_id": "VIS_REENTRY1",
                "event_type": "REENTRY",
                "timestamp": now.isoformat(),
                "is_staff": False,
                "confidence": 0.85,
                "metadata": {}
            }
        ]
        await client.post("/events/ingest", json=events)
        response = await client.get("/stores/STORE_REENTRY/metrics")
        assert response.status_code == 200
        data = response.json()
        assert data["unique_visitors"] == 1  # deduplicated
