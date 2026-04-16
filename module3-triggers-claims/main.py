import sys
import os

# Ensure Module 3 imports its own `routes` package before Module 1 adds a
# similarly named package to the import path.
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
MODULE1_DIR = os.path.abspath(os.path.join(BASE_DIR, "../module1-registration"))

if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Allow importing db, models, and config from the registration module (shared core)
if MODULE1_DIR not in sys.path:
    sys.path.append(MODULE1_DIR)

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import admin, claims, triggers
from monitor import ensure_trigger_polling_started

app = FastAPI(
    title="RahatPay Module 3 - Triggers & Claims Engine",
    description="Rule-based engine running eligibility checks and generating disruption payouts.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(admin.router)
app.include_router(claims.router)
app.include_router(triggers.router)


@app.on_event("startup")
async def _start_polling_loop():
    ensure_trigger_polling_started()

@app.get("/health")
def health_check():
    return {"status": "healthy", "module": "triggers-claims"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8003, reload=True)
