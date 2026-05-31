from __future__ import annotations

from datetime import datetime, timezone, timedelta
from uuid import uuid4

from fastapi import APIRouter, Depends
from sqlalchemy import select, func, and_, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AnomalyOut
from app.db.base import EventModel, SessionModel, AnomalyModel, DailyMetricModel
from app.db.session import get_db

router = APIRouter(prefix="/stores", tags=["stores"])


async def _compute_7day_stats(store_id: str, db: AsyncSession) -> dict:
    """Compute 7-day rolling averages for queue depth and conversion rate."""
    now = datetime.now(timezone.utc)
    seven_days_ago = now - timedelta(days=7)

    # Average queue depth from BILLING_QUEUE_JOIN events
    q_stmt = select(func.avg(EventModel.metadata_json["queue_depth"].as_float())).where(
        and_(
            EventModel.store_id == store_id,
            EventModel.event_type == "BILLING_QUEUE_JOIN",
            EventModel.timestamp >= seven_days_ago,
        )
    )
    q_avg = (await db.execute(q_stmt)).scalar() or 0.0

    # Stddev queue depth (approximate via raw SQL for JSONB)
    q_std_stmt = text("""
        SELECT STDDEV((metadata_json->>'queue_depth')::float)
        FROM events
        WHERE store_id = :sid AND event_type = 'BILLING_QUEUE_JOIN'
        AND timestamp >= :since
    """)
    q_std_result = await db.execute(q_std_stmt, {"sid": store_id, "since": seven_days_ago})
    q_std = q_std_result.scalar() or 0.0

    # Conversion rate from daily metrics if available, else compute from events
    conv_stmt = select(
        func.avg(DailyMetricModel.conversion_rate),
        func.stddev(DailyMetricModel.conversion_rate),
    ).where(
        and_(
            DailyMetricModel.store_id == store_id,
            DailyMetricModel.metric_date >= seven_days_ago,
        )
    )
    conv_result = await db.execute(conv_stmt)
    conv_row = conv_result.first()
    conv_avg = conv_row[0] or 0.0
    conv_std = conv_row[1] or 0.0

    return {
        "queue_avg": float(q_avg),
        "queue_std": float(q_std),
        "conv_avg": float(conv_avg),
        "conv_std": float(conv_std),
    }


@router.get("/{store_id}/anomalies", response_model=list[AnomalyOut])
async def get_anomalies(store_id: str, db: AsyncSession = Depends(get_db)) -> list[AnomalyOut]:
    now = datetime.now(timezone.utc)
    anomalies: list[AnomalyOut] = []

    stats = await _compute_7day_stats(store_id, db)

    # 1. Queue spike
    latest_q_stmt = (
        select(EventModel.metadata_json)
        .where(
            and_(
                EventModel.store_id == store_id,
                EventModel.event_type == "BILLING_QUEUE_JOIN",
            )
        )
        .order_by(EventModel.timestamp.desc())
        .limit(1)
    )
    latest_meta = (await db.execute(latest_q_stmt)).scalar()
    current_q = latest_meta.get("queue_depth") if latest_meta else 0
    current_q = current_q or 0

    q_threshold_warn = stats["queue_avg"] + 2 * stats["queue_std"]
    q_threshold_crit = stats["queue_avg"] + 3 * stats["queue_std"]

    if stats["queue_std"] > 0 and current_q > q_threshold_crit:
        anomalies.append(
            AnomalyOut(
                store_id=store_id,
                anomaly_type="QUEUE_SPIKE",
                severity="CRITICAL",
                message=f"Queue depth {current_q} exceeds 3σ threshold ({q_threshold_crit:.1f})",
                suggested_action="Open additional billing counter immediately",
                created_at=now,
            )
        )
    elif stats["queue_std"] > 0 and current_q > q_threshold_warn:
        anomalies.append(
            AnomalyOut(
                store_id=store_id,
                anomaly_type="QUEUE_SPIKE",
                severity="WARN",
                message=f"Queue depth {current_q} exceeds 2σ threshold ({q_threshold_warn:.1f})",
                suggested_action="Prepare additional billing counter",
                created_at=now,
            )
        )
    elif current_q >= 10:
        anomalies.append(
            AnomalyOut(
                store_id=store_id,
                anomaly_type="QUEUE_SPIKE",
                severity="WARN",
                message=f"Queue depth {current_q} exceeds the static alert threshold",
                suggested_action="Review billing throughput and deploy an additional cashier if needed",
                created_at=now,
            )
        )

    # 2. Conversion drop
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    uv_stmt = select(func.count(func.distinct(EventModel.visitor_id))).where(
        and_(
            EventModel.store_id == store_id,
            EventModel.is_staff == False,
            EventModel.event_type.in_(["ENTRY", "REENTRY"]),
            EventModel.timestamp >= today_start,
        )
    )
    uv = (await db.execute(uv_stmt)).scalar() or 0

    conv_stmt = select(func.count(func.distinct(SessionModel.visitor_id))).where(
        and_(
            SessionModel.store_id == store_id,
            SessionModel.is_staff == False,
            SessionModel.converted == True,
        )
    )
    conv = (await db.execute(conv_stmt)).scalar() or 0
    today_conv = conv / uv if uv > 0 else 0.0

    c_threshold_warn = stats["conv_avg"] - 2 * stats["conv_std"]
    c_threshold_crit = stats["conv_avg"] - 3 * stats["conv_std"]

    if stats["conv_std"] > 0 and today_conv < c_threshold_crit:
        anomalies.append(
            AnomalyOut(
                store_id=store_id,
                anomaly_type="CONVERSION_DROP",
                severity="CRITICAL",
                message=f"Conversion rate {today_conv:.2%} below 3σ threshold ({c_threshold_crit:.2%})",
                suggested_action="Investigate billing queue bottleneck and floor staff engagement",
                created_at=now,
            )
        )
    elif stats["conv_std"] > 0 and today_conv < c_threshold_warn:
        anomalies.append(
            AnomalyOut(
                store_id=store_id,
                anomaly_type="CONVERSION_DROP",
                severity="WARN",
                message=f"Conversion rate {today_conv:.2%} below 2σ threshold ({c_threshold_warn:.2%})",
                suggested_action="Review product placement and queue management",
                created_at=now,
            )
        )

    # 3. Dead zone (no visits in 30 min during open hours)
    thirty_min_ago = now - timedelta(minutes=30)
    zone_stmt = select(func.distinct(EventModel.zone_id)).where(
        and_(
            EventModel.store_id == store_id,
            EventModel.is_staff == False,
            EventModel.event_type == "ZONE_ENTER",
            EventModel.timestamp >= thirty_min_ago,
        )
    )
    active_zones = {row[0] for row in (await db.execute(zone_stmt)).all() if row[0]}

    # Assume all zones from store_layout; for challenge, infer from historical events
    all_zones_stmt = select(func.distinct(EventModel.zone_id)).where(
        and_(EventModel.store_id == store_id, EventModel.zone_id.isnot(None))
    )
    all_zones = {row[0] for row in (await db.execute(all_zones_stmt)).all() if row[0]}

    for zone in all_zones - active_zones:
        anomalies.append(
            AnomalyOut(
                store_id=store_id,
                anomaly_type="DEAD_ZONE",
                severity="WARN",
                message=f"No customer visits in zone {zone} for 30+ minutes",
                suggested_action=f"Check zone {zone} lighting, stock levels, and signage",
                created_at=now,
            )
        )

    # Persist anomalies (deduplicated — skip if same type + severity exists within last hour)
    one_hour_ago = now - timedelta(hours=1)
    for anom in anomalies:
        dup_check = (
            select(AnomalyModel)
            .where(
                and_(
                    AnomalyModel.store_id == anom.store_id,
                    AnomalyModel.anomaly_type == anom.anomaly_type,
                    AnomalyModel.severity == anom.severity,
                    AnomalyModel.created_at >= one_hour_ago,
                )
            )
            .limit(1)
        )
        existing = (await db.execute(dup_check)).scalar_one_or_none()
        if existing is not None:
            continue
        db.add(
            AnomalyModel(
                id=str(uuid4()),
                store_id=anom.store_id,
                anomaly_type=anom.anomaly_type,
                severity=anom.severity,
                message=anom.message,
                suggested_action=anom.suggested_action,
            )
        )
    await db.commit()

    return anomalies
