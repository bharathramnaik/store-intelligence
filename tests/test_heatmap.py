# PROMPT: "Write pytest tests for zone heatmap endpoint covering empty store, populated store, staff exclusion, confidence flag"
# CHANGES MADE: Added empty store returns empty zones, added populated store with zone frequency and dwell, added staff events excluded from heatmap, added LOW confidence when <20 sessions

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from uuid import uuid4
from httpx import AsyncClient


class TestHeatmap:
    async def test_empty_store_returns_empty_zones(self, client: AsyncClient):
        response = await client.get("/stores/STORE_HEAT_EMPTY/heatmap")
        assert response.status_code == 200
        data = response.json()
        assert data["zones"] == []
        assert data["data_confidence"] == "LOW"

    async def test_populated_store_zones(self, client: AsyncClient):
        now = datetime.now(timezone.utc)
        vid = "VIS_HEAT1"
        events = [
            {"event_id": str(uuid4()), "store_id": "STORE_HEAT1", "camera_id": "CAM_FLOOR", "visitor_id": vid, "event_type": "ENTRY", "timestamp": now.isoformat(), "is_staff": False, "confidence": 0.9, "metadata": {}},
            {"event_id": str(uuid4()), "store_id": "STORE_HEAT1", "camera_id": "CAM_FLOOR", "visitor_id": vid, "event_type": "ZONE_ENTER", "timestamp": (now + timedelta(seconds=10)).isoformat(), "zone_id": "SKINCARE", "is_staff": False, "confidence": 0.9, "metadata": {}},
            {"event_id": str(uuid4()), "store_id": "STORE_HEAT1", "camera_id": "CAM_FLOOR", "visitor_id": vid, "event_type": "ZONE_DWELL", "timestamp": (now + timedelta(seconds=60)).isoformat(), "zone_id": "SKINCARE", "dwell_ms": 30000, "is_staff": False, "confidence": 0.9, "metadata": {}},
        ]
        await client.post("/events/ingest", json=events)
        response = await client.get("/stores/STORE_HEAT1/heatmap")
        assert response.status_code == 200
        data = response.json()
        assert len(data["zones"]) == 1
        zone = data["zones"][0]
        assert zone["zone_id"] == "SKINCARE"
        assert zone["visit_frequency"] >= 1
        assert zone["avg_dwell_ms"] > 0
        assert zone["normalized_score"] == 100.0

    async def test_staff_excluded_from_heatmap(self, client: AsyncClient):
        now = datetime.now(timezone.utc)
        events = [
            {"event_id": str(uuid4()), "store_id": "STORE_HEAT2", "camera_id": "CAM_FLOOR", "visitor_id": "VIS_STAFF_HEAT", "event_type": "ENTRY", "timestamp": now.isoformat(), "is_staff": True, "confidence": 0.95, "metadata": {}},
            {"event_id": str(uuid4()), "store_id": "STORE_HEAT2", "camera_id": "CAM_FLOOR", "visitor_id": "VIS_STAFF_HEAT", "event_type": "ZONE_ENTER", "timestamp": (now + timedelta(seconds=5)).isoformat(), "zone_id": "SKINCARE", "is_staff": True, "confidence": 0.95, "metadata": {}},
        ]
        await client.post("/events/ingest", json=events)
        response = await client.get("/stores/STORE_HEAT2/heatmap")
        assert response.status_code == 200
        data = response.json()
        assert data["zones"] == []

    async def test_high_confidence_with_20_plus_sessions(self, client: AsyncClient):
        now = datetime.now(timezone.utc)
        events = []
        for i in range(25):
            events.append({
                "event_id": str(uuid4()),
                "store_id": "STORE_HEAT3",
                "camera_id": "CAM_FLOOR",
                "visitor_id": f"VIS_HEAT3_{i:04d}",
                "event_type": "ENTRY",
                "timestamp": now.isoformat(),
                "is_staff": False,
                "confidence": 0.9,
                "metadata": {},
            })
        await client.post("/events/ingest", json=events)
        response = await client.get("/stores/STORE_HEAT3/heatmap")
        assert response.status_code == 200
        data = response.json()
        assert data["data_confidence"] == "HIGH"

    async def test_dwell_without_zone_enter_no_crash(self, client: AsyncClient):
        now = datetime.now(timezone.utc)
        events = [
            {"event_id": str(uuid4()), "store_id": "STORE_HEAT4", "camera_id": "CAM_FLOOR", "visitor_id": "VIS_DWELL1", "event_type": "ZONE_DWELL", "timestamp": now.isoformat(), "zone_id": "MAKEUP", "dwell_ms": 30000, "is_staff": False, "confidence": 0.9, "metadata": {}},
        ]
        await client.post("/events/ingest", json=events)
        response = await client.get("/stores/STORE_HEAT4/heatmap")
        assert response.status_code == 200
        data = response.json()
        assert data["zones"] == []
