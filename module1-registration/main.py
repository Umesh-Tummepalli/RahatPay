"""
main.py
-------
RahatPay Module 1 — FastAPI application entry point.

Starts the server, registers all routes, and handles startup/shutdown.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import IntegrityError, OperationalError

from config import settings
from db.connection import init_db, close_db, check_db_health
from routes.auth import router as auth_router
from routes.registration import router as registration_router
from routes.policy import router as policy_router
from routes.admin import router as admin_router

# ── Logging setup ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger("rahatpay.module1")


# ── Lifespan (replaces on_event startup/shutdown) ─────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION} [{settings.ENVIRONMENT}]")

    # Initialize DB (create tables if not exist)
    await init_db()

    # Optionally run seed data
    if settings.ENVIRONMENT == "development":
        try:
            await _run_seed_data()
        except Exception as e:
            logger.warning(f"Seed data failed (non-fatal): {e}")

    logger.info("Module 1 startup complete.")
    yield

    # Shutdown
    await close_db()
    logger.info("Module 1 shutdown complete.")


# ── App instance ──────────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "Module 1: Registration & Policy Management for RahatPay. "
        "Owns rider identity, policy lifecycle, and the core database schema. "
        "All other modules read from this module's tables."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)


# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Exception handlers ────────────────────────────────────────────────────────

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Return structured validation errors."""
    errors = []
    for err in exc.errors():
        field = " → ".join(str(loc) for loc in err["loc"])
        errors.append({"field": field, "message": err["msg"]})
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "Validation error", "errors": errors},
    )


@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError):
    logger.error(f"DB IntegrityError on {request.url}: {exc}")
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": "A database constraint was violated. Check for duplicate data."},
    )


@app.exception_handler(OperationalError)
async def db_operational_error_handler(request: Request, exc: OperationalError):
    logger.critical(f"DB OperationalError on {request.url}: {exc}")
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"detail": "Database is temporarily unavailable. Please try again."},
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled exception on {request.url}: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An unexpected error occurred. Please contact support."},
    )


# ── Routes ────────────────────────────────────────────────────────────────────
app.include_router(auth_router,          prefix="")
app.include_router(registration_router,  prefix="")
app.include_router(policy_router,        prefix="")
app.include_router(admin_router,         prefix="")


# ── Health & Meta ─────────────────────────────────────────────────────────────

@app.get("/health", tags=["Health"])
async def health_check():
    """Liveness probe — returns 200 if app is running."""
    db_healthy = await check_db_health()
    return {
        "status": "healthy" if db_healthy else "degraded",
        "module": "module1-registration",
        "version": settings.APP_VERSION,
        "database": "connected" if db_healthy else "disconnected",
    }


@app.get("/", tags=["Meta"])
async def root():
    return {
        "module": "RahatPay Module 1 — Registration & Policy Management",
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "health": "/health",
        "endpoints": {
            "auth": ["/auth/send-otp", "/auth/verify-otp"],
            "registration": ["/register"],
            "dashboard": ["/rider/{id}/dashboard"],
            "payouts": ["/rider/{id}/payouts"],
            "zones": ["/zones"],
            "tiers": ["/tiers"],
            "tier_change": ["/rider/{id}/change-tier"],
            "renewal": ["/rider/{id}/renew"],
            "admin": ["/admin/workers", "/admin/claims/live", "/admin/fraud/flagged", "/admin/analytics/financial"],
        },
    }


# ── Seed helper ───────────────────────────────────────────────────────────────

async def _run_seed_data():
    """Run seed.sql on development startup if zones table is empty."""
    import os
    from sqlalchemy import text
    from db.connection import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        result = await session.execute(text("SELECT COUNT(*) FROM zones"))
        count = result.scalar()
        if count == 0:
            seed_path = os.path.join(os.path.dirname(__file__), "db", "seed.sql")
            if os.path.exists(seed_path):
                with open(seed_path, "r") as f:
                    seed_sql = f.read()
                await session.execute(text(seed_sql))
                await session.commit()
                logger.info("Seed data inserted.")
            else:
                logger.warning("seed.sql not found — skipping.")
        else:
            logger.info(f"Zones table has {count} records — skipping seed.")


# ── Dev runner ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        reload=settings.DEBUG,
        log_level="debug" if settings.DEBUG else "info",
    )
