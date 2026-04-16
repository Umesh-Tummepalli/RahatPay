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
from claims.processor import process_disruption_claims

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
    """Fetch pending and in-review claims with policy tier information."""
    stmt = (
        select(Claim, Policy)
        .join(Policy, Policy.id == Claim.policy_id)
        .where(Claim.status.in_(["pending", "in_review"]))
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
            processing_status="pending"
        )
        db.add(event)
        await db.flush()  # to get event.id
        
        logger.info(f"Created disruption event ID: {event.id}")
        result = await process_disruption_claims(event.id, db)
        await db.commit()

        return {
            "message": "Disaster simulation complete",
            "event_id": event.id,
            "workers_impacted": result.get("total_affected", 0),
            "claims_created": len(result.get("claims", [])),
            "payouts_created": 0,
            "total_payout_estimated": result.get("total_payout", 0.0),
            "processor_summary": result,
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
