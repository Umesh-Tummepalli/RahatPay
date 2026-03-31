"""
db/connection.py
----------------
Async SQLAlchemy engine + session factory.
All routes receive a DB session via FastAPI dependency injection.
"""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text
import logging

from config import settings

logger = logging.getLogger(__name__)

# ── Engine ─────────────────────────────────────────────────────────────────────
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,       # Reconnect if connection dropped
    pool_recycle=3600,        # Recycle after 1 hour
    echo=settings.DB_ECHO,
)

# ── Session factory ────────────────────────────────────────────────────────────
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,   # Keep objects usable after commit
    autoflush=False,
    autocommit=False,
)

# ── Declarative base (shared by all models) ────────────────────────────────────
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
    Creates tables if they don't exist (dev convenience).
    In production, use alembic migrations instead.
    """
    async with engine.begin() as conn:
        # Import all models so Base.metadata is populated
        from models import rider, policy  # noqa: F401
        await conn.run_sync(Base.metadata.create_all)
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
        logger.error(f"DB health check failed: {e}")
        return False
