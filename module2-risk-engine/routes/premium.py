from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

router = APIRouter(prefix="/evaluate", tags=["Risk Engine & Pricing"])

# ── Business Constants (Moved from config) ─────────────────────────
PREMIUM_FLOOR = 15.0          # ₹15 minimum weekly premium
PREMIUM_CAP_PERCENT = 0.035   # 3.5% of income maximum

TIER_CONFIG = {
    "kavach": {"tier_rate": 0.015},
    "suraksha": {"tier_rate": 0.018},
    "raksha": {"tier_rate": 0.022},
}

SEASONAL_FACTORS = {
    1: 0.90, 2: 0.88, 3: 0.92, 4: 0.95, 5: 1.00, 6: 1.20,
    7: 1.25, 8: 1.25, 9: 1.15, 10: 1.05, 11: 0.95, 12: 0.90,
}

CITY_MEDIAN_INCOME = {
    "Chennai": 3500.00, "Mumbai": 4200.00, 
    "Bangalore": 4000.00, "Delhi": 3800.00,
}
CITY_MEDIAN_HOURS = {
    "Chennai": 40.0, "Mumbai": 42.0, 
    "Bangalore": 41.0, "Delhi": 40.0,
}

_ZONE_RISK_TABLE = {
    1: 1.20, 2: 1.15, 3: 1.10, 4: 1.05, 5: 1.00, 6: 0.95,
    7: 1.25, 8: 1.10, 9: 1.30, 10: 1.20, 11: 1.15, 12: 1.35,
    13: 1.00, 14: 1.05, 15: 1.10, 16: 1.08, 17: 1.25, 18: 1.15,
    19: 1.40, 20: 1.35,
}

# ── Schemas ────────────────────────────────────────────────────────
class BaselineRequest(BaseModel):
    rider_id: str
    city: str
    is_seasoning: bool

class PremiumRequest(BaseModel):
    income: float
    tier: str
    zones: List[int]
    month: Optional[int] = None

# ── Endpoints ──────────────────────────────────────────────────────

@router.post("/baseline")
async def evaluate_baseline(request: BaselineRequest):
    """City-level median used as provisional baseline during seasoning."""
    city_key = request.city.strip().title()
    income = CITY_MEDIAN_INCOME.get(city_key, 3500.00)
    hours  = CITY_MEDIAN_HOURS.get(city_key, 40.0)
    
    return {
        "income": income,
        "hours": hours,
        "hourly_rate": round(income / hours, 2) if hours > 0 else 0.0,
        "is_provisional": True, # Hardcoded to true for this mock version
    }

@router.post("/premium")
async def evaluate_premium(request: PremiumRequest):
    tier_cfg = TIER_CONFIG.get(request.tier.lower())
    if not tier_cfg:
        return {"error": f"Unknown tier: {request.tier}"}

    tier_rate = tier_cfg["tier_rate"]
    
    # Average zone risk across all rider zones
    risks = [_ZONE_RISK_TABLE.get(z, 1.0) for z in request.zones if z]
    zone_risk = round(sum(risks) / len(risks), 4) if risks else 1.0

    # Seasonal factor from current month
    current_month = request.month or datetime.now().month
    seasonal_factor = SEASONAL_FACTORS.get(current_month, 1.0)

    # Core formula
    raw_premium = request.income * tier_rate * zone_risk * seasonal_factor

    # FIX: The Cap vs Floor Caution!
    # To protect low-income gig workers, if the computed premium hits the 3.5% cap,
    # the CAP must win over the floor so we don't accidentally charge 10%+ of small incomes.
    raw_premium_floored = max(raw_premium, PREMIUM_FLOOR)
    floor_applied = raw_premium < PREMIUM_FLOOR

    cap_amount = request.income * PREMIUM_CAP_PERCENT
    cap_applied = (request.income > 0) and (raw_premium_floored > cap_amount)
    
    final_premium = min(raw_premium_floored, cap_amount)
    # Edge case: If income is zero, premium should be 0, not 15.
    if request.income <= 0:
        final_premium = 0.0
        
    final_premium = round(final_premium, 2)

    return {
        "weekly_premium": final_premium,
        "breakdown": {
            "income": request.income,
            "tier_rate": tier_rate,
            "zone_risk": zone_risk,
            "seasonal_factor": seasonal_factor,
            "raw_premium": raw_premium,
            "floor_applied": floor_applied,
            "cap_applied": cap_applied,
            "final_premium": final_premium,
        }
    }
