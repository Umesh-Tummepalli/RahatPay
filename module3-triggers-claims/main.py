import asyncio
from fastapi import FastAPI
from contextlib import asynccontextmanager

from .routes.trigger_routes import router as trigger_router
from .triggers.monitor import trigger_monitor_loop

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Start polling external APIs
    print("Starting OpenWeatherMap monitor loop...")
    task = asyncio.create_task(trigger_monitor_loop())
    yield
    # Shutdown
    task.cancel()

app = FastAPI(title="Phase 2 - Module 3: Trigger & Claims", lifespan=lifespan)

# Mount Routes
app.include_router(trigger_router, prefix="/api/v1/triggers", tags=["Trigger & Claims"])

@app.get("/")
def health_check():
    return {"status": "Module 3 Component Alive", "service": "Triggers & Claims Engine"}
