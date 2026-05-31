from __future__ import annotations


from fastapi import APIRouter, Depends
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import HeatmapOut, HeatmapZone
from app.db.base import EventModel, SessionModel
from app.db.session import get_db
from app.core.date_utils import today_bounds

router = APIRouter(prefix="/stores", tags=["stores"])


@router.get("/{store_id}/heatmap", response_model=HeatmapOut)
async def get_heatmap(store_id: str, db: AsyncSession = Depends(get_db)) -> HeatmapOut:
    start, end = today_bounds()

    # Total sessions in window for confidence flag
    sess_stmt = select(func.count(func.distinct(SessionModel.visitor_id))).where(
        and_(
            SessionModel.store_id == store_id,
            SessionModel.is_staff == False,
        )
    )
    total_sessions = (await db.execute(sess_stmt)).scalar() or 0

    # Only count ZONE_ENTER from visitors who entered the store
    entering_ids = select(EventModel.visitor_id).where(
        and_(
            EventModel.store_id == store_id,
            EventModel.is_staff == False,
            EventModel.event_type.in_(["ENTRY", "REENTRY"]),
            EventModel.timestamp >= start,
            EventModel.timestamp < end,
        )
    )
    stmt = (
        select(
            EventModel.zone_id,
            func.count().label("visit_freq"),
        )
        .where(
            and_(
                EventModel.store_id == store_id,
                EventModel.is_staff == False,
                EventModel.event_type == "ZONE_ENTER",
                EventModel.timestamp >= start,
                EventModel.timestamp < end,
                EventModel.visitor_id.in_(entering_ids),
            )
        )
        .group_by(EventModel.zone_id)
    )

    result = await db.execute(stmt)
    rows = result.all()

    dwell_stmt = (
        select(
            EventModel.zone_id,
            func.avg(EventModel.dwell_ms).label("avg_dwell"),
        )
        .where(
            and_(
                EventModel.store_id == store_id,
                EventModel.is_staff == False,
                EventModel.event_type.in_(["ZONE_DWELL", "ZONE_EXIT"]),
                EventModel.dwell_ms > 0,
                EventModel.timestamp >= start,
                EventModel.timestamp < end,
                EventModel.visitor_id.in_(entering_ids),
            )
        )
        .group_by(EventModel.zone_id)
    )
    dwell_rows = {
        row.zone_id: round(row.avg_dwell or 0.0, 2)
        for row in (await db.execute(dwell_stmt)).all()
        if row.zone_id
    }

    zones = []
    if rows:
        freqs = [r.visit_freq for r in rows]
        min_freq = min(freqs)
        max_freq = max(freqs)
        for r in rows:
            norm = (
                (r.visit_freq - min_freq) / (max_freq - min_freq) * 100
                if max_freq > min_freq
                else 100.0
            )
            zones.append(
                HeatmapZone(
                    zone_id=r.zone_id or "UNKNOWN",
                    visit_frequency=r.visit_freq,
                    avg_dwell_ms=dwell_rows.get(r.zone_id or "", 0.0),
                    normalized_score=round(norm, 2),
                )
            )

    return HeatmapOut(
        store_id=store_id,
        zones=zones,
        data_confidence="HIGH" if total_sessions >= 20 else "LOW",
    )
