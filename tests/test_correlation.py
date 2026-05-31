# PROMPT: "Write pytest tests for POS correlation logic covering 5-min billing window, non-staff filtering, outside-window exclusion"
# CHANGES MADE: Added test for successful correlation within 5-min window, added test for outside-window exclusion (no false positive), added test for staff exclusion from correlation

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from uuid import uuid4
from httpx import AsyncClient
from sqlalchemy import select

from app.correlation import correlate_pos_transactions
from app.db.base import PosTransactionModel, SessionModel
from app.db.session import get_db_context


class TestCorrelation:
    async def test_correlation_within_window(self, client: AsyncClient):
        now = datetime.now(timezone.utc)
        vid = "VIS_CORR1"
        events = [
            {
                "event_id": str(uuid4()),
                "store_id": "STORE_CORR",
                "camera_id": "CAM_ENTRY",
                "visitor_id": vid,
                "event_type": "ENTRY",
                "timestamp": now.isoformat(),
                "is_staff": False,
                "confidence": 0.9,
                "metadata": {},
            },
            {
                "event_id": str(uuid4()),
                "store_id": "STORE_CORR",
                "camera_id": "CAM_BILL",
                "visitor_id": vid,
                "event_type": "BILLING_QUEUE_JOIN",
                "timestamp": (now + timedelta(minutes=2)).isoformat(),
                "zone_id": "BILLING",
                "is_staff": False,
                "confidence": 0.9,
                "metadata": {"queue_depth": 2},
            },
        ]
        await client.post("/events/ingest", json=events)

        async with get_db_context() as db:
            txn = PosTransactionModel(
                transaction_id="TXN_CORR1",
                store_id="STORE_CORR",
                timestamp=now + timedelta(minutes=4),
                basket_value_inr=500.0,
                correlated=False,
            )
            db.add(txn)
            await db.commit()

        async with get_db_context() as db:
            await correlate_pos_transactions(db)

        async with get_db_context() as db:
            result = await db.execute(select(SessionModel).where(SessionModel.visitor_id == vid))
            session = result.scalar_one()
            assert session.converted is True

    async def test_outside_window_no_correlation(self, client: AsyncClient):
        now = datetime.now(timezone.utc)
        vid = "VIS_CORR2"
        events = [
            {
                "event_id": str(uuid4()),
                "store_id": "STORE_CORR2",
                "camera_id": "CAM_ENTRY",
                "visitor_id": vid,
                "event_type": "ENTRY",
                "timestamp": now.isoformat(),
                "is_staff": False,
                "confidence": 0.9,
                "metadata": {},
            },
            {
                "event_id": str(uuid4()),
                "store_id": "STORE_CORR2",
                "camera_id": "CAM_BILL",
                "visitor_id": vid,
                "event_type": "BILLING_QUEUE_JOIN",
                "timestamp": now.isoformat(),
                "zone_id": "BILLING",
                "is_staff": False,
                "confidence": 0.9,
                "metadata": {"queue_depth": 1},
            },
        ]
        await client.post("/events/ingest", json=events)

        async with get_db_context() as db:
            txn = PosTransactionModel(
                transaction_id="TXN_CORR2",
                store_id="STORE_CORR2",
                timestamp=now + timedelta(minutes=10),
                basket_value_inr=300.0,
                correlated=False,
            )
            db.add(txn)
            await db.commit()

        async with get_db_context() as db:
            await correlate_pos_transactions(db)

        async with get_db_context() as db:
            result = await db.execute(select(SessionModel).where(SessionModel.visitor_id == vid))
            session = result.scalar_one()
            assert session.converted is False

    async def test_staff_not_correlated(self, client: AsyncClient):
        now = datetime.now(timezone.utc)
        vid = "VIS_CORR3"
        events = [
            {
                "event_id": str(uuid4()),
                "store_id": "STORE_CORR3",
                "camera_id": "CAM_ENTRY",
                "visitor_id": vid,
                "event_type": "ENTRY",
                "timestamp": now.isoformat(),
                "is_staff": True,
                "confidence": 0.95,
                "metadata": {},
            },
            {
                "event_id": str(uuid4()),
                "store_id": "STORE_CORR3",
                "camera_id": "CAM_BILL",
                "visitor_id": vid,
                "event_type": "BILLING_QUEUE_JOIN",
                "timestamp": (now + timedelta(minutes=1)).isoformat(),
                "zone_id": "BILLING",
                "is_staff": True,
                "confidence": 0.95,
                "metadata": {"queue_depth": 1},
            },
        ]
        await client.post("/events/ingest", json=events)

        async with get_db_context() as db:
            txn = PosTransactionModel(
                transaction_id="TXN_CORR3",
                store_id="STORE_CORR3",
                timestamp=now + timedelta(minutes=2),
                basket_value_inr=200.0,
                correlated=False,
            )
            db.add(txn)
            await db.commit()

        async with get_db_context() as db:
            await correlate_pos_transactions(db)

        async with get_db_context() as db:
            result = await db.execute(select(SessionModel).where(SessionModel.visitor_id == vid))
            session = result.scalar_one()
            assert session.converted is False
