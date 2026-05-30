# PROMPT: "Write pytest tests for conversion funnel covering session deduplication, drop-off percentages, re-entry handling"
# CHANGES MADE: Added test for complete funnel flow, added re-entry not double counting, added drop-off percentage math validation, added empty funnel test

from __future__ import annotations

import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4
from httpx import AsyncClient

from app.db.session import get_db_context


class TestFunnel:
    async def test_complete_funnel(self, client: AsyncClient):
        now = datetime.now(timezone.utc)
        vid = "VIS_FUNNEL1"
        events = [
            {"event_id": str(uuid4()), "store_id": "STORE_FUN", "camera_id": "CAM_ENTRY", "visitor_id": vid, "event_type": "ENTRY", "timestamp": now.isoformat(), "is_staff": False, "confidence": 0.9, "metadata": {}},
            {"event_id": str(uuid4()), "store_id": "STORE_FUN", "camera_id": "CAM_FLOOR", "visitor_id": vid, "event_type": "ZONE_ENTER", "timestamp": (now + timedelta(minutes=1)).isoformat(), "zone_id": "SKINCARE", "is_staff": False, "confidence": 0.9, "metadata": {}},
            {"event_id": str(uuid4()), "store_id": "STORE_FUN", "camera_id": "CAM_BILL", "visitor_id": vid, "event_type": "BILLING_QUEUE_JOIN", "timestamp": (now + timedelta(minutes=3)).isoformat(), "zone_id": "BILLING", "is_staff": False, "confidence": 0.9, "metadata": {"queue_depth": 2}},
        ]
        await client.post("/events/ingest", json=events)
        # Mark session as converted via POS correlation mock (direct DB update for test)
        async with get_db_context() as db:
            from sqlalchemy import text
            await db.execute(text("UPDATE sessions SET converted = true WHERE visitor_id = :vid"), {"vid": vid})
        response = await client.get("/stores/STORE_FUN/funnel")
        assert response.status_code == 200
        data = response.json()
        assert data["total_sessions"] == 1
        stages = {s["stage"]: s for s in data["stages"]}
        assert stages["Entry"]["count"] == 1
        assert stages["Zone Visit"]["count"] == 1
        assert stages["Billing Queue"]["count"] == 1
        assert stages["Purchase"]["count"] == 1
        assert stages["Zone Visit"]["drop_off_pct"] == 0.0

    async def test_reentry_not_double_counted(self, client: AsyncClient):
        now = datetime.now(timezone.utc)
        vid = "VIS_FUNNEL2"
        events = [
            {"event_id": str(uuid4()), "store_id": "STORE_FUN2", "camera_id": "CAM_ENTRY", "visitor_id": vid, "event_type": "ENTRY", "timestamp": (now - timedelta(hours=2)).isoformat(), "is_staff": False, "confidence": 0.9, "metadata": {}},
            {"event_id": str(uuid4()), "store_id": "STORE_FUN2", "camera_id": "CAM_ENTRY", "visitor_id": vid, "event_type": "REENTRY", "timestamp": now.isoformat(), "is_staff": False, "confidence": 0.85, "metadata": {}},
        ]
        await client.post("/events/ingest", json=events)
        response = await client.get("/stores/STORE_FUN2/funnel")
        assert response.status_code == 200
        data = response.json()
        assert data["total_sessions"] == 1  # deduplicated

    async def test_empty_funnel(self, client: AsyncClient):
        response = await client.get("/stores/STORE_EMPTY_FUN/funnel")
        assert response.status_code == 200
        data = response.json()
        assert data["total_sessions"] == 0
        for s in data["stages"]:
            assert s["count"] == 0
