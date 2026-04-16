"""
main.py  (Module 3 — Triggers & Claims)
----------------------------------------
FastAPI application entry point.

Runs standalone:
    uvicorn main:app --reload --port 8003

No manual environment variable injection required.
No cross-module sys.path hacks.
.env is loaded automatically from this directory.
"""

import os
import sys
import logging
import asyncio
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# ── Ensure Module 3's own packages take priority ──────────────────────────────
# Insert this module's directory at index 0 so that `import config`,
# `import db`, `import models` all resolve to Module 3's own copies,
# NOT to any other module that might share the Python path.
_BASE_DIR = os.path.abspath(os.path.dirname(__file__))
if _BASE_DIR not in sys.path:
    sys.path.insert(0, _BASE_DIR)

# ── Load .env BEFORE importing anything that reads env vars ──────────────────
from dotenv import load_dotenv  # noqa: E402
load_dotenv(os.path.join(_BASE_DIR, ".env"), override=False)

# ── Application imports (all resolve to Module 3's own packages) ─────────────
from routes import admin          # noqa: E402
from routes.triggers import router as triggers_router  # noqa: E402
from routes.claims import router as claims_router      # noqa: E402
from db.connection import init_db, close_db            # noqa: E402
from triggers.monitor import start_trigger_polling_loop  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger("rahatpay.module3")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Module 3 (Triggers & Claims).")
    await init_db()

    polling_task: asyncio.Task | None = None
    try:
        polling_task = asyncio.create_task(start_trigger_polling_loop())
        yield
    finally:
        if polling_task:
            polling_task.cancel()
            try:
                await polling_task
            except asyncio.CancelledError:
                pass
        await close_db()
        logger.info("Module 3 shutdown complete.")


app = FastAPI(
    title="RahatPay Module 3 - Triggers & Claims Engine",
    description="Trigger polling + disruption events + claims orchestration.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(admin.router)
app.include_router(triggers_router)
app.include_router(claims_router)


@app.get("/health")
def health_check():
    return {"status": "healthy", "module": "triggers-claims"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8003, reload=True)
