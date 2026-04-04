"""
main.py

Standalone FastAPI server for Module 2 — for development/testing only.
Module 1 imports premium functions directly; these endpoints are for
your own testing and for the demo video.

Run:
    cd module2
    uvicorn main:app --reload --port 8002

Endpoints:
    POST /api/premium/calculate         — calculate premium for given params
    POST /api/premium/rider/{rider_id}  — calculate premium for a known rider
    GET  /api/premium/zone-risk/{pincode} — get zone risk with explanation
    GET  /api/baseline/{rider_id}       — get rider's baseline profile
    GET  /api/zones                     — list all supported zones
    GET  /healthz                       — health check
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

from premium.calculator import calculate_premium, calculate_premium_for_rider
from premium.zone_risk import get_zone_risk_full, ZONE_RISK_TABLE
from premium.profiler import get_baseline
from premium.seasonal import get_seasonal_factor, seasonal_label

app = FastAPI(
    title="RahatPay — Module 2: AI Risk Engine & Premium Calculator",
    description="Zone risk scoring, rolling baseline profiling, and dynamic premium calculation.",
    version="1.0.0",
)


# ── Request / Response models ─────────────────────────────────────────────────

class PremiumRequest(BaseModel):
    baseline_weekly_income: float = Field(..., gt=0, description="Rider's 4-week avg weekly income (₹)")
    tier: str                     = Field(..., description="kavach / suraksha / raksha")
    zone_pincodes: list[str]      = Field(..., min_length=1, max_length=3)
    city: str                     = Field(..., description="City name e.g. 'chennai'")
    month: Optional[int]          = Field(None, ge=1, le=12, description="1–12, defaults to current month")

    model_config = {
        "json_schema_extra": {
            "example": {
                "baseline_weekly_income": 3500,
                "tier": "suraksha",
                "zone_pincodes": ["600017", "600020", "600032"],
                "city": "chennai",
                "month": 7,
            }
        }
    }


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/healthz")
def health():
    return {
        "status": "ok",
        "module": "Module 2 — AI Risk Engine & Premium Calculator",
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.post("/api/premium/calculate")
def calculate_premium_endpoint(req: PremiumRequest):
    """
    Calculate weekly premium with full breakdown.
    Module 1 calls this (or imports directly) during policy creation.
    """
    try:
        result = calculate_premium(
            baseline_weekly_income=req.baseline_weekly_income,
            tier=req.tier,
            zone_pincodes=req.zone_pincodes,
            city=req.city,
            month=req.month,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/premium/rider/{rider_id}")
def calculate_premium_for_rider_endpoint(rider_id: int, tier: str, month: Optional[int] = None):
    """
    Calculate premium for an existing rider by ID.
    Looks up their baseline from activity history automatically.
    """
    try:
        result = calculate_premium_for_rider(rider_id=rider_id, tier=tier, month=month)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/api/premium/zone-risk/{pincode}")
def get_zone_risk_endpoint(pincode: str):
    """
    Get zone risk multiplier and explanation for a pin code.
    Admin dashboard zone heatmap calls this.
    """
    return get_zone_risk_full(pincode)


@app.get("/api/baseline/{rider_id}")
def get_baseline_endpoint(rider_id: int):
    """
    Get rider's baseline profile — income, hours, hourly rate, top zones.
    Module 3 calls this during payout calculation.
    """
    try:
        return get_baseline(rider_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/api/zones")
def list_zones():
    """
    List all supported zones with their risk scores.
    Useful for the zone selection dropdown in Module 1's registration flow.
    """
    return {
        "zones": [
            {
                "pincode": pincode,
                "area": data["area"],
                "city": data["city"],
                "risk_multiplier": data["risk"],
            }
            for pincode, data in ZONE_RISK_TABLE.items()
        ],
        "total": len(ZONE_RISK_TABLE),
    }


@app.get("/api/seasonal/{city}")
def get_seasonal_info(city: str, month: Optional[int] = None):
    """Get seasonal factor for a city + month combination."""
    factor = get_seasonal_factor(city, month)
    label = seasonal_label(factor)
    if month is None:
        month = datetime.now().month
    return {
        "city": city,
        "month": month,
        "seasonal_factor": factor,
        "seasonal_label": label,
    }

@app.get("/api/rider/{rider_id}/shift-window")
def get_shift_window(rider_id: int):
    """
    Returns a rider's typical shift window derived from last 15 days of activity.
    Module 3 calls this for eligibility gate 2 (shift overlap check).
    """
    import dummy_db as db
    rider = db.get_rider(rider_id)
    if not rider:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Rider {rider_id} not found")
    return db.get_rider_shift_window(rider_id)


@app.get("/api/rider/{rider_id}/daily-activity")
def get_daily_activity(rider_id: int, days: int = 15):
    """
    Returns last N days of daily activity for a rider.
    Used by Module 3 and Module 5 to simulate the 15-day analysis window.
    """
    import dummy_db as db
    rider = db.get_rider(rider_id)
    if not rider:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Rider {rider_id} not found")
    return {
        "rider_id": rider_id,
        "days_requested": days,
        "activity": db.get_daily_activity(rider_id, last_n_days=days),
    }