import os
import sys
import logging
import asyncio
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Ensure Module 3 imports its own `routes` package before Module 1 adds a
# similarly named package to the import path.
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
MODULE1_DIR = os.path.abspath(os.path.join(BASE_DIR, "../module1-registration"))

if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Allow importing db, models, and config from the registration module (shared core)
if MODULE1_DIR not in sys.path:
    sys.path.append(MODULE1_DIR)

# Load Module 3 local env first (non-committed)
load_dotenv(os.path.join(BASE_DIR, ".env"), override=False)

from routes import admin  # noqa: E402
from routes.triggers import router as triggers_router  # noqa: E402
from routes.claims import router as claims_router  # noqa: E402
from db.connection import init_db, close_db  # noqa: E402
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
