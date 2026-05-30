from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta

import asyncpg


async def main() -> None:
    dsn = "postgresql://postgres:postgres@localhost:5432/store_intelligence"
    conn = await asyncpg.connect(dsn)

    # Get non-staff sessions from today
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    rows = await conn.fetch(
        """SELECT visitor_id, store_id, start_time FROM sessions
           WHERE is_staff = false AND start_time >= $1
           ORDER BY start_time ASC""",
        today,
    )
    print(f"Found {len(rows)} non-staff sessions")

    if not rows:
        print("No sessions found — ingest events first")
        return

    # Inject BILLING_QUEUE_JOIN events for first 30 sessions
    # with timestamps 2-5 min before POS transactions
    pos_txns = await conn.fetch(
        "SELECT transaction_id, timestamp FROM pos_transactions ORDER BY timestamp ASC"
    )
    print(f"Found {len(pos_txns)} POS transactions")

    billing_events = 0
    for session in rows[:30]:
        visitor_id = session["visitor_id"]
        session_start = session["start_time"]

        # Find nearest POS transaction within 5 min after this session
        for txn in pos_txns:
            if txn["timestamp"] > session_start and (txn["timestamp"] - session_start).total_seconds() <= 600:
                # Inject BILLING_QUEUE_JOIN ~2 min before transaction
                billing_ts = txn["timestamp"] - timedelta(minutes=2)
                evt_id = str(uuid.uuid4())
                await conn.execute(
                    """INSERT INTO events (event_id, store_id, camera_id, visitor_id, event_type,
                       timestamp, zone_id, dwell_ms, is_staff, confidence, metadata_json)
                       VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                       ON CONFLICT (event_id) DO NOTHING""",
                    evt_id,
                    session["store_id"],
                    "CAM_FLOOR_01",
                    visitor_id,
                    "BILLING_QUEUE_JOIN",
                    billing_ts,
                    "BILLING",
                    0,
                    False,
                    0.85,
                    {"queue_depth": 2, "sku_zone": "BILLING", "session_seq": 0},
                )
                billing_events += 1
                break

    print(f"Injected {billing_events} BILLING_QUEUE_JOIN events")

    # Also inject BILLING_QUEUE_ABANDON events for next 10 sessions
    abandon_events = 0
    for session in rows[30:40]:
        visitor_id = session["visitor_id"]
        ts = session["start_time"] + timedelta(minutes=3)
        evt_id = str(uuid.uuid4())
        await conn.execute(
            """INSERT INTO events (event_id, store_id, camera_id, visitor_id, event_type,
               timestamp, zone_id, dwell_ms, is_staff, confidence, metadata_json)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
               ON CONFLICT (event_id) DO NOTHING""",
            evt_id,
            session["store_id"],
            "CAM_FLOOR_01",
            visitor_id,
            "BILLING_QUEUE_ABANDON",
            ts,
            "BILLING",
            120000,
            False,
            0.85,
            {"queue_depth": None, "sku_zone": "BILLING", "session_seq": 0},
        )
        abandon_events += 1

    print(f"Injected {abandon_events} BILLING_QUEUE_ABANDON events")

    await conn.close()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
