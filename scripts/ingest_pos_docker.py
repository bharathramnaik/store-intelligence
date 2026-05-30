import csv, asyncio, asyncpg
from datetime import datetime

async def main():
    conn = await asyncpg.connect('postgresql://postgres:postgres@db:5432/store_intelligence')
    inserted = 0
    with open('/data/pos_transactions.csv') as f:
        for row in csv.DictReader(f):
            ts = datetime.fromisoformat(row['timestamp'].replace('Z', '+00:00'))
            r = await conn.execute(
                "INSERT INTO pos_transactions (transaction_id, store_id, timestamp, basket_value_inr, correlated)"
                " VALUES ($1, $2, $3, $4, false)"
                " ON CONFLICT (transaction_id) DO NOTHING",
                row['transaction_id'], row['store_id'], ts, float(row['basket_value_inr']),
            )
            if r == 'INSERT 0 1':
                inserted += 1
    await conn.close()
    print(f'Ingested {inserted} POS transactions')

asyncio.run(main())
