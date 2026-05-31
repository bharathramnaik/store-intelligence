from __future__ import annotations

import argparse
import csv
from datetime import datetime

import asyncpg


async def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest POS transactions CSV into the database")
    parser.add_argument("--csv", required=True, help="Path to pos_transactions.csv")
    parser.add_argument(
        "--dsn", default="postgresql://postgres:postgres@localhost:5432/store_intelligence"
    )
    args = parser.parse_args()

    conn = await asyncpg.connect(args.dsn)

    inserted = 0
    skipped = 0
    with open(args.csv, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            ts = datetime.fromisoformat(row["timestamp"].replace("Z", "+00:00"))
            r = await conn.execute(
                """INSERT INTO pos_transactions (transaction_id, store_id, timestamp, basket_value_inr, correlated)
                   VALUES ($1, $2, $3, $4, false)
                   ON CONFLICT (transaction_id) DO NOTHING""",
                row["transaction_id"],
                row["store_id"],
                ts,
                float(row["basket_value_inr"]),
            )
            if r == "INSERT 0 1":
                inserted += 1
            else:
                skipped += 1

    await conn.close()
    print(f"Ingested {inserted} POS transactions, skipped {skipped} (duplicates)")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
