from __future__ import annotations

from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import HealthOut, HealthStoreStatus
from app.db.base import EventModel
from app.db.session import get_db

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthOut)
async def health_check(db: AsyncSession = Depends(get_db)) -> HealthOut:
    now = datetime.now(timezone.utc)
    ten_min_ago = now - timedelta(minutes=10)

    try:
        stmt = select(EventModel.store_id, func.max(EventModel.timestamp)).group_by(EventModel.store_id)
        result = await db.execute(stmt)
        rows = result.all()

        stores = []
        for store_id, last_ts in rows:
            status = "ACTIVE" if last_ts and last_ts >= ten_min_ago else "STALE_FEED"
            stores.append(HealthStoreStatus(
                store_id=store_id,
                last_event_timestamp=last_ts,
                status=status,
            ))

        service = "healthy"
    except Exception:
        service = "degraded"
        stores = []

    return HealthOut(service=service, stores=stores, timestamp=now)
