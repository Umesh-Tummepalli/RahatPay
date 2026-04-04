"""
routes/admin.py
---------------
Admin API Layer for worker management, fraud monitoring, and financial overview.
"""

from typing import Optional, List, Any
import logging
import random
import httpx
from datetime import date, datetime, timedelta

from fastapi import APIRouter, HTTPException, status, Depends, Header, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload

from db.connection import get_db
from models.rider import Rider, Zone
from models.policy import Policy, Claim, Payout, DisruptionEvent
from config import TIER_CONFIG, settings
from services.subscription_state import (
    build_premium_quotes,
    ensure_subscription_state,
    get_active_paid_policy,
    get_trial_expires_at,
    has_seeded_history,
    isoformat,
    notification_is_unread,
    quote_summary_from_quotes,
    serialize_subscription_state,
    sync_subscription_phase,
    utcnow,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin Control Panel"])

# ── Authentication ────────────────────────────────────────────────────────────

async def require_admin(authorization: Optional[str] = Header(None)):
    """Mock JWT role-based access for 'admin'."""
    if not authorization or authorization != "Bearer admin_token":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Admin access required.",
        )
    return True


async def _serialize_worker_summary(db: AsyncSession, worker: Rider) -> dict:
    active_policy = await get_active_paid_policy(db, worker.id)
    subscription_state = await ensure_subscription_state(db, worker, active_policy=active_policy)
    sync_subscription_phase(subscription_state, active_policy=active_policy)

    payload = worker.to_dict()
    payload.update(
        {
            "trial_phase": subscription_state.phase,
            "trial_started_at": isoformat(subscription_state.trial_started_at),
            "trial_completed_at": isoformat(subscription_state.trial_completed_at),
            "has_seeded_history": has_seeded_history(worker),
            "last_seeded_at": isoformat(subscription_state.last_seeded_at),
            "last_quotes_at": isoformat(subscription_state.last_quotes_at),
            "quotes_ready": bool(subscription_state.premium_quotes),
            "quote_summary": quote_summary_from_quotes(subscription_state.premium_quotes),
            "notification_unread": notification_is_unread(subscription_state),
        }
    )
    return payload


async def _generate_seeded_history(
    db: AsyncSession,
    rider: Rider,
    days: int,
    base_hourly_rate: float,
    avg_hours_per_day: float,
) -> dict:
    active_policy = await get_active_paid_policy(db, rider.id)
    subscription_state = await ensure_subscription_state(db, rider, active_policy=active_policy)
    previous_phase = subscription_state.phase
    previous_had_history = has_seeded_history(rider)
    current_time = utcnow()

    daily_history = []
    total_income = 0.0
    total_hours = 0.0

    for day_offset in range(days, 0, -1):
        activity_date = (datetime.utcnow() - timedelta(days=day_offset)).date()
        hours_today = max(0.0, avg_hours_per_day + random.uniform(-2, 3))
        income_today = hours_today * base_hourly_rate

        if random.random() < 0.15:
            hours_today = 0.0
            income_today = 0.0

        daily_history.append(
            {
                "date": activity_date.isoformat(),
                "hours": round(hours_today, 2),
                "income": round(income_today, 2),
                "orders": max(0, int(hours_today * 2.5)),
            }
        )
        total_income += income_today
        total_hours += hours_today

    avg_weekly_income = (total_income / days) * 7 if days > 0 else 0.0
    avg_weekly_hours = (total_hours / days) * 7 if days > 0 else 0.0

    rider.baseline_weekly_income = round(avg_weekly_income, 2)
    rider.baseline_weekly_hours = round(avg_weekly_hours, 2)
    rider.daily_income_history = daily_history
    rider.is_seasoning = False

    premium_quotes = await build_premium_quotes(db, rider)
    subscription_state.premium_quotes = premium_quotes
    subscription_state.last_quotes_at = current_time
    subscription_state.last_seeded_at = current_time

    if active_policy is None:
        trial_expired_by_calendar = current_time >= get_trial_expires_at(subscription_state.trial_started_at)
        if not previous_had_history and subscription_state.trial_completed_at is None:
            subscription_state.trial_completed_at = current_time
        sync_subscription_phase(subscription_state, active_policy=None, now=current_time)
        if (
            subscription_state.phase == "plan_selection"
            and subscription_state.last_notified_at is None
            and premium_quotes
            and (not previous_had_history or trial_expired_by_calendar)
        ):
            subscription_state.last_notified_at = current_time
    else:
        sync_subscription_phase(subscription_state, active_policy=active_policy, now=current_time)

    await db.commit()
    await db.refresh(rider)
    await db.refresh(subscription_state)

    return {
        "message": f"Seeded {days} days of activity data",
        "rider_id": rider.id,
        "days_seeded": days,
        "total_income": round(total_income, 2),
        "total_hours": round(total_hours, 2),
        "new_baseline": {
            "weekly_income": round(avg_weekly_income, 2),
            "weekly_hours": round(avg_weekly_hours, 2),
            "hourly_rate": round(avg_weekly_income / avg_weekly_hours if avg_weekly_hours > 0 else 0, 2),
        },
        "daily_history": daily_history,
        "premium_quotes": premium_quotes,
        "quote_summary": quote_summary_from_quotes(premium_quotes),
        "trial_transition": {
            "from_phase": previous_phase,
            "to_phase": subscription_state.phase,
            "first_seed": not previous_had_history,
            "trial_completed_at": isoformat(subscription_state.trial_completed_at),
            "notification_pending": notification_is_unread(subscription_state),
        },
        "subscription_state": serialize_subscription_state(rider, subscription_state, active_policy=active_policy),
    }


# ── 1. Worker Management ──────────────────────────────────────────────────────

@router.get("/workers", dependencies=[Depends(require_admin)])
async def list_workers(
    platform: Optional[str] = None,
    zone_id: Optional[int] = None,
    tier: Optional[str] = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Rider)
    if platform:
        stmt = stmt.where(Rider.platform == platform)
    if zone_id:
        stmt = stmt.where(Rider.zone1_id == zone_id)
    if tier:
        stmt = stmt.where(Rider.tier == tier)
        
    stmt = stmt.offset(offset).limit(limit).order_by(Rider.id.desc())
    result = await db.execute(stmt)
    workers = result.scalars().all()

    payload = []
    for worker in workers:
        payload.append(await _serialize_worker_summary(db, worker))
    return payload


@router.get("/workers/{rider_id}", dependencies=[Depends(require_admin)])
async def get_worker(
    rider_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Rider).where(Rider.id == rider_id))
    worker = result.scalar_one_or_none()
    if not worker:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rider not found")
    
    # Also fetch active policy for renewal info
    stmt = select(Policy).where(
        and_(Policy.rider_id == rider_id, Policy.status == "active", Policy.cycle_end_date >= date.today())
    )
    pol_result = await db.execute(stmt)
    policy = pol_result.scalar_one_or_none()
    
    subscription_state = await ensure_subscription_state(db, worker, active_policy=policy)
    sync_subscription_phase(subscription_state, active_policy=policy)

    worker_data = worker.to_dict()
    worker_data["active_policy"] = policy.to_dict() if policy else None
    worker_data["subscription_state"] = serialize_subscription_state(worker, subscription_state, active_policy=policy)
    worker_data["trial_phase"] = subscription_state.phase
    worker_data["trial_started_at"] = isoformat(subscription_state.trial_started_at)
    worker_data["trial_completed_at"] = isoformat(subscription_state.trial_completed_at)
    worker_data["has_seeded_history"] = has_seeded_history(worker)
    worker_data["last_seeded_at"] = isoformat(subscription_state.last_seeded_at)
    worker_data["last_quotes_at"] = isoformat(subscription_state.last_quotes_at)
    worker_data["quote_summary"] = quote_summary_from_quotes(subscription_state.premium_quotes)
    return worker_data


class WorkerBlockRequest(BaseModel):
    is_blocked: bool


@router.patch("/workers/{rider_id}/block", dependencies=[Depends(require_admin)])
async def toggle_worker_block(
    rider_id: int,
    request: WorkerBlockRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Rider).where(Rider.id == rider_id))
    worker = result.scalar_one_or_none()
    if not worker:
        raise HTTPException(status_code=404, detail="Rider not found")
        
    worker.is_blocked = request.is_blocked
    await db.commit()
    return {"message": f"Worker blocked status set to {request.is_blocked}", "rider_id": rider_id}


class KYCReviewRequest(BaseModel):
    action: str
    reason: Optional[str] = None


@router.patch("/workers/{rider_id}/verify-kyc", dependencies=[Depends(require_admin)])
async def verify_kyc(
    rider_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Rider).where(Rider.id == rider_id))
    worker = result.scalar_one_or_none()
    if not worker:
        raise HTTPException(status_code=404, detail="Rider not found")
        
    worker.kyc_verified = True
    await db.commit()
    return {"message": "Worker KYC verified", "rider_id": rider_id}


@router.patch("/workers/{rider_id}/review-kyc", dependencies=[Depends(require_admin)])
async def review_kyc(
    rider_id: int,
    request: KYCReviewRequest,
    db: AsyncSession = Depends(get_db),
):
    if request.action not in ("approve", "reject"):
        raise HTTPException(status_code=400, detail="Invalid KYC action")

    result = await db.execute(select(Rider).where(Rider.id == rider_id))
    worker = result.scalar_one_or_none()
    if not worker:
        raise HTTPException(status_code=404, detail="Rider not found")

    if request.action == "approve":
        worker.kyc_verified = True
        worker.is_blocked = False
    else:
        worker.kyc_verified = False
        # Rejections are held from activation until corrected and re-reviewed.
        worker.is_blocked = True

    await db.commit()
    await db.refresh(worker)
    return {
        "message": f"KYC {request.action}d successfully",
        "rider_id": rider_id,
        "worker": worker.to_dict(),
        "reason": request.reason,
    }


# ── 2. Claims & Payouts ───────────────────────────────────────────────────────
# NOTE: All Claims, Payouts, and Disaster Simulation logic has been structurally
# decoupled and moved to Module 3 (module3-triggers-claims) running on port 8003.
# This prevents database locks during mass disaster simulation from degrading
# the registration API performance.


# ── 3. Fraud Monitoring (Dynamic Alert Store) ─────────────────────────────────

# In-memory store that accumulates fraud alerts from attack simulations
_fraud_alert_store: list[dict] = [
    {
        "rider_id": 12,
        "reason": "High claim frequency across multiple adjacent bins",
        "risk_score": 0.92,
        "exploit_type": "anomaly",
        "detection_method": "Isolation Forest",
        "action_taken": "Flagged for manual review",
        "flagged_at": "2026-03-31T10:00:00Z"
    },
    {
        "rider_id": 45,
        "reason": "Suspicious baseline spike post-registration",
        "risk_score": 0.85,
        "exploit_type": "baseline_inflation",
        "detection_method": "AIRA Behavioral Analysis",
        "action_taken": "Trust score reduced to 20",
        "flagged_at": "2026-03-31T09:15:00Z"
    }
]


@router.get("/fraud/flagged", dependencies=[Depends(require_admin)])
async def get_fraud_flagged():
    """Returns dynamically accumulated fraud alerts (attack simulations add to this list)."""
    return {"flagged_users": _fraud_alert_store}


@router.get("/fraud/zone-anomalies", dependencies=[Depends(require_admin)])
async def get_zone_anomalies():
    return {
        "anomalous_zones": [
            {
                "zone_id": 3,
                "anomaly_type": "disproportionate_claims",
                "description": "Claim volume is 3x higher than average",
                "severity": "high"
            }
        ]
    }


@router.get("/fraud/referrals", dependencies=[Depends(require_admin)])
async def get_fraud_referrals():
    return {
        "suspicious_referral_clusters": [
            {
                "cluster_token": "REF-ABC-123",
                "rider_ids": [101, 102, 103, 104],
                "risk_score": 0.88,
                "reason": "Simultaneous onboardings and exact same activity windows"
            }
        ]
    }


@router.get("/fraud/collusion", dependencies=[Depends(require_admin)])
async def get_fraud_collusion():
    return {
        "collusion_rings": [
            {
                "ring_id": "CR_001",
                "primary_zone_id": 9,
                "involved_riders": 5,
                "risk_intensity": 0.95
            }
        ]
    }


# ── 4. Zone & Coverage Management ─────────────────────────────────────────────

@router.get("/zones", dependencies=[Depends(require_admin)])
async def admin_get_zones(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Zone).order_by(Zone.zone_id))
    zones = result.scalars().all()

    payload = []
    recent_cutoff = datetime.utcnow() - timedelta(days=7)

    for zone in zones:
        recent_result = await db.execute(
            select(DisruptionEvent)
            .where(
                and_(
                    DisruptionEvent.affected_zone == zone.zone_id,
                    DisruptionEvent.event_start >= recent_cutoff,
                )
            )
            .order_by(DisruptionEvent.event_start.desc())
        )
        recent_events = recent_result.scalars().all()
        latest_event = recent_events[0] if recent_events else None

        zone_data = zone.to_dict()
        zone_data["recent_event_count"] = len(recent_events)
        zone_data["active_event_count"] = sum(1 for event in recent_events if event.processing_status == "processed")
        zone_data["latest_event_type"] = latest_event.event_type if latest_event else None
        zone_data["latest_event_at"] = latest_event.event_start.isoformat() if latest_event and latest_event.event_start else None
        payload.append(zone_data)

    return payload


class ToggleZoneRequest(BaseModel):
    is_active: bool


@router.patch("/zones/{zone_id}/toggle", dependencies=[Depends(require_admin)])
async def toggle_zone(
    zone_id: int,
    request: ToggleZoneRequest,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Zone).where(Zone.zone_id == zone_id))
    zone = result.scalar_one_or_none()
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")
        
    zone.is_active = request.is_active
    await db.commit()
    return {"message": f"Zone {zone_id} is_active set to {request.is_active}"}


@router.get("/zones/{zone_id}/events", dependencies=[Depends(require_admin)])
async def get_zone_events(zone_id: int, db: AsyncSession = Depends(get_db)):
    stmt = select(DisruptionEvent).where(DisruptionEvent.affected_zone == zone_id).order_by(DisruptionEvent.event_start.desc())
    result = await db.execute(stmt)
    return [e.to_dict() for e in result.scalars().all()]


# ── 5. Financial Overview ─────────────────────────────────────────────────────

@router.get("/analytics/financial", dependencies=[Depends(require_admin)])
async def get_financial_analytics(db: AsyncSession = Depends(get_db)):
    """Computes basic financial stats off real DB data."""
    
    # Total premiums collected
    prem_stmt = select(func.sum(Policy.weekly_premium)).where(Policy.status != "cancelled")
    prem_result = await db.execute(prem_stmt)
    total_premiums = float(prem_result.scalar() or 0.0)
    
    # Total payouts made
    payout_stmt = select(func.sum(Payout.amount)).where(Payout.status == "success")
    payout_result = await db.execute(payout_stmt)
    total_payouts = float(payout_result.scalar() or 0.0)
    
    # Loss ratio
    loss_ratio = total_payouts / total_premiums if total_premiums > 0 else 0.0
    
    # Payout Cap Utilization
    # To mock something meaningful for actual calculation: we gather the max possible exposure vs actual payout
    cap_stmt = select(func.sum(Policy.weekly_payout_cap)).where(Policy.status == "active")
    cap_result = await db.execute(cap_stmt)
    total_liability = float(cap_result.scalar() or 0.0)
    
    payout_cap_utilization = total_payouts / total_liability if total_liability > 0 else 0.0
    
    # Churn rate: active policies out of total unique riders
    riders_result = await db.execute(select(func.count(Rider.id)))
    total_riders = riders_result.scalar() or 1
    
    active_pol_result = await db.execute(select(func.count(Policy.id)).where(Policy.status == "active"))
    active_policies = active_pol_result.scalar() or 0
    
    churn_rate = 1.0 - (active_policies / total_riders) if total_riders > 0 else 0.0

    return {
        "total_premiums": round(total_premiums, 2),
        "total_payouts": round(total_payouts, 2),
        "loss_ratio": round(loss_ratio, 4),
        "total_liability": round(total_liability, 2),
        "payout_cap_utilization": round(payout_cap_utilization, 4),
        "churn_rate": round(churn_rate, 4)
    }


@router.get("/analytics/actuarial", dependencies=[Depends(require_admin)])
async def get_actuarial_analytics(db: AsyncSession = Depends(get_db)):
    def month_start(dt: datetime) -> datetime:
        return dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    def add_months(dt: datetime, months: int) -> datetime:
        total_months = (dt.year * 12 + (dt.month - 1)) + months
        year = total_months // 12
        month = (total_months % 12) + 1
        return dt.replace(year=year, month=month, day=1)

    tiers = ["kavach", "suraksha", "raksha"]
    tier_breakdown = []

    for tier in tiers:
        premium_result = await db.execute(
            select(func.sum(Policy.weekly_premium)).where(Policy.tier == tier)
        )
        payout_result = await db.execute(
            select(func.sum(Payout.amount))
            .join(Claim, Claim.id == Payout.claim_id)
            .join(Policy, Policy.id == Claim.policy_id)
            .where(
                and_(
                    Policy.tier == tier,
                    Payout.status == "success",
                )
            )
        )
        claims_result = await db.execute(
            select(func.count(Claim.id))
            .join(Policy, Policy.id == Claim.policy_id)
            .where(Policy.tier == tier)
        )

        premiums = float(premium_result.scalar() or 0.0)
        payouts = float(payout_result.scalar() or 0.0)
        claims = int(claims_result.scalar() or 0)
        ratio = (payouts / premiums * 100.0) if premiums > 0 else 0.0

        tier_breakdown.append(
            {
                "name": tier.capitalize(),
                "value": round(ratio, 1),
                "premiums": round(premiums, 2),
                "payouts": round(payouts, 2),
                "claims": claims,
            }
        )

    monthly_rows = []
    current_month_start = month_start(datetime.utcnow())
    for month_offset in range(-3, 1):
        bucket_start = add_months(current_month_start, month_offset)
        bucket_end = add_months(bucket_start, 1)
        label = bucket_start.strftime("%b")

        month_claims = await db.execute(
            select(func.count(Claim.id)).where(
                and_(
                    Claim.created_at >= bucket_start,
                    Claim.created_at < bucket_end,
                )
            )
        )
        month_payouts = await db.execute(
            select(func.sum(Payout.amount)).where(
                and_(
                    Payout.created_at >= bucket_start,
                    Payout.created_at < bucket_end,
                    Payout.status == "success",
                )
            )
        )

        monthly_rows.append(
            {
                "month": label,
                "volume": int(month_claims.scalar() or 0),
                "payouts": round(float(month_payouts.scalar() or 0.0), 2),
            }
        )

    cap_hits_result = await db.execute(
        select(func.count(Claim.id))
        .join(Policy, Policy.id == Claim.policy_id)
        .where(
            and_(
                Claim.final_payout.is_not(None),
                Claim.final_payout == Policy.weekly_payout_cap,
            )
        )
    )
    claims_paid_result = await db.execute(
        select(func.count(Payout.id)).where(Payout.status == "success")
    )

    financial = await get_financial_analytics(db)

    return {
        "loss_ratio_percent": round(financial["loss_ratio"] * 100, 1),
        "premiums_collected": financial["total_premiums"],
        "claims_paid_amount": financial["total_payouts"],
        "claims_paid_count": int(claims_paid_result.scalar() or 0),
        "payout_cap_hits": int(cap_hits_result.scalar() or 0),
        "tier_loss_ratio": tier_breakdown,
        "claim_volume": monthly_rows,
    }


@router.get("/payouts/live", dependencies=[Depends(require_admin)])
async def get_live_payouts(
    limit: int = Query(100, le=200),
    status_filter: Optional[str] = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(Payout, Claim, Rider)
        .join(Claim, Claim.id == Payout.claim_id)
        .join(Rider, Rider.id == Payout.rider_id)
        .order_by(Payout.created_at.desc())
        .limit(limit)
    )

    if status_filter:
        stmt = stmt.where(Payout.status == status_filter)

    result = await db.execute(stmt)
    rows = result.all()

    return [
        {
            "id": payout.id,
            "claim_id": payout.claim_id,
            "rider_id": payout.rider_id,
            "partner_id": rider.partner_id,
            "worker_name": rider.name,
            "amount": float(payout.amount),
            "gateway": payout.gateway,
            "status": payout.status,
            "gateway_reference": payout.gateway_reference,
            "initiated_at": payout.initiated_at.isoformat() if payout.initiated_at else None,
            "completed_at": payout.completed_at.isoformat() if payout.completed_at else None,
            "claim_status": claim.status,
        }
        for payout, claim, rider in rows
    ]


# ── 6. System Config ──────────────────────────────────────────────────────────

@router.get("/config", dependencies=[Depends(require_admin)])
async def get_system_config():
    """Return mock or current module settings."""
    return {
        "tier_parameters": TIER_CONFIG,
        "fraud_thresholds": {
            "high_claim_frequency": 3,
            "collusion_proximity_meters": 50,
        },
        "batch_job_status": {
            "last_premium_run": "2026-03-31T01:00:00Z",
            "last_gate_eval": "2026-03-31T03:00:00Z"
        }
    }


class ConfigPatchRequest(BaseModel):
    fraud_thresholds: Optional[dict] = None
    update_message: Optional[str] = None


@router.patch("/config", dependencies=[Depends(require_admin)])
async def update_system_config(request: ConfigPatchRequest):
    """Mocks accepting config modification."""
    return {
        "message": "Configuration updated successfully (mock)",
        "fraud_thresholds": request.fraud_thresholds or {}
    }


# ── 7. Seed Demo Data ─────────────────────────────────────────────────────────

_SEED_RIDERS = [
    {"partner_prefix": "SWG-ARJ", "name": "Arjun Patel",    "phone_seed": "9101000001", "platform": "swiggy",  "city": "Mumbai",    "tier": "kavach",   "zone1_id": 9,  "zone2_id": 10, "kyc_verified": True,  "is_blocked": False},
    {"partner_prefix": "ZMT-PRI", "name": "Priya Sharma",   "phone_seed": "9101000002", "platform": "zomato",  "city": "Chennai",   "tier": "suraksha", "zone1_id": 1,  "zone2_id": 2,  "kyc_verified": True,  "is_blocked": False},
    {"partner_prefix": "SWG-RAJ", "name": "Rajesh Kumar",   "phone_seed": "9101000003", "platform": "swiggy",  "city": "Delhi",     "tier": "raksha",   "zone1_id": 19, "zone2_id": 20, "kyc_verified": True,  "is_blocked": False},
    {"partner_prefix": "ZMT-ANA", "name": "Ananya Reddy",   "phone_seed": "9101000004", "platform": "zomato",  "city": "Bangalore", "tier": "suraksha", "zone1_id": 13, "zone2_id": 14, "kyc_verified": False, "is_blocked": False},
    {"partner_prefix": "SWG-VIK", "name": "Vikram Singh",   "phone_seed": "9101000005", "platform": "swiggy",  "city": "Mumbai",    "tier": "raksha",   "zone1_id": 11, "zone2_id": 12, "kyc_verified": True,  "is_blocked": False},
    {"partner_prefix": "DNZ-MEE", "name": "Meera Joshi",    "phone_seed": "9101000006", "platform": "dunzo",   "city": "Delhi",     "tier": "suraksha", "zone1_id": 17, "zone2_id": 19, "kyc_verified": False, "is_blocked": False},
    {"partner_prefix": "ZMT-KAV", "name": "Kavya Nair",     "phone_seed": "9101000007", "platform": "zomato",  "city": "Chennai",   "tier": "kavach",   "zone1_id": 5,  "zone2_id": 8,  "kyc_verified": True,  "is_blocked": True},
    {"partner_prefix": "SWG-IMR", "name": "Imran Shaikh",   "phone_seed": "9101000008", "platform": "swiggy",  "city": "Bangalore", "tier": "raksha",   "zone1_id": 14, "zone2_id": 15, "kyc_verified": True,  "is_blocked": False},
]


_SEED_EVENT_TEMPLATES = [
    {"event_type": "flood",            "severity": "severe_l1", "payout_rate": 0.85, "zone_id": 9,  "lost_hours": 6.0},
    {"event_type": "heavy_rain",       "severity": "moderate",  "payout_rate": 0.60, "zone_id": 10, "lost_hours": 3.5},
    {"event_type": "cyclone",          "severity": "severe_l2", "payout_rate": 0.90, "zone_id": 1,  "lost_hours": 7.0},
    {"event_type": "civic_disruption", "severity": "moderate",  "payout_rate": 0.55, "zone_id": 13, "lost_hours": 4.5},
    {"event_type": "extreme_heat",     "severity": "severe_l1", "payout_rate": 0.70, "zone_id": 19, "lost_hours": 5.0},
]


def _event_is_covered(tier: str, event_type: str) -> bool:
    allowed_triggers = TIER_CONFIG.get(tier, {}).get("coverage_triggers", [])
    if event_type in allowed_triggers:
        return True
    if "weather_conditions" in allowed_triggers and event_type in {"heavy_rain", "cyclone", "flood", "extreme_heat"}:
        return True
    if "platform_outages" in allowed_triggers and event_type == "civic_disruption":
        return True
    if "civic_disruptions" in allowed_triggers and event_type == "civic_disruption":
        return True
    if event_type == "other":
        return True
    return False


@router.post("/seed-demo", dependencies=[Depends(require_admin)])
async def seed_demo_data(db: AsyncSession = Depends(get_db)):
    """
    Generates a realistic demo dataset across riders, policies, events,
    claims, and payouts so the admin dashboard feels live.
    """
    # Inline premium constants (same as Module 2) so this always works
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
    FLOOR = 15.0
    CAP_PCT = 0.035

    zone_rows = await db.execute(select(Zone).order_by(Zone.zone_id))
    zones = zone_rows.scalars().all()
    if not zones:
        raise HTTPException(
            status_code=400,
            detail="No zones found. Seed the base schema before running demo data.",
        )

    batch_id = datetime.utcnow().strftime("%m%d%H%M%S")
    existing_riders_result = await db.execute(select(func.count(Rider.id)))
    rider_offset = existing_riders_result.scalar() or 0

    created_workers = []
    created_policies = 0

    for index, seed in enumerate(_SEED_RIDERS, start=1):
        suffix = rider_offset + index
        partner_id = f"{seed['partner_prefix']}-{suffix:04d}"
        phone = str(int(seed["phone_seed"]) + suffix)[-10:]

        daily_earnings = [round(random.uniform(400, 1200), 2) for _ in range(15)]
        history_list = [{"day": 15 - i, "amount": amt} for i, amt in enumerate(daily_earnings)]
        total_earnings = sum(daily_earnings)
        avg_daily = total_earnings / 15
        baseline_weekly_income = round(avg_daily * 7, 2)
        baseline_weekly_hours = round(random.uniform(35, 50), 1)

        zone_ids = [seed["zone1_id"]]
        if seed.get("zone2_id"):
            zone_ids.append(seed["zone2_id"])
        if seed.get("zone3_id"):
            zone_ids.append(seed["zone3_id"])

        tier_cfg = TIER_CONFIG[seed["tier"]]
        tier_rate = tier_cfg["tier_rate"]
        risks = [_ZONE_RISK.get(z, 1.0) for z in zone_ids]
        zone_risk = round(sum(risks) / len(risks), 4) if risks else 1.0
        seasonal_factor = _SEASONAL.get(datetime.now().month, 1.0)

        raw_premium = baseline_weekly_income * tier_rate * zone_risk * seasonal_factor
        raw_floored = max(raw_premium, FLOOR)
        floor_applied = raw_premium < FLOOR
        cap_amount = baseline_weekly_income * CAP_PCT
        cap_applied = raw_floored > cap_amount and baseline_weekly_income > 0
        final_premium = round(min(raw_floored, cap_amount) if baseline_weekly_income > 0 else 0.0, 2)

        breakdown_json = {
            "income": baseline_weekly_income,
            "tier_rate": tier_rate,
            "zone_risk": zone_risk,
            "seasonal_factor": seasonal_factor,
            "raw_premium": round(raw_premium, 2),
            "floor_applied": floor_applied,
            "cap_applied": cap_applied,
            "final_premium": final_premium,
        }

        rider = Rider(
            partner_id=partner_id,
            platform=seed["platform"],
            name=seed["name"],
            phone=phone,
            aadhaar_last4=str(1000 + suffix)[-4:] if index % 2 else None,
            pan=(f"RPAYA{suffix:04d}F")[:10] if index % 2 == 0 else None,
            city=seed["city"],
            zone1_id=seed["zone1_id"],
            zone2_id=seed.get("zone2_id"),
            zone3_id=seed.get("zone3_id"),
            tier=seed["tier"],
            baseline_weekly_income=baseline_weekly_income,
            baseline_weekly_hours=baseline_weekly_hours,
            daily_income_history=history_list,
            is_seasoning=index % 3 == 0,
            trust_score=round(random.uniform(38, 91), 2),
            is_blocked=seed["is_blocked"],
            kyc_verified=seed["kyc_verified"],
        )
        db.add(rider)
        await db.flush()

        policy_status = "active" if index % 5 else "pending"
        cycle_start = date.today() - timedelta(days=(index - 1) * 2)
        policy = Policy(
            rider_id=rider.id,
            tier=seed["tier"],
            weekly_premium=final_premium,
            premium_breakdown=breakdown_json,
            weekly_payout_cap=tier_cfg["weekly_payout_cap"],
            coverage_type=tier_cfg["coverage_type"],
            status=policy_status,
            cycle_start_date=cycle_start,
            cycle_end_date=cycle_start + timedelta(days=28),
        )
        db.add(policy)
        created_policies += 1

        created_workers.append({
            "name": seed["name"],
            "partner_id": partner_id,
            "tier": seed["tier"],
            "city": seed["city"],
            "baseline_weekly_income": baseline_weekly_income,
            "weekly_premium": final_premium,
        })

    await db.flush()

    riders_result = await db.execute(
        select(Rider)
        .options(selectinload(Rider.policies))
        .order_by(Rider.id.desc())
        .limit(60)
    )
    demo_riders = riders_result.scalars().all()

    created_events = 0
    created_claims = 0
    created_payouts = 0
    event_summaries = []

    for event_index, template in enumerate(_SEED_EVENT_TEMPLATES, start=1):
        event_start = datetime.utcnow() - timedelta(hours=event_index * 3)
        event = DisruptionEvent(
            event_type=template["event_type"],
            severity=template["severity"],
            payout_rate=template["payout_rate"],
            affected_zone=template["zone_id"],
            trigger_data={
                "source": "seed_demo",
                "batch_id": batch_id,
                "alert_code": f"DEMO-{batch_id}-{event_index}",
            },
            event_start=event_start,
            event_end=event_start + timedelta(hours=8),
            processing_status="processed",
        )
        db.add(event)
        await db.flush()
        created_events += 1

        claims_for_event = 0

        for rider in demo_riders:
            if rider.is_blocked:
                continue

            active_policy = rider.active_policy
            if not active_policy:
                continue

            rider_zones = {z for z in [rider.zone1_id, rider.zone2_id, rider.zone3_id] if z is not None}
            if template["zone_id"] not in rider_zones:
                continue

            if not _event_is_covered(active_policy.tier, template["event_type"]):
                continue

            hourly_rate = rider.baseline_hourly_rate or 100.0
            calculated = round(template["lost_hours"] * hourly_rate * template["payout_rate"], 2)
            final_amt = round(min(calculated, float(active_policy.weekly_payout_cap), 5000.0), 2)

            status_cycle = ["pending", "approved", "paid", "rejected"]
            claim_status = status_cycle[(created_claims + event_index) % len(status_cycle)]
            if final_amt <= 0:
                claim_status = "rejected"

            claim = Claim(
                rider_id=rider.id,
                policy_id=active_policy.id,
                disruption_event_id=event.id,
                gate_results={
                    "seed_demo": True,
                    "batch_id": batch_id,
                    "zone_match": True,
                    "kyc_verified": rider.kyc_verified,
                },
                is_eligible=claim_status != "rejected",
                ineligibility_reason=None if claim_status != "rejected" else "Demo rejection for dashboard variety",
                lost_hours=template["lost_hours"],
                hourly_rate=hourly_rate,
                severity_rate=template["payout_rate"],
                calculated_payout=calculated,
                final_payout=0 if claim_status == "rejected" else final_amt,
                status=claim_status,
            )
            db.add(claim)
            await db.flush()
            created_claims += 1
            claims_for_event += 1

            if claim_status == "paid":
                payout = Payout(
                    claim_id=claim.id,
                    rider_id=rider.id,
                    amount=final_amt,
                    gateway="test" if event_index % 2 else "razorpay",
                    gateway_reference=f"DEMO-PAYOUT-{batch_id}-{claim.id}",
                    gateway_response={"seed_demo": True, "status": "captured"},
                    upi_id=f"{rider.partner_id.lower().replace('-', '')[:12]}@okaxis",
                    status="success",
                    initiated_at=event_start + timedelta(minutes=20),
                    completed_at=event_start + timedelta(minutes=45),
                )
                db.add(payout)
                created_payouts += 1

        event_summaries.append(
            {
                "event_type": template["event_type"],
                "zone_id": template["zone_id"],
                "claims_created": claims_for_event,
            }
        )

    await db.commit()

    return {
        "message": "Demo dataset seeded for dashboard walkthrough",
        "riders_created": len(created_workers),
        "policies_created": created_policies,
        "events_created": created_events,
        "claims_created": created_claims,
        "payouts_created": created_payouts,
        "details": created_workers,
        "event_summaries": event_summaries,
    }


# ── 8. Attack Simulation Engine ───────────────────────────────────────────────

class AttackSimulationRequest(BaseModel):
    attack_type: str  # gps_spoofing | baseline_inflation | velocity_exploit | collusion_ring


_ATTACK_SCENARIOS = {
    "gps_spoofing": {
        "title": "GPS Spoofing Attack",
        "description": "Rider R-1042 faked their GPS location to match Zone 9 (Mumbai Fort) during Cyclone Meera, despite being physically located 50km away in Navi Mumbai.",
        "detection_method": "Cell-tower triangulation mismatch + accelerometer zero-movement check",
        "evidence": [
            "GPS reported: 18.9340°N, 72.8355°E (Mumbai Fort — disaster zone)",
            "Cell tower triangulation: 19.0330°N, 73.0297°E (Navi Mumbai — 50km away)",
            "Accelerometer data: 0.0 m/s² for 4 hours (device stationary at home)",
            "No platform activity logs from Swiggy API during claimed disruption window",
        ],
        "countermeasure": "Claim C-8847 auto-rejected. Trust score reduced from 72 to 15. Account flagged for manual review.",
        "risk_score": 0.96,
        "rider_id": 1042,
    },
    "baseline_inflation": {
        "title": "Baseline Inflation Exploit",
        "description": "Rider R-2088 artificially worked 18-hour days during their 4-week seasoning period to inflate their baseline_weekly_income from ₹3,500 to ₹14,200, then dropped to 2 hours/day after seasoning ended.",
        "detection_method": "AIRA Behavioral Deviation Model (z-score > 3.2 vs city median)",
        "evidence": [
            "Seasoning period avg: ₹14,200/week (z-score 3.4 vs Chennai median ₹3,500)",
            "Post-seasoning avg: ₹980/week (93% drop in activity)",
            "Weekly payout cap was artificially inflated to ₹5,000 based on fake baseline",
            "Pattern matches known 'pump-and-dump' insurance fraud playbook",
        ],
        "countermeasure": "Baseline recalculated to city median ₹3,500. Premium adjusted. Trust score dropped to 10. Flagged for KYC re-verification.",
        "risk_score": 0.91,
        "rider_id": 2088,
    },
    "velocity_exploit": {
        "title": "Velocity / Rate-Limit Exploit",
        "description": "An automated bot submitted 50 claim requests in 2 minutes for Rider R-3055 during a minor rain event, attempting to drain the payout pool before daily batch validation.",
        "detection_method": "Rate limiter + request fingerprinting (identical User-Agent, sub-second intervals)",
        "evidence": [
            "50 POST /claims requests in 120 seconds from IP 103.21.xx.xx",
            "All requests had identical headers and payload templates",
            "Normal human claim rate: 1 per event. This was 50x anomalous.",
            "Request intervals: 2.1s, 2.3s, 2.0s — consistent bot pattern",
        ],
        "countermeasure": "Rate limiter blocked 48/50 claims. 2 that passed were auto-held. Rider account suspended. IP address blacklisted. Incident escalated to fraud team.",
        "risk_score": 0.98,
        "rider_id": 3055,
    },
    "collusion_ring": {
        "title": "Collusion Ring Detection",
        "description": "5 riders (R-4001 through R-4005) in Zone 19 (Delhi Badarpur) submitted claims for the exact same 'flood' event within a 3-minute window, all reporting identical lost hours (6.0) and identical severity rates.",
        "detection_method": "Spatial graph clustering + temporal coincidence analysis",
        "evidence": [
            "All 5 riders registered within 48 hours of each other (same referral token REF-DL-9923)",
            "Claims submitted at: 14:01, 14:02, 14:02, 14:03, 14:03 — 3-minute window",
            "All claimed exactly 6.0 lost hours with severity_rate 0.85",
            "KYC documents show 3/5 share the same residential address",
            "No IMD weather alert for Delhi Badarpur during the claimed period",
        ],
        "countermeasure": "All 5 accounts frozen. Collusion Ring CR_002 created. Claims auto-rejected. Referral token REF-DL-9923 permanently blacklisted.",
        "risk_score": 0.97,
        "rider_id": 4001,
    },
}


async def _resolve_imran_rider(db: AsyncSession) -> Optional[Rider]:
    """Prefer the app demo login rider, then fall back to seeded Imran records."""
    stmt = select(Rider).where(
        or_(
            Rider.partner_id == "demo-imran-shaikh",
            Rider.name == "Imran Shaikh",
            Rider.partner_id.like("SWG-IMR-%"),
        )
    ).order_by(Rider.id.desc())
    result = await db.execute(stmt)
    return result.scalars().first()


@router.post("/simulate-attack", dependencies=[Depends(require_admin)])
async def simulate_attack(
    request: AttackSimulationRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Simulates a specific fraud attack scenario and returns the full detection
    pipeline response. Also appends the result to the live fraud alert feed.
    """
    scenario = _ATTACK_SCENARIOS.get(request.attack_type)
    if not scenario:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown attack_type '{request.attack_type}'. Valid: {list(_ATTACK_SCENARIOS.keys())}"
        )

    rider = await _resolve_imran_rider(db)
    rider_id = rider.id if rider else scenario["rider_id"]

    # Append to the dynamic fraud alert store so the Fraud page updates
    alert = {
        "rider_id": rider_id,
        "reason": scenario["description"],
        "risk_score": scenario["risk_score"],
        "exploit_type": request.attack_type,
        "detection_method": scenario["detection_method"],
        "action_taken": scenario["countermeasure"],
        "flagged_at": datetime.utcnow().isoformat() + "Z",
    }

    # Don't duplicate if already simulated
    existing_ids = {(a["rider_id"], a["exploit_type"]) for a in _fraud_alert_store}
    if (alert["rider_id"], alert["exploit_type"]) not in existing_ids:
        _fraud_alert_store.insert(0, alert)

    synthetic_event = None
    if rider and rider.zone1_id:
        event_type_map = {
            "gps_spoofing": "flood",
            "baseline_inflation": "heavy_rain",
            "velocity_exploit": "poor_aqi",
            "collusion_ring": "civic_disruption",
        }
        severity_map = {
            "gps_spoofing": "severe_l1",
            "baseline_inflation": "moderate",
            "velocity_exploit": "severe_l1",
            "collusion_ring": "severe_l2",
        }
        payout_rate_map = {
            "gps_spoofing": 0.80,
            "baseline_inflation": 0.55,
            "velocity_exploit": 0.65,
            "collusion_ring": 0.85,
        }

        now = datetime.utcnow()
        synthetic_event = DisruptionEvent(
            event_type=event_type_map.get(request.attack_type, "other"),
            severity=severity_map.get(request.attack_type, "moderate"),
            payout_rate=payout_rate_map.get(request.attack_type, 0.5),
            affected_zone=rider.zone1_id,
            trigger_data={
                "source": "attack_simulation",
                "attack_type": request.attack_type,
                "target_rider_id": rider.id,
                "target_name": rider.name,
            },
            event_start=now,
            event_end=now + timedelta(hours=6),
            processing_status="processed",
        )
        db.add(synthetic_event)
        await db.commit()
        await db.refresh(synthetic_event)

    return {
        "attack_type": request.attack_type,
        "title": scenario["title"],
        "description": scenario["description"],
        "detection_method": scenario["detection_method"],
        "evidence": scenario["evidence"],
        "countermeasure": scenario["countermeasure"],
        "risk_score": scenario["risk_score"],
        "alert_added": True,
        "target_rider_id": rider_id,
        "target_rider_name": rider.name if rider else "Imran Shaikh",
        "mobile_event_created": bool(synthetic_event),
        "mobile_event_id": synthetic_event.id if synthetic_event else None,
        "mobile_event_zone": synthetic_event.affected_zone if synthetic_event else None,
    }


# ── 9. Disaster Simulation Proxy (Module 3) ───────────────────────────────────

class DisasterSimulationRequest(BaseModel):
    event_type: str
    severity: str
    affected_zone: int
    lost_hours: float
    severity_rate: float


@router.post("/simulate-disaster", dependencies=[Depends(require_admin)])
async def simulate_disaster_proxy(request: DisasterSimulationRequest):
    """
    Proxy endpoint to Module 3 (port 8003) for disaster simulation.
    This allows the Admin Dashboard to call only Module 1 (port 8001) for all simulations.
    """
    MODULE3_URL = "http://localhost:8003"
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{MODULE3_URL}/admin/simulate-disaster",
                json={
                    "event_type": request.event_type,
                    "severity": request.severity,
                    "affected_zone": request.affected_zone,
                    "lost_hours": request.lost_hours,
                    "severity_rate": request.severity_rate
                },
                headers={"Authorization": "Bearer admin_token"}
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as e:
        logger.error(f"Module 3 disaster simulation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Module 3 (Claims Engine) unavailable: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error in disaster simulation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Disaster simulation failed: {str(e)}"
        )


# ── 10. Real-time Event Polling (for Mobile App & Dashboard) ─────────────────

@router.get("/events/recent")
async def get_recent_events(
    limit: int = Query(20, le=100),
    zone_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Get recent disruption events for mobile app polling.
    Returns events from the last 7 days, optionally filtered by zone.
    """
    from sqlalchemy import desc
    
    stmt = select(DisruptionEvent).order_by(desc(DisruptionEvent.event_start)).limit(limit)
    
    if zone_id:
        stmt = stmt.where(DisruptionEvent.affected_zone == zone_id)
    
    result = await db.execute(stmt)
    events = result.scalars().all()
    
    return [
        {
            "id": e.id,
            "event_type": e.event_type,
            "severity": e.severity,
            "affected_zone": e.affected_zone,
            "event_start": e.event_start.isoformat() if e.event_start else None,
            "event_end": e.event_end.isoformat() if e.event_end else None,
            "payout_rate": e.payout_rate,
            "trigger_data": e.trigger_data,
        }
        for e in events
    ]


@router.get("/events/zone/{zone_id}")
async def get_zone_events(
    zone_id: int,
    hours: int = Query(168, description="Hours to look back (default 7 days)"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get disruption events for a specific zone within the last N hours.
    Used by mobile app to check for active events affecting the rider.
    """
    from sqlalchemy import desc, and_
    
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    
    stmt = select(DisruptionEvent).where(
        and_(
            DisruptionEvent.affected_zone == zone_id,
            DisruptionEvent.event_start >= cutoff
        )
    ).order_by(desc(DisruptionEvent.event_start))
    
    result = await db.execute(stmt)
    events = result.scalars().all()
    
    return [
        {
            "id": e.id,
            "event_type": e.event_type,
            "severity": e.severity,
            "payout_rate": e.payout_rate,
            "event_start": e.event_start.isoformat() if e.event_start else None,
            "trigger_data": e.trigger_data,
        }
        for e in events
    ]


@router.get("/rider/{rider_id}/active-events")
async def get_rider_active_events(
    rider_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get active disruption events affecting a specific rider.
    Checks all zones the rider is registered in (zone1, zone2, zone3).
    """
    from sqlalchemy import desc, and_, or_

    # Get rider's zones
    rider_result = await db.execute(select(Rider).where(Rider.id == rider_id))
    rider = rider_result.scalar_one_or_none()

    if not rider:
        raise HTTPException(status_code=404, detail="Rider not found")

    zone_ids = [z for z in [rider.zone1_id, rider.zone2_id, rider.zone3_id] if z is not None]

    if not zone_ids:
        return []

    # Get active events from last 72 hours in rider's zones
    cutoff = datetime.utcnow() - timedelta(hours=72)

    stmt = select(DisruptionEvent).where(
        and_(
            DisruptionEvent.affected_zone.in_(zone_ids),
            DisruptionEvent.event_start >= cutoff
        )
    ).order_by(desc(DisruptionEvent.event_start))

    result = await db.execute(stmt)
    events = result.scalars().all()

    return [
        {
            "id": e.id,
            "event_type": e.event_type,
            "severity": e.severity,
            "payout_rate": e.payout_rate,
            "affected_zone": e.affected_zone,
            "event_start": e.event_start.isoformat() if e.event_start else None,
        }
        for e in events
    ]


# ── User Sync & Seed Data Endpoints ───────────────────────────────────────────

class SyncUserRequest(BaseModel):
    """Request to sync a Firebase user to PostgreSQL"""
    firebase_uid: str
    email: str
    display_name: str
    phone: Optional[str] = None
    platform: str = "swiggy"
    city: str = "chennai"
    tier: str = "suraksha"
    zone1_id: int = 1
    zone2_id: Optional[int] = None
    zone3_id: Optional[int] = None


@router.post("/sync-user", dependencies=[Depends(require_admin)])
async def sync_firebase_user(
    request: SyncUserRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Sync a Firebase user to PostgreSQL riders table.
    Called after user signs up in mobile app.
    """
    try:
        existing = await db.execute(
            select(Rider).where(Rider.partner_id == request.firebase_uid)
        )
        existing_rider = existing.scalar_one_or_none()
        if existing_rider:
            active_policy = await get_active_paid_policy(db, existing_rider.id)
            subscription_state = await ensure_subscription_state(db, existing_rider, active_policy=active_policy)
            if not existing_rider.daily_income_history:
                await _generate_seeded_history(
                    db,
                    existing_rider,
                    days=15,
                    base_hourly_rate=70.0,
                    avg_hours_per_day=5.0,
                )

            return {
                "message": "User already synced",
                "rider_id": existing_rider.id,
                "status": "exists",
                "phase": subscription_state.phase,
            }

        rider = Rider(
            partner_id=request.firebase_uid,
            platform=request.platform,
            name=request.display_name,
            phone=request.phone or f"999999{random.randint(1000, 9999)}",
            aadhaar_last4="0000",
            city=request.city.title(),
            zone1_id=request.zone1_id,
            zone2_id=request.zone2_id,
            zone3_id=request.zone3_id,
            tier=request.tier,
            baseline_weekly_income=3500.00,
            baseline_weekly_hours=50.00,
            is_seasoning=True,
            trust_score=50.00,
            is_blocked=False,
            kyc_verified=False,
        )
        db.add(rider)
        await db.flush()

        subscription_state = await ensure_subscription_state(db, rider, active_policy=None)
        
        # Automatically generate 15-day sample history so everything is ready
        await _generate_seeded_history(
            db,
            rider,
            days=15,
            base_hourly_rate=70.0,
            avg_hours_per_day=5.0,
        )
        
        await db.commit()

        return {
            "message": "User synced successfully",
            "rider_id": rider.id,
            "status": "created",
            "phase": subscription_state.phase,
        }
    except Exception as e:
        await db.rollback()
        logger.error(f"Sync user error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class SeedUserDataRequest(BaseModel):
    """Request to seed 15 days of activity data for a user"""
    rider_id: int
    days: int = 15
    base_hourly_rate: float = 70.0
    avg_hours_per_day: float = 5.0


@router.post("/workers/{rider_id}/seed-sample-data", dependencies=[Depends(require_admin)])
async def seed_worker_sample_data(
    rider_id: int,
    request: SeedUserDataRequest,
    db: AsyncSession = Depends(get_db),
):
    if request.rider_id != rider_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Route rider_id and body rider_id must match.",
        )

    rider_result = await db.execute(select(Rider).where(Rider.id == rider_id))
    rider = rider_result.scalar_one_or_none()
    if rider is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rider not found")

    try:
        return await _generate_seeded_history(
            db,
            rider,
            days=request.days,
            base_hourly_rate=request.base_hourly_rate,
            avg_hours_per_day=request.avg_hours_per_day,
        )
    except HTTPException:
        raise
    except Exception as exc:
        await db.rollback()
        logger.error("Seed user data error: %s", exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post("/seed-user-data", dependencies=[Depends(require_admin)])
async def seed_user_activity_data(
    request: SeedUserDataRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Generate 15 days of realistic activity data for a rider.
    Creates daily income history and updates baseline.
    """
    try:
        rider_result = await db.execute(select(Rider).where(Rider.id == request.rider_id))
        rider = rider_result.scalar_one_or_none()
        if rider is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rider not found")

        return await _generate_seeded_history(
            db,
            rider,
            days=request.days,
            base_hourly_rate=request.base_hourly_rate,
            avg_hours_per_day=request.avg_hours_per_day,
        )
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Seed user data error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rider/{rider_id}/earnings", dependencies=[Depends(require_admin)])
async def get_rider_earnings(
    rider_id: int,
    days: int = 15,
    db: AsyncSession = Depends(get_db),
):
    """Get earnings history for a rider"""
    rider_result = await db.execute(
        select(Rider).where(Rider.id == rider_id)
    )
    rider = rider_result.scalar_one_or_none()

    if not rider:
        raise HTTPException(status_code=404, detail="Rider not found")

    history = rider.daily_income_history or []
    recent_history = history[-days:] if len(history) > days else history

    total_earnings = sum(day.get("income", 0) for day in recent_history)
    total_hours = sum(day.get("hours", 0) for day in recent_history)

    return {
        "rider_id": rider_id,
        "days": len(recent_history),
        "total_earnings": round(total_earnings, 2),
        "total_hours": round(total_hours, 2),
        "avg_daily_earnings": round(total_earnings / len(recent_history) if recent_history else 0, 2),
        "daily_history": recent_history,
        "baseline": {
            "weekly_income": float(rider.baseline_weekly_income or 0),
            "weekly_hours": float(rider.baseline_weekly_hours or 0),
        }
    }
