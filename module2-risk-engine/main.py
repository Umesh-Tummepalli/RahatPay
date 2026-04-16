"""
main.py

Standalone FastAPI server for Module 2 — Risk Engine & Premium Calculator.
Module 1 imports premium functions directly; these endpoints are for
integration, testing, and the demo video.

Run:
    cd module2-risk-engine
    uvicorn main:app --reload --port 8002

Endpoints:
    POST /api/premium/calculate            — calculate premium for given params
    POST /api/premium/rider/{rider_id}     — calculate premium for a known rider
    GET  /api/premium/zone-risk/{pincode}  — get zone risk with explanation
    GET  /api/baseline/{rider_id}          — get rider's baseline profile
    GET  /api/zones                        — list all supported zones
    GET  /api/seasonal/{city}              — get seasonal factor for a city/month
    GET  /api/rider/{id}/shift-window      — rider's typical shift window
    GET  /api/rider/{id}/daily-activity    — rider's last N days of activity
    POST /evaluate/baseline                — Module 1 adapter alias (contract fix)
    POST /evaluate/premium                 — Module 1 adapter alias (contract fix)
    POST /api/fraud/check-zone             — zone-level event plausibility check
    POST /api/fraud/check-rider            — per-rider claim fraud scoring
    POST /api/fraud/score-spoof            — GPS/sensor spoof detection
    GET  /api/model/info                   — ML model metadata (IRDAI audit trail)
    GET  /healthz                          — health check
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


# ═══════════════════════════════════════════════════════════════════════════════
# Module 1 Adapter Aliases — Fix contract mismatch
# Module 1's module2_adapter.py calls /evaluate/* but Module 2 was exposing /api/*
# These aliases bridge the gap without breaking existing endpoints.
# ═══════════════════════════════════════════════════════════════════════════════

class EvalBaselineRequest(BaseModel):
    rider_id:     str = Field(..., description="Rider ID (string or int)")
    city:         str = Field("chennai", description="City name")
    is_seasoning: bool = Field(False, description="True if rider has < 4 weeks of history")

class EvalPremiumRequest(BaseModel):
    income: float     = Field(..., gt=0, description="Rider's weekly income baseline (₹)")
    tier:   str       = Field(..., description="kavach / suraksha / raksha")
    zones:  list[str] = Field(default_factory=list, description="Zone pincodes")
    city:   str       = Field("chennai")
    month:  Optional[int] = Field(None, ge=1, le=12)


@app.post("/evaluate/baseline", tags=["Module1 Aliases"])
def evaluate_baseline_alias(req: EvalBaselineRequest):
    """
    Alias for GET /api/baseline/{rider_id}.
    Called by module1/integrations/module2_adapter.py — fixes contract mismatch.
    """
    try:
        rider_id = int(req.rider_id)
        b = get_baseline(rider_id)
        return {
            "income":       b["weekly_income"],
            "hours":        b["weekly_hours"],
            "hourly_rate":  b["hourly_rate"],
            "is_provisional": (b.get("source") != "rolling_4week"),
            "city":         req.city,
            "rider_id":     rider_id,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/evaluate/premium", tags=["Module1 Aliases"])
def evaluate_premium_alias(req: EvalPremiumRequest):
    """
    Alias for POST /api/premium/calculate.
    Called by module1/integrations/module2_adapter.py — fixes contract mismatch.
    """
    try:
        result = calculate_premium(
            baseline_weekly_income=req.income,
            tier=req.tier,
            zone_pincodes=req.zones if req.zones else ["600017"],
            city=req.city,
            month=req.month,
        )
        bd = result["breakdown"]
        return {
            "weekly_premium": result["weekly_premium_inr"],
            "breakdown": {
                "income":          bd["baseline_income"],
                "tier_rate":       bd["tier_rate"],
                "zone_risk":       bd["zone_risk"],
                "seasonal_factor": bd["seasonal_factor"],
                "raw_premium":     bd["raw_premium"],
                "floor_applied":   "Floor" in str(bd.get("guardrail_applied", "")),
                "cap_applied":     any(k in str(bd.get("guardrail_applied", ""))
                                       for k in ("Cap", "Ceiling", "cap")),
                "final_premium":   result["weekly_premium_inr"],
            },
        }
    except (ValueError, KeyError) as e:
        raise HTTPException(status_code=400, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════════════
# Fraud Detection Endpoints
# Called by Module 3 before disbursing claims and by Admin dashboard.
# ═══════════════════════════════════════════════════════════════════════════════

class FraudZoneRequest(BaseModel):
    event_id:              Optional[int] = Field(None, description="Disruption event ID from Module 3")
    zone_pincode:         str = Field(..., description="Disruption event pincode")
    event_type:           str = Field(..., description="heavy_rain | flood | cyclone | poor_aqi | heatwave | civic")
    event_hour:           int = Field(..., ge=0, le=23, description="Hour the event started (0-23)")
    num_riders_claiming:  int = Field(..., ge=0,  description="Count of riders claiming for this event")
    enrolled_riders:      int = Field(1, ge=1, description="Total riders enrolled in the zone")
    claims:               list[dict] = Field(default_factory=list, description="List of claim dictionaries")
    is_api_verified:      bool = Field(False, description="Verified by external API?")

class FraudRiderRequest(BaseModel):
    rider_id:                   int         = Field(..., description="Rider's integer ID")
    claim_amount:               float       = Field(..., gt=0)
    weekly_cap:                 float       = Field(..., gt=0)
    disruption_zone_pincode:    str
    rider_zones:                list[str]   = Field(..., min_length=1)
    event_start_hour:           int         = Field(..., ge=0, le=23)
    shift_start:                int         = Field(..., ge=0, le=23)
    shift_end:                  int         = Field(..., ge=0, le=23)
    recent_claim_count_7days:   int         = Field(0, ge=0)
    zone_recent_mean_claims_7days: float    = Field(0.0, ge=0)
    event_id:                   str
    already_claimed_event_ids:  list[str]   = Field(default_factory=list)
    claim_id:                   Optional[int] = None

class SpoofRequest(BaseModel):
    rider_id:               int             = Field(..., description="Rider ID")
    gps_accuracy_m:         Optional[float] = Field(None, description="GPS accuracy in metres")
    accelerometer_variance: Optional[float] = Field(None, description="Accelerometer magnitude variance")
    gyroscope_variance:     Optional[float] = Field(None, description="Gyroscope variance")
    wifi_ssid_count:        Optional[int]   = Field(None, description="Count of visible Wi-Fi SSIDs")
    device_id:              str             = Field("unknown", description="Mobile device identifier")


@app.post("/api/fraud/check-zone", tags=["Fraud"])
def fraud_check_zone(req: FraudZoneRequest):
    """
    Zone-level plausibility check before bulk claim creation using Isolation Forest.
    Module 3 calls this when a disruption event is first detected.
    """
    from fraud.detector import check_zone_fraud
    
    # Run the Isolation Forest model
    results = check_zone_fraud(
        event_id=req.event_id or 0,
        claims=req.claims,
        is_api_verified=req.is_api_verified,
        enrolled_riders=req.enrolled_riders
    )
    
    # If the batch was flagged, it's a mass claim
    mass_claim_flag = any(r["flagged"] for r in results)
    
    return {
        "zone_pincode":            req.zone_pincode,
        "event_type":              req.event_type,
        "mass_claim_flag":         mass_claim_flag,
        "mass_claim_riders":       req.num_riders_claiming,
        "recommendation":          "manual_review" if mass_claim_flag else "proceed",
        "claim_evaluations":       results,
        "timestamp":               datetime.utcnow().isoformat(),
    }


@app.post("/api/fraud/check-rider", tags=["Fraud"])
def fraud_check_rider(req: FraudRiderRequest):
    """
    Per-rider fraud check for a single claim.
    Module 3 calls this after payout calculation, before disbursement.

    Returns: fraud_score (0-1), verdict (pass/review/flag), recommended_status.
    """
    from fraud.detector import check_rider_claim
    result = check_rider_claim(
        rider_id=req.rider_id,
        claim_amount=req.claim_amount,
        weekly_cap=req.weekly_cap,
        disruption_zone_pincode=req.disruption_zone_pincode,
        rider_zones=req.rider_zones,
        event_start_hour=req.event_start_hour,
        shift_start=req.shift_start,
        shift_end=req.shift_end,
        recent_claim_count_7days=req.recent_claim_count_7days,
        zone_recent_mean_claims_7days=req.zone_recent_mean_claims_7days,
        event_id=req.event_id,
        already_claimed_event_ids=req.already_claimed_event_ids,
        claim_id=req.claim_id,
    )
    return {
        "rider_id":           result.rider_id,
        "claim_id":           result.claim_id,
        "fraud_score":        result.score,
        "verdict":            result.verdict,
        "recommended_status": result.recommended_status,
        "signals":            result.signals,
        "reasons":            result.reasons,
        "timestamp":          datetime.utcnow().isoformat(),
    }


@app.post("/api/fraud/score-spoof", tags=["Fraud"])
def fraud_score_spoof(req: SpoofRequest):
    """
    GPS/sensor spoof detection via Gradient Boosting Classifier.
    """
    from fraud.spoof_scorer import score_sensor_payload
    
    sensor_data = {
        "gps_accuracy": req.gps_accuracy_m if req.gps_accuracy_m is not None else 50.0,
        "accel_variance": req.accelerometer_variance if req.accelerometer_variance is not None else 0.0,
        "gyro_variance": req.gyroscope_variance if req.gyroscope_variance is not None else 0.0,
        "mag_variance": 0.0,  # Not provided in request, default to 0
        "wifi_ssid_count": req.wifi_ssid_count if req.wifi_ssid_count is not None else 1,
    }
    
    result = score_sensor_payload(
        rider_id=req.rider_id,
        sensor_data=sensor_data
    )
    return {
        "rider_id":    result.rider_id,
        "spoof_score": result.score,
        "verdict":     result.verdict,
        "signals":     result.signals,
        "reasons":     result.reasons,
        "timestamp":   datetime.utcnow().isoformat(),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Model Info Endpoint — IRDAI compliance / Admin dashboard
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/api/model/info", tags=["Model"])
def model_info():
    """
    Returns metadata about the loaded ML risk models.
    """
    from premium.zone_risk import _load_model
    import os
    import pickle
    from datetime import datetime as dt

    def _model_meta(path: str, trained_on: str) -> dict:
        if not os.path.exists(path):
            return {"status": "missing", "trained_on": trained_on}
        mtime = dt.utcfromtimestamp(os.path.getmtime(path)).isoformat()
        try:
            with open(path, "rb") as fh:
                model_obj = pickle.load(fh)
            algorithm = type(model_obj).__name__
        except Exception:
            algorithm = "unknown"
        return {
            "status": "loaded",
            "trained_on": trained_on,
            "algorithm": algorithm,
            "file": path,
            "last_trained_utc": mtime,
        }

    model = _load_model()
    model_loaded = model is not None
    pincode_count = len(getattr(model, "_pincode_features", {})) if model_loaded else 0
    zone_meta = _model_meta("models/zone_fraud_iforest.pkl", "Mass Claim Batch Density")
    spoof_meta = _model_meta("models/spoof_detector.pkl", "6-Dimensional Sensor Payloads")

    return {
        "models": {
            "risk_engine": {
                "algorithm": "XGBoostRegressor (GridSearchCV Optimized)",
                "status": "loaded" if model_loaded else "fallback_lookup_table",
                "feature_count": pincode_count,
            },
            "zone_fraud_detector": {
                "algorithm": "Ensemble: IsolationForest + LocalOutlierFactor (LOF)",
                "voting_strategy": "OR — flagged if EITHER model detects anomaly",
                **zone_meta,
            },
            "gps_spoof_scorer": {
                **spoof_meta,
            }
        },
        "compliance": {
            "irdai_objective_trigger":   True,
            "zero_touch_processing":     True,
            "audit_trail":               "Full breakdown returned on every prediction",
            "human_override_available":  True,
        },
        "timestamp": datetime.utcnow().isoformat(),
    }