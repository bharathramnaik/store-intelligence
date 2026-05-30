from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import MetricOut
from app.db.base import EventModel, SessionModel
from app.db.session import get_db
from app.core.logging import logger

router = APIRouter(prefix="/stores", tags=["stores"])


def _today_bounds() -> tuple[datetime, datetime]:
    now = datetime.now(timezone.utc)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)
    return start, end


@router.get("/{store_id}/metrics", response_model=MetricOut)
async def get_metrics(store_id: str, db: AsyncSession = Depends(get_db)) -> MetricOut:
    start, end = _today_bounds()

    # Unique visitors (non-staff, ENTRY or REENTRY today)
    uv_stmt = select(func.count(func.distinct(EventModel.visitor_id))).where(
        and_(
            EventModel.store_id == store_id,
            EventModel.is_staff == False,
            EventModel.event_type.in_(["ENTRY", "REENTRY"]),
            EventModel.timestamp >= start,
            EventModel.timestamp < end,
        )
    )
    uv_result = await db.execute(uv_stmt)
    unique_visitors = uv_result.scalar() or 0

    # Conversion rate (sessions converted today)
    conv_stmt = select(func.count(func.distinct(SessionModel.visitor_id))).where(
        and_(
            SessionModel.store_id == store_id,
            SessionModel.is_staff == False,
            SessionModel.converted == True,
            SessionModel.start_time >= start,
            SessionModel.start_time < end,
        )
    )
    conv_result = await db.execute(conv_stmt)
    converters = conv_result.scalar() or 0
    conversion_rate = round(converters / unique_visitors, 4) if unique_visitors > 0 else 0.0

    # Avg dwell per zone (entering visitors only)
    entering_ids = select(EventModel.visitor_id).where(
        and_(
            EventModel.store_id == store_id,
            EventModel.is_staff == False,
            EventModel.event_type.in_(["ENTRY", "REENTRY"]),
            EventModel.timestamp >= start,
            EventModel.timestamp < end,
        )
    )
    dwell_stmt = select(
        EventModel.zone_id, func.avg(EventModel.dwell_ms)
    ).where(
        and_(
            EventModel.store_id == store_id,
            EventModel.is_staff == False,
            EventModel.event_type.in_(["ZONE_DWELL", "ZONE_EXIT"]),
            EventModel.dwell_ms > 0,
            EventModel.timestamp >= start,
            EventModel.timestamp < end,
            EventModel.visitor_id.in_(entering_ids),
        )
    ).group_by(EventModel.zone_id)
    dwell_result = await db.execute(dwell_stmt)
    avg_dwell_per_zone = {row[0]: round(row[1] or 0.0, 2) for row in dwell_result.all() if row[0]}

    # Latest queue depth from BILLING_QUEUE_JOIN metadata
    q_stmt = select(EventModel.metadata_json).where(
        and_(
            EventModel.store_id == store_id,
            EventModel.event_type == "BILLING_QUEUE_JOIN",
        )
    ).order_by(EventModel.timestamp.desc()).limit(1)
    q_result = await db.execute(q_stmt)
    latest_meta = q_result.scalar()
    queue_depth = latest_meta.get("queue_depth") if latest_meta else 0
    queue_depth = queue_depth or 0

    # Abandonment rate (non-staff, today)
    ab_join = select(func.count()).where(
        and_(
            EventModel.store_id == store_id,
            EventModel.event_type == "BILLING_QUEUE_JOIN",
            EventModel.is_staff == False,
            EventModel.timestamp >= start,
            EventModel.timestamp < end,
        )
    )
    ab_abandon = select(func.count()).where(
        and_(
            EventModel.store_id == store_id,
            EventModel.event_type == "BILLING_QUEUE_ABANDON",
            EventModel.is_staff == False,
            EventModel.timestamp >= start,
            EventModel.timestamp < end,
        )
    )
    j_val = (await db.execute(ab_join)).scalar() or 0
    a_val = (await db.execute(ab_abandon)).scalar() or 0
    abandonment_rate = round(a_val / j_val, 4) if j_val > 0 else 0.0

    return MetricOut(
        store_id=store_id,
        unique_visitors=unique_visitors,
        conversion_rate=conversion_rate,
        avg_dwell_per_zone=avg_dwell_per_zone,
        queue_depth=queue_depth,
        abandonment_rate=abandonment_rate,
        computed_at=datetime.now(timezone.utc),
    )
