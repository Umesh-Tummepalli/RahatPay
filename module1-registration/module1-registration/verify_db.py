import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
import os
import sys

# Assume local db using settings or default fallback
DATABASE_URL = "postgresql+asyncpg://rahatpay:rahatpay@localhost:5432/rahatpay"
engine = create_async_engine(DATABASE_URL, isolation_level="AUTOCOMMIT", echo=False)

async def run_sql_file(conn, filepath):
    if not os.path.exists(filepath):
        print(f"FAILED: File {filepath} not found.")
        sys.exit(1)
    
    with open(filepath, "r", encoding="utf-8") as f:
        sql = f.read()
    
    # Simple split heuristic if strictly needed; asyncpg .execute() handles multiple statements perfectly in many cases
    try:
        await conn.execute(text(sql))
        print(f"SUCCESS: Executed {filepath}")
    except Exception as e:
        print(f"FAILED: Failed to execute {filepath}. Error: {e}")
        sys.exit(1)

async def check_db_and_schema():
    print("Step 1/2: Checking database connection...")
    try:
        async with engine.begin() as conn:
            # Check DB start
            await conn.execute(text("SELECT 1"))
            print("SUCCESS: PostgreSQL is reachable.")
            
            # Clean before schema (cascade drop tables to be safe for test)
            tables = ["payouts", "claims", "disruption_events", "policies", "riders", "zones"]
            for table in tables:
                try:
                    await conn.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE;"))
                except Exception:
                    pass
            
            print("Step 2/2: Injecting schema and seed...")
            await run_sql_file(conn, "db/schema.sql")
            await run_sql_file(conn, "db/seed.sql")
            
    except Exception as e:
        print(f"FAILED: DB Connection or setup failed. Error: {e}")
        sys.exit(1)
        
if __name__ == "__main__":
    asyncio.run(check_db_and_schema())
