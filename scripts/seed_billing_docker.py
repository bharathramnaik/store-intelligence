import uuid, json, asyncio, asyncpg
from datetime import datetime, timezone, timedelta

async def main():
    conn = await asyncpg.connect('postgresql://postgres:postgres@db:5432/store_intelligence')

    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    # Get non-staff sessions ordered by time
    rows = await conn.fetch(
        "SELECT visitor_id, store_id, start_time FROM sessions"
        " WHERE is_staff = false AND start_time >= $1"
        " ORDER BY start_time ASC",
        today,
    )
    print(f"Found {len(rows)} non-staff sessions")

    # Get POS transactions
    pos_txns = await conn.fetch(
        "SELECT transaction_id, timestamp FROM pos_transactions ORDER BY timestamp ASC"
    )
    print(f"Found {len(pos_txns)} POS transactions")

    # Match sessions to POS transactions by order (first N sessions get matched)
    billing_count = 0
    for i in range(min(len(pos_txns), min(20, len(rows)))):
        session = rows[i]
        txn = pos_txns[i]
        vid = session["visitor_id"]
        txn_ts = txn["timestamp"]

        # Inject BILLING_QUEUE_JOIN 2 minutes before transaction
        billing_ts = txn_ts - timedelta(minutes=2)
        evt_id = str(uuid.uuid4())
        await conn.execute(
            "INSERT INTO events (event_id, store_id, camera_id, visitor_id, event_type,"
            " timestamp, zone_id, dwell_ms, is_staff, confidence, metadata_json)"
            " VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11::jsonb)"
            " ON CONFLICT (event_id) DO NOTHING",
            evt_id, session["store_id"], "CAM_FLOOR_01", vid,
            "BILLING_QUEUE_JOIN", billing_ts, "BILLING", 0, False, 0.85,
            json.dumps({"queue_depth": 2, "sku_zone": "BILLING", "session_seq": 0}),
        )
        billing_count += 1

    print(f"Injected {billing_count} BILLING_QUEUE_JOIN events (matched to sessions)")

    # Also inject abandon events for sessions without POS match
    abandon_count = 0
    for i in range(billing_count, min(billing_count + 8, len(rows))):
        session = rows[i]
        vid = session["visitor_id"]
        ts = session["start_time"] + timedelta(minutes=3)
        evt_id = str(uuid.uuid4())
        await conn.execute(
            "INSERT INTO events (event_id, store_id, camera_id, visitor_id, event_type,"
            " timestamp, zone_id, dwell_ms, is_staff, confidence, metadata_json)"
            " VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11::jsonb)"
            " ON CONFLICT (event_id) DO NOTHING",
            evt_id, session["store_id"], "CAM_FLOOR_01", vid,
            "BILLING_QUEUE_ABANDON", ts, "BILLING", 120000, False, 0.85,
            json.dumps({"queue_depth": None, "sku_zone": "BILLING", "session_seq": 0}),
        )
        abandon_count += 1

    print(f"Injected {abandon_count} BILLING_QUEUE_ABANDON events")
    await conn.close()

asyncio.run(main())
