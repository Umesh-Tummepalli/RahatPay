"""
routes/policy.py
----------------
Policy and rider management endpoints:

  GET  /rider/{id}/dashboard         — Active coverage + premium breakdown
  GET  /rider/{id}/payouts           — Payout / claim history
  GET  /zones                        — Zones by city
  GET  /tiers                        — Static tier definitions
  POST /rider/{id}/renew             — Renew policy at cycle end
  POST /rider/{id}/change-tier       — Tier change (only at cycle boundary)
"""

import logging
from datetime import date, datetime, timedelta
from typing import Optional, List, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload

from db.connection import get_db
from models.rider import Rider, Zone
from models.policy import Policy, Claim, Payout
from config import TIER_CONFIG, settings
from services.subscription_state import (
    build_premium_quote,
    build_premium_quotes,
    ensure_subscription_state,
    get_active_paid_policy,
    get_rider_baseline,
    get_rider_zone_map,
    notification_is_unread,
    serialize_subscription_state,
    sync_subscription_phase,
    utcnow,
)

router = APIRouter(tags=["Policy & Dashboard"])
logger = logging.getLogger(__name__)


# ── Helper ────────────────────────────────────────────────────────────────────

async def _get_rider_or_404(rider_id: int, db: AsyncSession) -> Rider:
    """Fetch rider by integer ID; raise 404 if not found."""
    stmt = (
        select(Rider)
        .where(Rider.id == rider_id)
        .options(
            selectinload(Rider.zone1),
            selectinload(Rider.zone2),
            selectinload(Rider.zone3),
            selectinload(Rider.policies),
        )
    )
    result = await db.execute(stmt)
    rider = result.scalar_one_or_none()
    if not rider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rider '{rider_id}' not found.",
        )
    return rider


async def _get_active_policy_or_404(rider: Rider, db: AsyncSession) -> Policy:
    """Return the current active policy for a rider; raise 404 if none."""
    stmt = select(Policy).where(
        and_(
            Policy.rider_id == rider.id,
            Policy.status == "active",
            Policy.cycle_end_date >= date.today(),
        )
    )
    result = await db.execute(stmt)
    policy = result.scalar_one_or_none()
    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No active policy found for rider '{rider.id}'. "
                   "Please renew or complete registration.",
        )
    return policy


# ── Dashboard ─────────────────────────────────────────────────────────────────

class ZoneDetail(BaseModel):
    zone_id: int
    area_name: str
    city: str
    polygon: List[Any]
    risk_multiplier: float
    is_active: bool
    registration_cap: int


class PremiumBreakdownDetail(BaseModel):
    income: float
    tier_rate: float
    zone_risk: float
    seasonal_factor: float
    raw_premium: float
    floor_applied: bool
    cap_applied: bool
    final_premium: float


class DashboardResponse(BaseModel):
    rider_id: int
    name: str
    tier: str
    platform: str
    city: str
    policy_id: int
    policy_status: str
    weekly_premium: float
    weekly_payout_cap: float
    premium_breakdown: PremiumBreakdownDetail
    zones: list[ZoneDetail]
    baseline_weekly_income: Optional[float]
    baseline_weekly_hours: Optional[float]
    baseline_hourly_rate: Optional[float]
    is_seasoning: bool
    already_paid_this_week: float
    remaining_headroom: float
    cycle_start_date: str
    cycle_end_date: str
    days_remaining: int
    trust_score: float


@router.get(
    "/rider/{rider_id}/dashboard",
    response_model=DashboardResponse,
    summary="Rider dashboard",
    description="Returns full policy, premium breakdown, zone details, and payout headroom.",
)
async def get_dashboard(
    rider_id: int,
    db: AsyncSession = Depends(get_db),
):
    rider = await _get_rider_or_404(rider_id, db)
    policy = await _get_active_policy_or_404(rider, db)

    # Sum of paid claims this week
    week_start = date.today() - timedelta(days=date.today().weekday())
    paid_this_week_result = await db.execute(
        select(func.coalesce(func.sum(Claim.final_payout), 0)).where(
            and_(
                Claim.rider_id == rider.id,
                Claim.status == "paid",
                Claim.created_at >= week_start,
            )
        )
    )
    already_paid = float(paid_this_week_result.scalar_one())
    remaining_headroom = max(0.0, float(policy.weekly_payout_cap) - already_paid)

    # Build zone details
    zones = []
    for zone_obj in [rider.zone1, rider.zone2, rider.zone3]:
        if zone_obj:
            zones.append(ZoneDetail(
                zone_id=zone_obj.zone_id,
                area_name=zone_obj.area_name,
                city=zone_obj.city,
                polygon=zone_obj.polygon,
                risk_multiplier=float(zone_obj.risk_multiplier),
                is_active=zone_obj.is_active,
                registration_cap=zone_obj.registration_cap,
            ))

    # Premium breakdown from stored policy
    bd = policy.premium_breakdown or {}
    breakdown = PremiumBreakdownDetail(
        income=bd.get("income", 0),
        tier_rate=bd.get("tier_rate", 0),
        zone_risk=bd.get("zone_risk", 1.0),
        seasonal_factor=bd.get("seasonal_factor", 1.0),
        raw_premium=bd.get("raw_premium", float(policy.weekly_premium)),
        floor_applied=bd.get("floor_applied", False),
        cap_applied=bd.get("cap_applied", False),
        final_premium=bd.get("final_premium", float(policy.weekly_premium)),
    )

    return DashboardResponse(
        rider_id=rider.id,
        name=rider.name,
        tier=rider.tier,
        platform=rider.platform,
        city=rider.city,
        policy_id=policy.id,
        policy_status=policy.status,
        weekly_premium=float(policy.weekly_premium),
        weekly_payout_cap=float(policy.weekly_payout_cap),
        premium_breakdown=breakdown,
        zones=zones,
        baseline_weekly_income=float(rider.baseline_weekly_income) if rider.baseline_weekly_income else None,
        baseline_weekly_hours=float(rider.baseline_weekly_hours) if rider.baseline_weekly_hours else None,
        baseline_hourly_rate=rider.baseline_hourly_rate,
        is_seasoning=rider.is_seasoning,
        already_paid_this_week=already_paid,
        remaining_headroom=remaining_headroom,
        cycle_start_date=policy.cycle_start_date.isoformat(),
        cycle_end_date=policy.cycle_end_date.isoformat(),
        days_remaining=policy.days_remaining,
        trust_score=float(rider.trust_score),
    )


# ── Payout History ────────────────────────────────────────────────────────────

class GateResultDetail(BaseModel):
    zone_overlap: Optional[bool] = None
    shift_window: Optional[bool] = None
    platform_inactivity: Optional[bool] = None
    location_verified: Optional[bool] = None


class ClaimHistoryItem(BaseModel):
    claim_id: int
    disruption_event_id: int
    event_type: Optional[str] = None
    severity: Optional[str] = None
    gate_results: dict
    is_eligible: bool
    ineligibility_reason: Optional[str]
    lost_hours: Optional[float]
    hourly_rate: Optional[float]
    severity_rate: Optional[float]
    calculated_payout: Optional[float]
    final_payout: Optional[float]
    status: str
    created_at: str


class PayoutHistoryResponse(BaseModel):
    rider_id: int
    total_paid: float
    total_claims: int
    approved_claims: int
    rejected_claims: int
    claims: list[ClaimHistoryItem]


@router.get(
    "/rider/{rider_id}/payouts",
    response_model=PayoutHistoryResponse,
    summary="Rider payout history",
    description="Returns all claims with gate results, payout amounts, and status.",
)
async def get_payout_history(
    rider_id: int,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    # Verify rider exists
    rider_result = await db.execute(select(Rider).where(Rider.id == rider_id))
    rider = rider_result.scalar_one_or_none()
    if not rider:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rider not found.")

    # Fetch claims with disruption event data
    from models.policy import DisruptionEvent
    stmt = (
        select(Claim, DisruptionEvent)
        .outerjoin(DisruptionEvent, Claim.disruption_event_id == DisruptionEvent.id)
        .where(Claim.rider_id == rider_id)
        .order_by(Claim.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    results = await db.execute(stmt)
    rows = results.all()

    # Aggregate stats
    stats_stmt = select(
        func.count(Claim.id).label("total"),
        func.sum(func.case((Claim.status == "paid", 1), else_=0)).label("approved"),
        func.sum(func.case((Claim.status == "rejected", 1), else_=0)).label("rejected"),
        func.coalesce(
            func.sum(func.case((Claim.status == "paid", Claim.final_payout), else_=0)), 0
        ).label("total_paid"),
    ).where(Claim.rider_id == rider_id)
    stats_result = await db.execute(stats_stmt)
    stats = stats_result.one()

    claims = []
    for claim, event in rows:
        claims.append(ClaimHistoryItem(
            claim_id=claim.id,
            disruption_event_id=claim.disruption_event_id,
            event_type=event.event_type if event else None,
            severity=event.severity if event else None,
            gate_results=claim.gate_results or {},
            is_eligible=claim.is_eligible,
            ineligibility_reason=claim.ineligibility_reason,
            lost_hours=float(claim.lost_hours) if claim.lost_hours else None,
            hourly_rate=float(claim.hourly_rate) if claim.hourly_rate else None,
            severity_rate=float(claim.severity_rate) if claim.severity_rate else None,
            calculated_payout=float(claim.calculated_payout) if claim.calculated_payout else None,
            final_payout=float(claim.final_payout) if claim.final_payout else None,
            status=claim.status,
            created_at=claim.created_at.isoformat() if claim.created_at else "",
        ))

    return PayoutHistoryResponse(
        rider_id=rider_id,
        total_paid=float(stats.total_paid),
        total_claims=int(stats.total or 0),
        approved_claims=int(stats.approved or 0),
        rejected_claims=int(stats.rejected or 0),
        claims=claims,
    )


# ── Zones ─────────────────────────────────────────────────────────────────────

class ZoneResponse(BaseModel):
    zone_id: int
    city: str
    area_name: str
    polygon: List[Any]
    risk_multiplier: float
    is_active: bool
    registration_cap: int


@router.get(
    "/zones",
    response_model=list[ZoneResponse],
    summary="List zones",
    description="Returns all delivery zones. Filter by city.",
)
async def get_zones(
    city: Optional[str] = Query(None, description="Filter by city name, e.g. Chennai"),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Zone)
    if city:
        stmt = stmt.where(Zone.city.ilike(f"%{city.strip()}%"))
    stmt = stmt.order_by(Zone.city, Zone.area_name)

    result = await db.execute(stmt)
    zones = result.scalars().all()

    if not zones:
        detail = f"No zones found for city '{city}'." if city else "No zones found."
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)

    return [ZoneResponse(**z.to_dict()) for z in zones]


# ── Tiers ─────────────────────────────────────────────────────────────────────

class TierResponse(BaseModel):
    name: str
    display_name: str
    tier_rate: float
    tier_rate_percent: str
    weekly_payout_cap: float
    coverage_type: str
    coverage_triggers: list[str]
    description: str
    premium_floor: float
    premium_cap_percent: str


@router.get(
    "/tiers",
    response_model=list[TierResponse],
    summary="List available tiers",
    description="Returns all insurance tiers with rates, caps, and coverage details.",
)
async def get_tiers():
    tiers = []
    for tier_key, cfg in TIER_CONFIG.items():
        tiers.append(TierResponse(
            name=cfg["name"],
            display_name=cfg["display_name"],
            tier_rate=cfg["tier_rate"],
            tier_rate_percent=f"{cfg['tier_rate'] * 100:.1f}%",
            weekly_payout_cap=cfg["weekly_payout_cap"],
            coverage_type=cfg["coverage_type"],
            coverage_triggers=cfg["coverage_triggers"],
            description=cfg["description"],
            premium_floor=settings.PREMIUM_FLOOR,
            premium_cap_percent=f"{settings.PREMIUM_CAP_PERCENT * 100:.1f}%",
        ))
    return tiers


# ── Tier Change ───────────────────────────────────────────────────────────────

class TierChangeRequest(BaseModel):
    new_tier: str

    @classmethod
    def validate_tier(cls, v: str) -> str:
        if v not in TIER_CONFIG:
            raise ValueError(f"Invalid tier. Must be one of: {list(TIER_CONFIG.keys())}")
        return v


class TierChangeResponse(BaseModel):
    rider_id: int
    old_tier: str
    new_tier: str
    effective_from: str
    message: str


@router.post(
    "/rider/{rider_id}/change-tier",
    response_model=TierChangeResponse,
    summary="Change rider tier",
    description="Tier changes are only allowed at cycle boundary (when current policy expires).",
)
async def change_tier(
    rider_id: int,
    request: TierChangeRequest,
    db: AsyncSession = Depends(get_db),
):
    if request.new_tier not in TIER_CONFIG:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid tier '{request.new_tier}'. Must be one of: {list(TIER_CONFIG.keys())}",
        )

    rider = await _get_rider_or_404(rider_id, db)

    if rider.tier == request.new_tier:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Rider is already on the '{request.new_tier}' tier.",
        )

    # Check if active policy is still mid-cycle
    active_policy_stmt = select(Policy).where(
        and_(
            Policy.rider_id == rider.id,
            Policy.status == "active",
            Policy.cycle_end_date > date.today(),
        )
    )
    result = await db.execute(active_policy_stmt)
    active_policy = result.scalar_one_or_none()

    if active_policy:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Cannot change tier mid-cycle. Current policy expires on "
                f"{active_policy.cycle_end_date.isoformat()}. "
                "Tier change will take effect from the next cycle."
            ),
        )

    # Safe to change — no active policy
    old_tier = rider.tier
    rider.tier = request.new_tier
    await db.commit()
    await db.refresh(rider)

    logger.info(f"Rider {rider_id} tier changed: {old_tier} → {request.new_tier}")

    return TierChangeResponse(
        rider_id=rider_id,
        old_tier=old_tier,
        new_tier=request.new_tier,
        effective_from=date.today().isoformat(),
        message=(
            f"Tier changed from '{old_tier}' to '{request.new_tier}'. "
            "Your new premium will apply from the next policy cycle."
        ),
    )


# ── Premium Simulation ────────────────────────────────────────────────────────

class PremiumSimulationRequest(BaseModel):
    income: float
    tier: str
    zones: list[int]
    month: Optional[int] = None

class PremiumSimulationResponse(BaseModel):
    weekly_premium: float
    breakdown: dict

@router.post(
    "/premium/simulate",
    response_model=PremiumSimulationResponse,
    summary="Simulate Premium Calculation",
    description="Simulate the premium calculation for a rider without registering them. Used by the simulation dashboard.",
)
async def simulate_premium(request: PremiumSimulationRequest):
    """Calculate premium locally without calling Module 2."""
    if request.tier not in TIER_CONFIG:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid tier '{request.tier}'. Must be one of: {list(TIER_CONFIG.keys())}",
        )

    # Premium calculation constants (same as Module 2)
    PREMIUM_FLOOR = 15.0
    PREMIUM_CAP_PERCENT = 0.035
    
    _ZONE_RISK = {
        1: 1.20, 2: 1.15, 3: 1.10, 4: 1.05, 5: 1.00, 6: 0.95,
        7: 1.25, 8: 1.10, 9: 1.30, 10: 1.20, 11: 1.15, 12: 1.35,
        13: 1.00, 14: 1.05, 15: 1.10, 16: 1.08, 17: 1.25, 18: 1.15,
        19: 1.40, 20: 1.35,
    }
    
    _SEASONAL = {
        1: 0.90, 2: 0.88, 3: 0.92, 4: 0.95, 5: 1.00, 6: 1.20,
        7: 1.25, 8: 1.25, 9: 1.15, 10: 1.05, 11: 0.95, 12: 0.90,
    }

    # Get tier rate
    tier_rate = TIER_CONFIG[request.tier]["tier_rate"]

    # Calculate average zone risk
    risks = [_ZONE_RISK.get(z, 1.0) for z in request.zones if z]
    zone_risk = round(sum(risks) / len(risks), 4) if risks else 1.0

    # Get seasonal factor
    current_month = request.month or datetime.now().month
    seasonal_factor = _SEASONAL.get(current_month, 1.0)

    # Core formula
    raw_premium = request.income * tier_rate * zone_risk * seasonal_factor

    # Apply floor and cap
    raw_premium_floored = max(raw_premium, PREMIUM_FLOOR)
    floor_applied = raw_premium < PREMIUM_FLOOR

    cap_amount = request.income * PREMIUM_CAP_PERCENT
    cap_applied = (request.income > 0) and (raw_premium_floored > cap_amount)

    final_premium = min(raw_premium_floored, cap_amount) if request.income > 0 else 0.0
    final_premium = round(final_premium, 2)

    breakdown_json = {
        "income": request.income,
        "tier_rate": tier_rate,
        "zone_risk": zone_risk,
        "seasonal_factor": seasonal_factor,
        "raw_premium": round(raw_premium, 2),
        "floor_applied": floor_applied,
        "cap_applied": cap_applied,
        "final_premium": final_premium,
    }

    return PremiumSimulationResponse(
        weekly_premium=final_premium,
        breakdown=breakdown_json,
    )


# ── Policy Renewal ────────────────────────────────────────────────────────────

class RenewPolicyResponse(BaseModel):
    rider_id: int
    policy_id: int
    tier: str
    weekly_premium: float
    weekly_payout_cap: float
    premium_breakdown: dict
    cycle_start_date: str
    cycle_end_date: str
    message: str


@router.post(
    "/rider/{rider_id}/renew",
    response_model=RenewPolicyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Renew policy",
    description=(
        "Creates a new 4-week policy cycle for the rider. "
        "Only callable when previous cycle has ended or expired. "
        "Also re-calculates premium with updated baseline."
    ),
)
async def renew_policy(
    rider_id: int,
    db: AsyncSession = Depends(get_db),
):
    rider = await _get_rider_or_404(rider_id, db)

    # Block renewal if active policy exists
    active_stmt = select(Policy).where(
        and_(
            Policy.rider_id == rider.id,
            Policy.status == "active",
            Policy.cycle_end_date >= date.today(),
        )
    )
    result = await db.execute(active_stmt)
    existing_active = result.scalar_one_or_none()

    if existing_active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"An active policy already exists. "
                f"Renewal available from {existing_active.cycle_end_date.isoformat()}."
            ),
        )

    # Expire any stale 'active' policies (cycle_end_date in the past)
    stale_stmt = select(Policy).where(
        and_(
            Policy.rider_id == rider.id,
            Policy.status == "active",
            Policy.cycle_end_date < date.today(),
        )
    )
    stale_result = await db.execute(stale_stmt)
    for stale in stale_result.scalars().all():
        stale.status = "expired"

    weeks_since_join = (utcnow() - rider.created_at.replace(tzinfo=utcnow().tzinfo)).days / 7
    new_is_seasoning = weeks_since_join < 4

    baseline = get_rider_baseline(rider, is_seasoning=new_is_seasoning)

    # Update rider baseline and seasoning status
    rider.baseline_weekly_income = baseline.income
    rider.baseline_weekly_hours = baseline.hours
    rider.is_seasoning = new_is_seasoning

    zone_map = await get_rider_zone_map(db, rider)
    quote = build_premium_quote(rider, rider.tier, zone_map)

    # Create new policy
    cycle_start = date.today()
    cycle_end = cycle_start + timedelta(days=28)
    breakdown_json = quote["premium_breakdown"]

    new_policy = Policy(
        rider_id=rider.id,
        tier=rider.tier,
        weekly_premium=quote["weekly_premium"],
        premium_breakdown=breakdown_json,
        weekly_payout_cap=quote["weekly_payout_cap"],
        coverage_type=quote["coverage_type"],
        status="active",
        cycle_start_date=cycle_start,
        cycle_end_date=cycle_end,
    )
    db.add(new_policy)
    await ensure_subscription_state(db, rider, active_policy=new_policy)
    await db.commit()
    await db.refresh(new_policy)
    await db.refresh(rider)

    logger.info(f"Policy renewed for rider {rider_id}. New policy: {new_policy.id}")

    return RenewPolicyResponse(
        rider_id=rider_id,
        policy_id=new_policy.id,
        tier=rider.tier,
        weekly_premium=float(new_policy.weekly_premium),
        weekly_payout_cap=float(new_policy.weekly_payout_cap),
        premium_breakdown=breakdown_json,
        cycle_start_date=cycle_start.isoformat(),
        cycle_end_date=cycle_end.isoformat(),
        message=(
            f"Policy renewed successfully. "
            f"New cycle: {cycle_start} → {cycle_end}. "
            f"Weekly premium: ₹{new_policy.weekly_premium}."
        ),
    )
