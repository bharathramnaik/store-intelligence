from __future__ import annotations

from datetime import datetime, timezone, timedelta

from sqlalchemy import select, and_, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import PosTransactionModel, EventModel, SessionModel
from app.core.logging import logger


async def correlate_pos_transactions(db: AsyncSession) -> None:
    """Background task: correlate POS transactions with visitor sessions."""
    # Find uncorrelated transactions
    stmt = select(PosTransactionModel).where(PosTransactionModel.correlated == False)
    result = await db.execute(stmt)
    transactions = result.scalars().all()

    for txn in transactions:
        window_start = txn.timestamp - timedelta(minutes=5)
        # Find visitors in billing zone within 5 min before transaction
        evt_stmt = select(func.distinct(EventModel.visitor_id)).where(
            and_(
                EventModel.store_id == txn.store_id,
                EventModel.event_type.in_(["BILLING_QUEUE_JOIN", "ZONE_ENTER"]),
                EventModel.zone_id == "BILLING",
                EventModel.timestamp >= window_start,
                EventModel.timestamp <= txn.timestamp,
                EventModel.is_staff == False,
            )
        )
        evt_result = await db.execute(evt_stmt)
        visitor_ids = evt_result.scalars().all()

        if visitor_ids:
            await db.execute(
                update(SessionModel)
                .where(
                    and_(
                        SessionModel.visitor_id.in_(visitor_ids),
                        SessionModel.store_id == txn.store_id,
                    )
                )
                .values(converted=True)
            )
            txn.correlated = True
            logger.info("pos_correlated", transaction_id=txn.transaction_id, visitors=len(visitor_ids))

    await db.commit()
