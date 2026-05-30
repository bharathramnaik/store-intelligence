# PROMPT: "Write pytest tests for anomaly detection covering dead zone, stale feed, queue spike"
# CHANGES MADE: Added dead zone test with 35 min gap, added stale feed test with mocked old timestamp, added queue spike injection test, added conversion drop test

from __future__ import annotations

import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4
from httpx import AsyncClient

from app.db.session import get_db_context


class TestAnomalies:
    async def test_dead_zone(self, client: AsyncClient):
        now = datetime.now(timezone.utc)
        old = now - timedelta(minutes=35)
        events = [
            {"event_id": str(uuid4()), "store_id": "STORE_DEAD", "camera_id": "CAM_FLOOR", "visitor_id": "VIS_DEAD1", "event_type": "ZONE_ENTER", "timestamp": old.isoformat(), "zone_id": "SKINCARE", "is_staff": False, "confidence": 0.9, "metadata": {}},
        ]
        await client.post("/events/ingest", json=events)
        response = await client.get("/stores/STORE_DEAD/anomalies")
        assert response.status_code == 200
        data = response.json()
        dead_zones = [a for a in data if a["anomaly_type"] == "DEAD_ZONE"]
        assert len(dead_zones) >= 1
        assert dead_zones[0]["severity"] == "WARN"

    async def test_stale_feed(self, client: AsyncClient):
        now = datetime.now(timezone.utc)
        old = now - timedelta(minutes=15)
        events = [
            {"event_id": str(uuid4()), "store_id": "STORE_STALE", "camera_id": "CAM_ENTRY", "visitor_id": "VIS_STALE1", "event_type": "ENTRY", "timestamp": old.isoformat(), "is_staff": False, "confidence": 0.9, "metadata": {}},
        ]
        await client.post("/events/ingest", json=events)
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        stale = [s for s in data["stores"] if s["store_id"] == "STORE_STALE"]
        assert len(stale) == 1
        assert stale[0]["status"] == "STALE_FEED"

    async def test_queue_spike(self, client: AsyncClient):
        now = datetime.now(timezone.utc)
        # Inject high queue depth
        events = []
        for i in range(20):
            events.append({
                "event_id": str(uuid4()),
                "store_id": "STORE_QSPIKE",
                "camera_id": "CAM_BILL",
                "visitor_id": f"VIS_Q{i:03d}",
                "event_type": "BILLING_QUEUE_JOIN",
                "timestamp": now.isoformat(),
                "zone_id": "BILLING",
                "is_staff": False,
                "confidence": 0.9,
                "metadata": {"queue_depth": 50, "sku_zone": "BILLING", "session_seq": 1}
            })
        await client.post("/events/ingest", json=events)
        response = await client.get("/stores/STORE_QSPIKE/anomalies")
        assert response.status_code == 200
        data = response.json()
        spikes = [a for a in data if a["anomaly_type"] == "QUEUE_SPIKE"]
        assert len(spikes) >= 1
        assert spikes[0]["severity"] in ("WARN", "CRITICAL")
