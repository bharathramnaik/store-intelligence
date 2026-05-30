from __future__ import annotations

from datetime import datetime, timezone, timedelta

from typing import Literal

from fastapi import APIRouter, Depends
from sqlalchemy import select, func, and_, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import FunnelOut, FunnelStage
from app.db.base import EventModel, SessionModel
from app.db.session import get_db

router = APIRouter(prefix="/stores", tags=["stores"])


def _today_bounds() -> tuple[datetime, datetime]:
    now = datetime.now(timezone.utc)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)
    return start, end


@router.get("/{store_id}/funnel", response_model=FunnelOut)
async def get_funnel(store_id: str, db: AsyncSession = Depends(get_db)) -> FunnelOut:
    start, end = _today_bounds()

    # Stage 1: Entry (ENTRY or REENTRY)
    s1 = select(func.count(func.distinct(EventModel.visitor_id))).where(
        and_(
            EventModel.store_id == store_id,
            EventModel.is_staff == False,
            EventModel.event_type.in_(["ENTRY", "REENTRY"]),
            EventModel.timestamp >= start,
            EventModel.timestamp < end,
        )
    )
    entry_count = (await db.execute(s1)).scalar() or 0

    # Stage 2: Zone Visit (ZONE_ENTER from entering visitors only)
    entering_ids = select(EventModel.visitor_id).where(
        and_(
            EventModel.store_id == store_id,
            EventModel.is_staff == False,
            EventModel.event_type.in_(["ENTRY", "REENTRY"]),
            EventModel.timestamp >= start,
            EventModel.timestamp < end,
        )
    )
    s2 = select(func.count(func.distinct(EventModel.visitor_id))).where(
        and_(
            EventModel.store_id == store_id,
            EventModel.is_staff == False,
            EventModel.event_type == "ZONE_ENTER",
            EventModel.timestamp >= start,
            EventModel.timestamp < end,
            EventModel.visitor_id.in_(entering_ids),
        )
    )
    zone_count = (await db.execute(s2)).scalar() or 0

    # Stage 3: Billing Queue
    s3 = select(func.count(func.distinct(EventModel.visitor_id))).where(
        and_(
            EventModel.store_id == store_id,
            EventModel.is_staff == False,
            EventModel.event_type == "BILLING_QUEUE_JOIN",
            EventModel.timestamp >= start,
            EventModel.timestamp < end,
        )
    )
    queue_count = (await db.execute(s3)).scalar() or 0

    # Stage 4: Purchase (converted sessions today)
    s4 = select(func.count(func.distinct(SessionModel.visitor_id))).where(
        and_(
            SessionModel.store_id == store_id,
            SessionModel.is_staff == False,
            SessionModel.converted == True,
            SessionModel.start_time >= start,
            SessionModel.start_time < end,
        )
    )
    purchase_count = (await db.execute(s4)).scalar() or 0

    stages = [
        FunnelStage(stage="Entry", count=entry_count, drop_off_pct=None),
        FunnelStage(
            stage="Zone Visit",
            count=zone_count,
            drop_off_pct=round((entry_count - zone_count) / entry_count * 100, 2) if entry_count else 0.0,
        ),
        FunnelStage(
            stage="Billing Queue",
            count=queue_count,
            drop_off_pct=round((zone_count - queue_count) / zone_count * 100, 2) if zone_count else 0.0,
        ),
        FunnelStage(
            stage="Purchase",
            count=purchase_count,
            drop_off_pct=round((queue_count - purchase_count) / queue_count * 100, 2) if queue_count else 0.0,
        ),
    ]

    data_confidence: Literal["LOW", "HIGH"] = "HIGH" if entry_count >= 20 else "LOW"
    return FunnelOut(store_id=store_id, stages=stages, total_sessions=entry_count, data_confidence=data_confidence)
