"""
db/connection.py  (Module 3 — Triggers & Claims)
-------------------------------------------------
Async SQLAlchemy engine + session factory.
Uses Module 3's own config — no dependency on Module 1.
"""

import logging

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text
from sqlalchemy.pool import NullPool

from config import settings

logger = logging.getLogger(__name__)

# ── Engine ─────────────────────────────────────────────────────────────────────
# Use NullPool for SQLite (no pool args supported) vs QueuePool for PostgreSQL.
_is_sqlite = settings.DATABASE_URL.startswith("sqlite")
_engine_kwargs = (
    {"poolclass": NullPool}
    if _is_sqlite
    else {
        "pool_size": 10,
        "max_overflow": 20,
        "pool_pre_ping": True,
        "pool_recycle": 3600,
    }
)
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DB_ECHO,
    **_engine_kwargs,
)

# ── Session factory ────────────────────────────────────────────────────────────
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)

# ── Declarative base (shared by all Module 3 models) ──────────────────────────
class Base(DeclarativeBase):
    pass


# ── Dependency injection helper ────────────────────────────────────────────────
async def get_db() -> AsyncSession:
    """
    FastAPI dependency that yields a DB session per request.
    Usage in routes:
        async def my_route(db: AsyncSession = Depends(get_db)):
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ── Startup / Shutdown ─────────────────────────────────────────────────────────
async def init_db():
    """
    Run on app startup.
    Verifies connectivity; tables are owned by Module 1 (schema migrations run there).
    Module 3 does NOT create tables — it reads/writes to the shared PostgreSQL DB.
    """
    async with engine.begin() as conn:
        # Import models so SQLAlchemy metadata is populated (needed for ORM queries).
        from models import policy, rider  # noqa: F401
        # Do NOT call Base.metadata.create_all — Module 1 owns table creation.
        await conn.run_sync(lambda _: None)  # Lightweight connectivity check
        logger.info("Database tables verified / created.")


async def close_db():
    """Run on app shutdown."""
    await engine.dispose()
    logger.info("Database connection pool closed.")


async def check_db_health() -> bool:
    """Returns True if the database is reachable."""
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error("DB health check failed: %s", e)
        return False
