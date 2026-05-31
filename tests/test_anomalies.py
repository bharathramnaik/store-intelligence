# PROMPT: "Write pytest tests for GET /stores/{id}/anomalies covering QUEUE_SPIKE (with varying historical depths so stddev>0), CONVERSION_DROP (with varying 7-day rates so stddev>0), DEAD_ZONE (no visits in 30+ min), verifying severity and suggested_action fields exist in response"
# CHANGES MADE: Added dead zone test with 35 min gap, added stale feed test with mocked old timestamp, added queue spike with historical data (varying depths) so stddev>0, added conversion drop with varying 7-day rates so stddev>0, added anomaly persistence DB check, added severity and suggested_action field validation, updated prompt block

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from uuid import uuid4
from httpx import AsyncClient

from app.db.session import get_db_context
from app.db.base import AnomalyModel
from sqlalchemy import select


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
        dz = dead_zones[0]
        assert dz["severity"] == "WARN"
        assert "SKINCARE" in dz["message"]
        assert "lighting" in dz["suggested_action"].lower() or "signage" in dz["suggested_action"].lower()

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
        events = []

        for day in range(7, 0, -1):
            old = now - timedelta(days=day)
            for _ in range(5):
                events.append({
                    "event_id": str(uuid4()),
                    "store_id": "STORE_QSPIKE",
                    "camera_id": "CAM_BILL",
                    "visitor_id": f"VIS_QHIST{day}_{_}",
                    "event_type": "BILLING_QUEUE_JOIN",
                    "timestamp": old.isoformat(),
                    "zone_id": "BILLING",
                    "is_staff": False,
                    "confidence": 0.9,
                    "metadata": {"queue_depth": day + 1, "sku_zone": "BILLING", "session_seq": 1}
                })

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
        s = spikes[0]
        assert s["severity"] in ("WARN", "CRITICAL")
        assert "counter" in s["suggested_action"].lower() or "cashier" in s["suggested_action"].lower()

    async def test_conversion_drop(self, client: AsyncClient):
        now = datetime.now(timezone.utc)
        async with get_db_context() as db:
            from app.db.base import DailyMetricModel
            varying_rates = [0.30, 0.28, 0.32, 0.25, 0.35, 0.29, 0.31]
            for i in range(7, 0, -1):
                d = now - timedelta(days=i)
                db.add(DailyMetricModel(
                    id=str(uuid4()),
                    store_id="STORE_CDROP",
                    metric_date=d.replace(hour=0, minute=0, second=0, microsecond=0),
                    unique_visitors=100,
                    conversion_rate=varying_rates[7 - i],
                    avg_dwell_ms=45000.0,
                    queue_depth=3,
                    abandonment_rate=0.05,
                ))
            await db.commit()

        for i in range(100):
            events = [{
                "event_id": str(uuid4()),
                "store_id": "STORE_CDROP",
                "camera_id": "CAM_ENTRY",
                "visitor_id": f"VIS_CD{i:04d}",
                "event_type": "ENTRY",
                "timestamp": now.isoformat(),
                "is_staff": False,
                "confidence": 0.9,
                "metadata": {},
            }]
            await client.post("/events/ingest", json=events)

        response = await client.get("/stores/STORE_CDROP/anomalies")
        assert response.status_code == 200
        data = response.json()
        cdrops = [a for a in data if a["anomaly_type"] == "CONVERSION_DROP"]
        assert len(cdrops) >= 1
        c = cdrops[0]
        assert c["severity"] in ("WARN", "CRITICAL")
        assert "conversion" in c["message"].lower()
        assert "queue" in c["suggested_action"].lower() or "product" in c["suggested_action"].lower() or "floor" in c["suggested_action"].lower()

    async def test_anomaly_persisted_in_db(self, client: AsyncClient):
        now = datetime.now(timezone.utc)
        old = now - timedelta(minutes=35)
        events = [
            {"event_id": str(uuid4()), "store_id": "STORE_PERSIST", "camera_id": "CAM_FLOOR", "visitor_id": "VIS_PERSIST1", "event_type": "ZONE_ENTER", "timestamp": old.isoformat(), "zone_id": "MAKEUP", "is_staff": False, "confidence": 0.9, "metadata": {}},
        ]
        await client.post("/events/ingest", json=events)
        await client.get("/stores/STORE_PERSIST/anomalies")

        async with get_db_context() as db:
            result = await db.execute(
                select(AnomalyModel).where(AnomalyModel.store_id == "STORE_PERSIST")
            )
            persisted = result.scalars().all()
            assert len(persisted) >= 1
            assert persisted[0].anomaly_type == "DEAD_ZONE"
            assert persisted[0].suggested_action is not None
