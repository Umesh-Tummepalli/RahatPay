from typing import Optional
import logging
from datetime import date, datetime, timezone, timedelta

from fastapi import APIRouter, HTTPException, status, Depends, Header
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_

# These are successfully imported because of the sys.path.insert in main.py
from db.connection import get_db
from models.rider import Rider
from models.policy import Policy, Claim, DisruptionEvent, Payout
from config import TIER_CONFIG

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Claims & Triggers Admin Panel"])

# ── Authentication ────────────────────────────────────────────────────────────

async def require_admin(authorization: Optional[str] = Header(None)):
    """Mock JWT role-based access for 'admin'."""
    if not authorization or authorization != "Bearer admin_token":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Admin access required.",
        )
    return True

# ── Claims & Payouts Engine ───────────────────────────────────────────────────

@router.get("/claims/live", dependencies=[Depends(require_admin)])
async def get_live_claims(db: AsyncSession = Depends(get_db)):
    """Fetch pending claims with policy tier information."""
    stmt = (
        select(Claim, Policy)
        .join(Policy, Policy.id == Claim.policy_id)
        .where(Claim.status == 'pending')
        .order_by(Claim.created_at.desc())
        .limit(100)
    )
    result = await db.execute(stmt)
    rows = result.all()
    
    return [
        {
            **claim.to_dict(),
            "tier": policy.tier,
            "weekly_payout_cap": float(policy.weekly_payout_cap),
        }
        for claim, policy in rows
    ]


def _event_is_covered(policy_tier: str, event_type: str) -> bool:
    tier_cfg = TIER_CONFIG.get(policy_tier, {})
    allowed_triggers = tier_cfg.get("coverage_triggers", [])

    if event_type in allowed_triggers:
        return True
    if "weather_conditions" in allowed_triggers and event_type in ("heavy_rain", "cyclone", "flood", "extreme_heat"):
        return True
    if "platform_outages" in allowed_triggers and event_type == "civic_disruption":
        return True
    if "civic_disruptions" in allowed_triggers and event_type == "civic_disruption":
        return True
    if event_type == "other":
        return True
    return False

class SimulateDisasterRequest(BaseModel):
    event_type: str
    severity: str
    affected_zone: int
    lost_hours: float
    severity_rate: float

@router.post("/simulate-disaster", dependencies=[Depends(require_admin)])
async def simulate_disaster(
    request: SimulateDisasterRequest,
    db: AsyncSession = Depends(get_db)
):
    try:
        logger.info(f"Starting disaster simulation: {request.event_type} in zone {request.affected_zone}")
        
        # 1. Create DisruptionEvent
        now = datetime.now(timezone.utc)
        event_end_time = now + timedelta(hours=8)  # Event lasts 8 hours
        
        event = DisruptionEvent(
            event_type=request.event_type,
            severity=request.severity,
            payout_rate=request.severity_rate,
            affected_zone=request.affected_zone,
            trigger_data={"source": "admin_simulation", "auto_seeded": True},
            event_start=now,
            event_end=event_end_time,
            processing_status="processed"
        )
        db.add(event)
        await db.flush()  # to get event.id
        
        logger.info(f"Created disruption event ID: {event.id}")

        # 2. Find all eligible riders in the zone with active policies.
        rider_stmt = select(Rider).where(
            or_(
                Rider.zone1_id == request.affected_zone,
                Rider.zone2_id == request.affected_zone,
                Rider.zone3_id == request.affected_zone
            )
        )
        rider_result = await db.execute(rider_stmt)
        riders = rider_result.scalars().all()
        
        logger.info(f"Found {len(riders)} riders in zone {request.affected_zone}")

        eligible_claim_inputs = []

        for r in riders:
            # Check active policy
            pol_stmt = select(Policy).where(
                and_(
                    Policy.rider_id == r.id,
                    Policy.status == "active",
                    Policy.cycle_end_date >= date.today()
                )
            )
            pol_result = await db.execute(pol_stmt)
            policy = pol_result.scalar_one_or_none()

            if not policy:
                logger.debug(f"Rider {r.id} has no active policy")
                continue

            # Check coverage trigger
            if not _event_is_covered(policy.tier, request.event_type):
                logger.debug(f"Policy {policy.id} tier {policy.tier} doesn't cover {request.event_type}")
                continue

            rate = float(r.baseline_hourly_rate) if r.baseline_hourly_rate else 100.0
            calculated = request.lost_hours * rate * request.severity_rate
            cap = float(policy.weekly_payout_cap)
            final_amt = min(calculated, cap)
            # Global max constraint
            final_amt = min(final_amt, 5000.0)

            eligible_claim_inputs.append(
                {
                    "rider": r,
                    "policy": policy,
                    "rate": rate,
                    "calculated": calculated,
                    "final_amt": final_amt,
                }
            )

        logger.info(f"Found {len(eligible_claim_inputs)} eligible claims")

        created_claims = 0
        total_payout_calculated = 0.0
        payout_records_created = 0
        workers_impacted = 0

        # All claims start as "pending" to show up in the claims queue
        # Admin can then approve/reject them manually
        for idx, item in enumerate(eligible_claim_inputs):
            r = item["rider"]
            policy = item["policy"]
            rate = item["rate"]
            calculated = item["calculated"]
            final_amt = item["final_amt"]

            claim = Claim(
                rider_id=r.id,
                policy_id=policy.id,
                disruption_event_id=event.id,
                gate_results={"simulation": True, "auto_seeded": True},
                is_eligible=True,
                lost_hours=request.lost_hours,
                hourly_rate=rate,
                severity_rate=request.severity_rate,
                calculated_payout=calculated,
                final_payout=final_amt,
                status="pending"  # All simulation claims start as pending
            )
            db.add(claim)
            await db.flush()
            created_claims += 1
            workers_impacted += 1
            total_payout_calculated += final_amt

            logger.info(f"Created claim {claim.id} for rider {r.id} (policy tier: {policy.tier}) - Status: pending")

        await db.commit()
        
        logger.info(f"Disaster simulation complete: {created_claims} claims, {payout_records_created} payouts")

        return {
            "message": "Disaster simulation complete",
            "event_id": event.id,
            "workers_impacted": workers_impacted,
            "claims_created": created_claims,
            "payouts_created": payout_records_created,
            "total_payout_estimated": round(total_payout_calculated, 2)
        }
    except Exception as e:
        logger.error(f"Disaster simulation failed: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Disaster simulation failed: {str(e)}"
        )

class OverrideClaimRequest(BaseModel):
    status: str
    final_payout: Optional[float] = None

@router.patch("/claims/{claim_id}/override", dependencies=[Depends(require_admin)])
async def override_claim(
    claim_id: int,
    request: OverrideClaimRequest,
    db: AsyncSession = Depends(get_db),
):
    if request.status not in ("approved", "rejected", "paid", "failed"):
        raise HTTPException(status_code=400, detail="Invalid claim status")

    result = await db.execute(select(Claim).where(Claim.id == claim_id))
    claim = result.scalar_one_or_none()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    if request.final_payout is not None:
        if request.final_payout < 0 or request.final_payout > 5000:
            raise HTTPException(status_code=400, detail="final_payout must be between 0 and 5000")
        claim.final_payout = request.final_payout
    elif request.status in ("approved", "paid") and claim.final_payout is None:
        claim.final_payout = claim.calculated_payout or 0

    if request.status == "rejected":
        claim.is_eligible = False
        if not claim.ineligibility_reason:
            claim.ineligibility_reason = "Rejected by admin override"

    if request.status in ("approved", "paid"):
        claim.is_eligible = True
        claim.ineligibility_reason = None

    claim.status = request.status

    if request.status == "paid":
        now_override = datetime.now(timezone.utc)
        payout_result = await db.execute(
            select(Payout).where(Payout.claim_id == claim.id).order_by(Payout.id.desc())
        )
        payout = payout_result.scalar_one_or_none()

        if payout is None:
            payout = Payout(
                claim_id=claim.id,
                rider_id=claim.rider_id,
                amount=claim.final_payout or 0,
                gateway="manual",
                gateway_reference=f"ADMIN-CLAIM-{claim.id}",
                gateway_response={"source": "admin_override"},
                status="success",
                initiated_at=now_override,  # Explicitly set to avoid constraint violation
                completed_at=now_override,
            )
            db.add(payout)
        else:
            payout.amount = claim.final_payout or payout.amount
            payout.gateway = "manual"
            payout.gateway_reference = payout.gateway_reference or f"ADMIN-CLAIM-{claim.id}"
            payout.gateway_response = {"source": "admin_override"}
            payout.status = "success"
            payout.completed_at = now_override

    await db.commit()
    await db.refresh(claim)

    return {
        "message": "Claim overridden successfully",
        "claim_id": claim.id,
        "claim": claim.to_dict(),
    }
