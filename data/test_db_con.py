import asyncio, asyncpg

async def test():
    conn = await asyncpg.connect(
        "postgresql://store_intelligence_ih6t_user:FAJT3yKUeIpak3AAnXc5Mw72ZRBSWKQk@dpg-d8dsiin40ujc73d0urj0-a/store_intelligence_ih6t"
    )
    v = await conn.fetchval("SELECT version()")
    tables = await conn.fetch("SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname='public'")
    print(f"PostgreSQL: {v}")
    print(f"Tables: {[r[0] for r in tables]}")
    await conn.close()

asyncio.run(test())
