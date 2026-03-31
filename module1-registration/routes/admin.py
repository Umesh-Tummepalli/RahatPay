"""
routes/admin.py
---------------
Admin API Layer for worker management, fraud monitoring, and financial overview.
"""

from typing import Optional, List, Any
import logging
from datetime import date

from fastapi import APIRouter, HTTPException, status, Depends, Header, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload

from db.connection import get_db
from models.rider import Rider, Zone
from models.policy import Policy, Claim, Payout, DisruptionEvent
from config import TIER_CONFIG, settings

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
    
    return [w.to_dict() for w in workers]


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
    
    worker_data = worker.to_dict()
    worker_data["active_policy"] = policy.to_dict() if policy else None
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


# ── 2. Claims & Payouts ───────────────────────────────────────────────────────

@router.get("/claims/live", dependencies=[Depends(require_admin)])
async def get_live_claims(db: AsyncSession = Depends(get_db)):
    """Fetch pending claims logic."""
    stmt = select(Claim).where(Claim.status == 'pending').order_by(Claim.created_at.desc()).limit(100)
    result = await db.execute(stmt)
    return [c.to_dict() for c in result.scalars().all()]


@router.get("/claims/{rider_id}", dependencies=[Depends(require_admin)])
async def get_rider_claims(rider_id: int, db: AsyncSession = Depends(get_db)):
    stmt = select(Claim).where(Claim.rider_id == rider_id).order_by(Claim.created_at.desc())
    result = await db.execute(stmt)
    return [c.to_dict() for c in result.scalars().all()]


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
        
    claim.status = request.status
    if request.final_payout is not None:
        claim.final_payout = request.final_payout
    await db.commit()
    return {"message": "Claim overridden successfully", "claim_id": claim.id}


@router.get("/payouts", dependencies=[Depends(require_admin)])
async def get_all_payouts(limit: int = 50, offset: int = 0, db: AsyncSession = Depends(get_db)):
    stmt = select(Payout).order_by(Payout.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(stmt)
    return [p.to_dict() for p in result.scalars().all()]


# ── 3. Fraud Monitoring ───────────────────────────────────────────────────────

@router.get("/fraud/flagged", dependencies=[Depends(require_admin)])
async def get_fraud_flagged():
    """Returns structured mock data representing users flagged for potential fraud."""
    return {
        "flagged_users": [
            {
                "rider_id": 12,
                "reason": "High claim frequency across multiple adjacent bins",
                "risk_score": 0.92,
                "flagged_at": "2026-03-31T10:00:00Z"
            },
            {
                "rider_id": 45,
                "reason": "Suspicious baseline spike post-registration",
                "risk_score": 0.85,
                "flagged_at": "2026-03-31T09:15:00Z"
            }
        ]
    }


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
    return [z.to_dict() for z in result.scalars().all()]


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
