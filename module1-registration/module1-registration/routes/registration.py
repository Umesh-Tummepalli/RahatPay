"""
routes/registration.py
-----------------------
POST /register — Rider registration endpoint.

This is the MOST IMPORTANT endpoint in Module 1.
Logic:
  1. Validate partner_id uniqueness
  2. Validate all zone pincodes exist
  3. Call Module 2 → get_baseline()
  4. Call Module 2 → calculate_premium()
  5. Create rider record
  6. Create active policy (4-week cycle)
  7. Return full premium breakdown
"""

import logging
from datetime import date, timedelta
from typing import List, Optional

from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from db.connection import get_db
from models.rider import Rider, Zone
from models.policy import Policy
from config import TIER_CONFIG, settings
from integrations.module2_adapter import get_baseline, calculate_premium, BaselineResult

router = APIRouter(tags=["Registration"])
logger = logging.getLogger(__name__)

# ── Pydantic schemas ──────────────────────────────────────────────────────────

class KYCInput(BaseModel):
    type: str = Field(..., pattern="^(aadhaar|pan)$", description="'aadhaar' or 'pan'")
    value: str

    @field_validator("value")
    @classmethod
    def validate_kyc_value(cls, v: str, info) -> str:
        # We can't access type here without model_validator, so do basic sanity
        v = v.strip().upper()
        if not v:
            raise ValueError("KYC value cannot be empty.")
        return v

    @model_validator(mode="after")
    def validate_format(self):
        import re
        if self.type == "aadhaar":
            # Only store last 4 digits
            digits = re.sub(r"\D", "", self.value)
            if len(digits) not in (4, 12):
                raise ValueError("Aadhaar must be 12 digits (or last 4).")
            self.value = digits[-4:]
        elif self.type == "pan":
            if not re.match(r"^[A-Z]{5}[0-9]{4}[A-Z]$", self.value):
                raise ValueError("PAN must be in format ABCDE1234F.")
        return self


# ── Polygon schemas ───────────────────────────────────────────────────────────

class LatLngPoint(BaseModel):
    """A single latitude/longitude coordinate."""
    lat: float = Field(..., ge=-90.0, le=90.0, description="Latitude [-90, 90]")
    lng: float = Field(..., ge=-180.0, le=180.0, description="Longitude [-180, 180]")


class ZoneInput(BaseModel):
    """
    Zone entry with an optional polygon (list of lat/lng pairs).
    The zone_id must correspond to one of zone1_id / zone2_id / zone3_id.
    If polygon is provided it must have at least 3 points.
    """
    zone_id: int = Field(..., description="Must match one of zone1_id / zone2_id / zone3_id")
    polygon: List[LatLngPoint] = Field(
        ...,
        min_length=3,
        description="Polygon boundary — minimum 3 lat/lng points",
    )

    @field_validator("zone_id", mode="before")
    @classmethod
    def validate_zone_id(cls, v) -> int:
        if not isinstance(v, int) and not str(v).isdigit():
            raise ValueError("zone_id must be a positive integer.")
        return int(v)

    @field_validator("polygon")
    @classmethod
    def polygon_has_min_points(cls, v: List[LatLngPoint]) -> List[LatLngPoint]:
        if len(v) < 3:
            raise ValueError("Polygon must have at least 3 lat/lng points.")
        return v


class RegisterRiderRequest(BaseModel):
    partner_id: str = Field(..., min_length=3, max_length=100, description="Unique ID from Swiggy/Zomato")
    platform: str = Field(..., pattern="^(swiggy|zomato|dunzo|other)$")
    name: str = Field(..., min_length=2, max_length=200)
    phone: str = Field(..., description="Indian mobile number")
    kyc: KYCInput
    city: str = Field(..., min_length=2, max_length=100)
    zone1_id: int = Field(..., description="Primary zone (mandatory)")
    zone2_id: Optional[int] = Field(None, description="Secondary zone (optional)")
    zone3_id: Optional[int] = Field(None, description="Tertiary zone (optional)")
    tier: str = Field(..., pattern="^(kavach|suraksha|raksha)$")
    # Optional polygon data per zone.  When provided every entry must carry a
    # zone_id that matches one of zone1_id / zone2_id / zone3_id and a polygon
    # with at least 3 valid lat/lng points.
    zones: Optional[List[ZoneInput]] = Field(
        None,
        description="Optional polygon data for each zone (zone_id + polygon list).",
    )
    demo_income_override: Optional[float] = Field(
        None,
        ge=0.0,
        le=1_000_000.0,
        description=(
            "Demo/QA only: use this weekly income instead of Module 2 baseline for premium. "
            "Ignored when ALLOW_DEMO_INCOME_OVERRIDE is false or in production."
        ),
    )

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        import re
        cleaned = v.strip().replace(" ", "").replace("-", "")
        if not re.match(r"^(\+91|91|0)?[6-9]\d{9}$", cleaned):
            raise ValueError("Invalid Indian phone number.")
        return v

    @field_validator("partner_id")
    @classmethod
    def sanitize_partner_id(cls, v: str) -> str:
        v = v.strip()
        import re
        if not re.match(r"^[A-Za-z0-9\-_]+$", v):
            raise ValueError("partner_id may only contain letters, numbers, hyphens, underscores.")
        return v

    @field_validator("zone1_id", "zone2_id", "zone3_id", mode="before")
    @classmethod
    def validate_zone_id_format(cls, v):
        if v is None:
            return v
        if not isinstance(v, int) and not str(v).isdigit():
            raise ValueError("Zone ID must be a positive integer.")
        return int(v)

    @model_validator(mode="after")
    def zones_are_distinct(self):
        zone_ids = [z for z in [self.zone1_id, self.zone2_id, self.zone3_id] if z]
        if len(zone_ids) != len(set(zone_ids)):
            raise ValueError("Zone IDs must be distinct.")

        # Validate that every ZoneInput.zone_id is one of the declared zone slots.
        if self.zones:
            declared = set(zone_ids)
            seen: set[int] = set()
            for entry in self.zones:
                if entry.zone_id not in declared:
                    raise ValueError(
                        f"zones[].zone_id={entry.zone_id} does not match any of "
                        f"zone1_id / zone2_id / zone3_id ({sorted(declared)})."
                    )
                if entry.zone_id in seen:
                    raise ValueError(
                        f"Duplicate zone_id={entry.zone_id} in zones list."
                    )
                seen.add(entry.zone_id)

        return self


class PremiumBreakdownResponse(BaseModel):
    income: float
    tier_rate: float
    zone_risk: float
    seasonal_factor: float
    raw_premium: float
    floor_applied: bool
    cap_applied: bool
    final_premium: float


class RegisterRiderResponse(BaseModel):
    rider_id: int
    partner_id: str
    name: str
    tier: str
    policy_id: int
    weekly_premium: float
    weekly_payout_cap: float
    premium_breakdown: PremiumBreakdownResponse
    cycle_start_date: str
    cycle_end_date: str
    is_seasoning: bool
    message: str


# ── Route ─────────────────────────────────────────────────────────────────────

@router.post(
    "/register",
    response_model=RegisterRiderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new rider",
    description=(
        "Creates rider identity and active insurance policy. "
        "Calls Module 2 to compute baseline income and premium. "
        "Policy is locked for 4 weeks."
    ),
)
async def register_rider(
    request: RegisterRiderRequest,
    db: AsyncSession = Depends(get_db),
):
    # ── Step 1: Check partner_id uniqueness ───────────────────────────────────
    existing = await db.execute(
        select(Rider).where(Rider.partner_id == request.partner_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Rider with partner_id '{request.partner_id}' already exists.",
        )

    # ── Step 2: Check phone uniqueness ────────────────────────────────────────
    existing_phone = await db.execute(
        select(Rider).where(Rider.phone == request.phone)
    )
    if existing_phone.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Phone number is already registered.",
        )

    # ── Step 3: Validate zones exist in DB ────────────────────────────────────
    zone_ids = [
        z for z in [request.zone1_id, request.zone2_id, request.zone3_id]
        if z is not None
    ]
    zone_records = await db.execute(
        select(Zone).where(Zone.zone_id.in_(zone_ids))
    )
    found_zones: dict[int, Zone] = {z.zone_id: z for z in zone_records.scalars().all()}

    missing = [p for p in zone_ids if p not in found_zones]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown zone IDs: {missing}. Use GET /zones?city=... to list valid zones.",
        )

    # Validate city consistency (zone must belong to requested city)
    city_mismatch = [
        p for p, z in found_zones.items()
        if z.city.strip().lower() != request.city.strip().lower()
    ]
    if city_mismatch:
        mismatch_details = {p: found_zones[p].city for p in city_mismatch}
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Zone IDs {city_mismatch} don't belong to city '{request.city}'. "
                   f"Actual cities: {mismatch_details}",
        )

    # ── Step 3b: Persist polygon data for zones (if provided) ─────────────────
    # For each ZoneInput entry, serialise the polygon and write it back to the
    # zone record.  This is additive — it never removes existing zone_id logic.
    if request.zones:
        for zone_entry in request.zones:
            zone_rec = found_zones.get(zone_entry.zone_id)
            # zone_rec is guaranteed non-None at this point (checked above)
            polygon_data = [
                {"lat": point.lat, "lng": point.lng}
                for point in zone_entry.polygon
            ]
            zone_rec.polygon = polygon_data  # type: ignore[assignment]
            db.add(zone_rec)

    # ── Step 4: Call Module 2 → get_baseline ─────────────────────────────────
    # New riders are always in seasoning (no historical data)
    try:
        baseline = await get_baseline(
            rider_id=request.partner_id,  # Use partner_id as ref before rider_id exists
            city=request.city,
            is_seasoning=True,
        )
    except Exception as e:
        logger.error(f"Module 2 get_baseline failed during registration: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to fetch baseline data. Please try again.",
        )

    if request.demo_income_override is not None:
        if settings.ENVIRONMENT == "production" or not settings.ALLOW_DEMO_INCOME_OVERRIDE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="demo_income_override is not enabled for this environment.",
            )
        hours = (
            float(baseline.hours)
            if baseline.hours and float(baseline.hours) > 0
            else 40.0
        )
        inc = float(request.demo_income_override)
        baseline = BaselineResult(
            income=inc,
            hours=hours,
            hourly_rate=round(inc / hours, 2) if hours > 0 else 0.0,
            is_provisional=True,
        )
        logger.info(
            "Registration demo_income_override applied: income=%s (partner_id=%s)",
            inc,
            request.partner_id,
        )

    # ── Step 5: Call Module 2 → calculate_premium ────────────────────────────
    try:
        premium_result = await calculate_premium(
            income=baseline.income,
            tier=request.tier,
            zones=zone_ids,
        )
    except Exception as e:
        logger.error(f"Module 2 calculate_premium failed during registration: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to calculate premium. Please try again.",
        )

    # ── Step 6: Create rider record ───────────────────────────────────────────
    rider = Rider(
        partner_id=request.partner_id,
        platform=request.platform,
        name=request.name.strip(),
        phone=request.phone,
        aadhaar_last4=request.kyc.value if request.kyc.type == "aadhaar" else None,
        pan=request.kyc.value if request.kyc.type == "pan" else None,
        city=request.city.strip().title(),
        zone1_id=request.zone1_id,
        zone2_id=request.zone2_id,
        zone3_id=request.zone3_id,
        tier=request.tier,
        baseline_weekly_income=baseline.income,
        baseline_weekly_hours=baseline.hours,
        is_seasoning=True,         # Always starts in seasoning
        trust_score=50.00,         # Default trust score
    )
    db.add(rider)
    await db.flush()  # Gets rider.id without full commit

    # ── Step 7: Create policy (4-week cycle) ──────────────────────────────────
    tier_cfg = TIER_CONFIG[request.tier]
    cycle_start = date.today()
    cycle_end = cycle_start + timedelta(days=28)

    bd = premium_result.breakdown
    breakdown_json = {
        "income":           bd.income,
        "tier_rate":        bd.tier_rate,
        "zone_risk":        bd.zone_risk,
        "seasonal_factor":  bd.seasonal_factor,
        "raw_premium":      bd.raw_premium,
        "floor_applied":    bd.floor_applied,
        "cap_applied":      bd.cap_applied,
        "final_premium":    bd.final_premium,
    }

    policy = Policy(
        rider_id=rider.id,
        tier=request.tier,
        weekly_premium=premium_result.weekly_premium,
        premium_breakdown=breakdown_json,
        weekly_payout_cap=tier_cfg["weekly_payout_cap"],
        coverage_type=tier_cfg["coverage_type"],
        status="active",
        cycle_start_date=cycle_start,
        cycle_end_date=cycle_end,
    )
    db.add(policy)

    # Commit both rider and policy atomically
    try:
        await db.commit()
        await db.refresh(rider)
        await db.refresh(policy)
    except IntegrityError as e:
        await db.rollback()
        error_msg = str(e.orig).lower() if e.orig else str(e)
        if "partner_id" in error_msg or "unique" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Rider with this partner_id or phone already exists.",
            )
        logger.error(f"IntegrityError during registration: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Registration failed due to a data conflict: {str(e.orig)}",
        )

    logger.info(f"Rider registered: {rider.id} | partner_id={rider.partner_id} | tier={rider.tier}")

    return RegisterRiderResponse(
        rider_id=rider.id,
        partner_id=rider.partner_id,
        name=rider.name,
        tier=rider.tier,
        policy_id=policy.id,
        weekly_premium=float(policy.weekly_premium),
        weekly_payout_cap=float(policy.weekly_payout_cap),
        premium_breakdown=PremiumBreakdownResponse(**breakdown_json),
        cycle_start_date=policy.cycle_start_date.isoformat(),
        cycle_end_date=policy.cycle_end_date.isoformat(),
        is_seasoning=rider.is_seasoning,
        message=(
            f"Registration successful. Your '{request.tier}' policy is active for 4 weeks. "
            f"Weekly premium: ₹{policy.weekly_premium}."
        ),
    )
