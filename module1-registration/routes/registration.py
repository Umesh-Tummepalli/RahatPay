"""
routes/registration.py
----------------------
POST /register - rider registration endpoint.
"""

import logging
import re
from datetime import date, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from db.connection import get_db
from models.policy import Policy
from models.rider import Rider, Zone
from services.subscription_state import (
    build_premium_quote,
    ensure_subscription_state,
    get_city_baseline,
    get_rider_zone_map,
)

router = APIRouter(tags=["Registration"])
logger = logging.getLogger(__name__)


class KYCInput(BaseModel):
    type: str = Field(..., pattern="^(aadhaar|pan)$", description="'aadhaar' or 'pan'")
    value: str

    @field_validator("value")
    @classmethod
    def validate_kyc_value(cls, value: str) -> str:
        cleaned = value.strip().upper()
        if not cleaned:
            raise ValueError("KYC value cannot be empty.")
        return cleaned

    @model_validator(mode="after")
    def validate_format(self):
        if self.type == "aadhaar":
            digits = re.sub(r"\D", "", self.value)
            if len(digits) not in (4, 12):
                raise ValueError("Aadhaar must be 12 digits (or last 4).")
            self.value = digits[-4:]
        elif self.type == "pan":
            if not re.match(r"^[A-Z]{5}[0-9]{4}[A-Z]$", self.value):
                raise ValueError("PAN must be in format ABCDE1234F.")
        return self


class LatLngPoint(BaseModel):
    lat: float = Field(..., ge=-90.0, le=90.0, description="Latitude [-90, 90]")
    lng: float = Field(..., ge=-180.0, le=180.0, description="Longitude [-180, 180]")


class ZoneInput(BaseModel):
    zone_id: int = Field(..., description="Must match one of zone1_id / zone2_id / zone3_id")
    polygon: List[LatLngPoint] = Field(
        ...,
        min_length=3,
        description="Polygon boundary - minimum 3 lat/lng points",
    )

    @field_validator("zone_id", mode="before")
    @classmethod
    def validate_zone_id(cls, value) -> int:
        if not isinstance(value, int) and not str(value).isdigit():
            raise ValueError("zone_id must be a positive integer.")
        return int(value)

    @field_validator("polygon")
    @classmethod
    def polygon_has_min_points(cls, value: List[LatLngPoint]) -> List[LatLngPoint]:
        if len(value) < 3:
            raise ValueError("Polygon must have at least 3 lat/lng points.")
        return value


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
    zones: Optional[List[ZoneInput]] = Field(
        None,
        description="Optional polygon data for each zone (zone_id + polygon list).",
    )

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        cleaned = value.strip().replace(" ", "").replace("-", "")
        if not re.match(r"^(\+91|91|0)?[6-9]\d{9}$", cleaned):
            raise ValueError("Invalid Indian phone number.")
        return value

    @field_validator("partner_id")
    @classmethod
    def sanitize_partner_id(cls, value: str) -> str:
        cleaned = value.strip()
        if not re.match(r"^[A-Za-z0-9\-_]+$", cleaned):
            raise ValueError("partner_id may only contain letters, numbers, hyphens, underscores.")
        return cleaned

    @field_validator("zone1_id", "zone2_id", "zone3_id", mode="before")
    @classmethod
    def validate_zone_id_format(cls, value):
        if value is None:
            return value
        if not isinstance(value, int) and not str(value).isdigit():
            raise ValueError("Zone ID must be a positive integer.")
        return int(value)

    @model_validator(mode="after")
    def zones_are_distinct(self):
        zone_ids = [zone_id for zone_id in [self.zone1_id, self.zone2_id, self.zone3_id] if zone_id]
        if len(zone_ids) != len(set(zone_ids)):
            raise ValueError("Zone IDs must be distinct.")

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
                    raise ValueError(f"Duplicate zone_id={entry.zone_id} in zones list.")
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


@router.post(
    "/register",
    response_model=RegisterRiderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new rider",
    description=(
        "Creates rider identity and an active paid policy. "
        "Used by the legacy registration flow."
    ),
)
async def register_rider(
    request: RegisterRiderRequest,
    db: AsyncSession = Depends(get_db),
):
    existing = await db.execute(select(Rider).where(Rider.partner_id == request.partner_id))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Rider with partner_id '{request.partner_id}' already exists.",
        )

    existing_phone = await db.execute(select(Rider).where(Rider.phone == request.phone))
    if existing_phone.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Phone number is already registered.",
        )

    zone_ids = [zone_id for zone_id in [request.zone1_id, request.zone2_id, request.zone3_id] if zone_id is not None]
    zone_records = await db.execute(select(Zone).where(Zone.zone_id.in_(zone_ids)))
    found_zones: dict[int, Zone] = {zone.zone_id: zone for zone in zone_records.scalars().all()}

    missing = [zone_id for zone_id in zone_ids if zone_id not in found_zones]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown zone IDs: {missing}. Use GET /zones?city=... to list valid zones.",
        )

    city_mismatch = [
        zone_id
        for zone_id, zone in found_zones.items()
        if zone.city.strip().lower() != request.city.strip().lower()
    ]
    if city_mismatch:
        mismatch_details = {zone_id: found_zones[zone_id].city for zone_id in city_mismatch}
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Zone IDs {city_mismatch} don't belong to city '{request.city}'. "
                f"Actual cities: {mismatch_details}"
            ),
        )

    if request.zones:
        for zone_entry in request.zones:
            zone_record = found_zones.get(zone_entry.zone_id)
            polygon_data = [{"lat": point.lat, "lng": point.lng} for point in zone_entry.polygon]
            zone_record.polygon = polygon_data  # type: ignore[assignment]
            db.add(zone_record)

    baseline = get_city_baseline(request.city)
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
        is_seasoning=True,
        trust_score=50.00,
    )
    db.add(rider)
    await db.flush()

    zone_map = await get_rider_zone_map(db, rider)
    quote = build_premium_quote(rider, request.tier, zone_map)

    cycle_start = date.today()
    cycle_end = cycle_start + timedelta(days=28)
    breakdown_json = quote["premium_breakdown"]

    policy = Policy(
        rider_id=rider.id,
        tier=request.tier,
        weekly_premium=quote["weekly_premium"],
        premium_breakdown=breakdown_json,
        weekly_payout_cap=quote["weekly_payout_cap"],
        coverage_type=quote["coverage_type"],
        status="active",
        cycle_start_date=cycle_start,
        cycle_end_date=cycle_end,
    )
    db.add(policy)
    await ensure_subscription_state(db, rider, active_policy=policy)

    try:
        await db.commit()
        await db.refresh(rider)
        await db.refresh(policy)
    except IntegrityError as exc:
        await db.rollback()
        error_msg = str(exc.orig).lower() if exc.orig else str(exc)
        if "partner_id" in error_msg or "unique" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Rider with this partner_id or phone already exists.",
            )
        logger.error("IntegrityError during registration: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Registration failed due to a data conflict: {str(exc.orig)}",
        )

    logger.info("Rider registered: %s | partner_id=%s | tier=%s", rider.id, rider.partner_id, rider.tier)

    return RegisterRiderResponse(
        rider_id=rider.id,
        partner_id=rider.partner_id,
        name=rider.name,
        tier=rider.tier,
        policy_id=policy.id,
        weekly_premium=float(policy.weekly_premium),
        weekly_payout_cap=float(policy.weekly_payout_cap),
        premium_breakdown=PremiumBreakdownResponse(
            income=float(breakdown_json["income"]),
            tier_rate=float(breakdown_json["tier_rate"]),
            zone_risk=float(breakdown_json["zone_risk"]),
            seasonal_factor=float(breakdown_json["seasonal_factor"]),
            raw_premium=float(breakdown_json["raw_premium"]),
            floor_applied=bool(breakdown_json["floor_applied"]),
            cap_applied=bool(breakdown_json["cap_applied"]),
            final_premium=float(breakdown_json["final_premium"]),
        ),
        cycle_start_date=policy.cycle_start_date.isoformat(),
        cycle_end_date=policy.cycle_end_date.isoformat(),
        is_seasoning=rider.is_seasoning,
        message=(
            f"Registration successful. Your '{request.tier}' policy is active for 4 weeks. "
            f"Weekly premium: Rs. {float(policy.weekly_premium):.2f}."
        ),
    )


@router.get(
    "/rider/{identifier}/income-profile",
    summary="Get 15-day income history for a rider",
)
async def get_rider_income_profile(
    identifier: str,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Rider).where((Rider.partner_id == identifier) | (Rider.phone == identifier))
    result = await db.execute(stmt)
    rider = result.scalar_one_or_none()

    if not rider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rider not found.",
        )

    return {
        "rider_id": rider.id,
        "partner_id": rider.partner_id,
        "name": rider.name,
        "city": rider.city,
        "baseline_weekly_income": float(rider.baseline_weekly_income) if rider.baseline_weekly_income else 0,
        "daily_income_history": rider.daily_income_history or [],
        "zone_ids": [zone_id for zone_id in [rider.zone1_id, rider.zone2_id, rider.zone3_id] if zone_id],
    }
