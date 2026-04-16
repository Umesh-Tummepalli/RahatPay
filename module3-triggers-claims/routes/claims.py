from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.connection import get_db
from models.policy import Claim, DisruptionEvent, Payout


router = APIRouter(prefix="/api/claims", tags=["Claims"])


@router.get("/rider/{rider_id}")
async def get_rider_claims(rider_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Claim).where(Claim.rider_id == rider_id).order_by(Claim.created_at.desc())
    )
    claims = result.scalars().all()

    payload = []
    for claim in claims:
        event_result = await db.execute(
            select(DisruptionEvent).where(DisruptionEvent.id == claim.disruption_event_id)
        )
        payout_result = await db.execute(
            select(Payout).where(Payout.claim_id == claim.id).order_by(Payout.id.desc())
        )
        event = event_result.scalar_one_or_none()
        payout = payout_result.scalar_one_or_none()
        payload.append(
            {
                **claim.to_dict(),
                "event": {
                    "event_type": event.event_type if event else None,
                    "severity": event.severity if event else None,
                    "affected_zone": event.affected_zone if event else None,
                    "event_start": event.event_start.isoformat() if event and event.event_start else None,
                    "event_end": event.event_end.isoformat() if event and event.event_end else None,
                },
                "payout": payout.to_dict() if payout else None,
            }
        )

    return {"rider_id": rider_id, "claims": payload, "count": len(payload)}


@router.get("/{claim_id}")
async def get_claim_detail(claim_id: int, db: AsyncSession = Depends(get_db)):
    claim_result = await db.execute(select(Claim).where(Claim.id == claim_id))
    claim = claim_result.scalar_one_or_none()
    if claim is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found")

    event_result = await db.execute(
        select(DisruptionEvent).where(DisruptionEvent.id == claim.disruption_event_id)
    )
    payout_result = await db.execute(
        select(Payout).where(Payout.claim_id == claim.id).order_by(Payout.id.desc())
    )
    event = event_result.scalar_one_or_none()
    payout = payout_result.scalar_one_or_none()

    return {
        **claim.to_dict(),
        "event": {
            "event_type": event.event_type if event else None,
            "severity": event.severity if event else None,
            "affected_zone": event.affected_zone if event else None,
            "event_start": event.event_start.isoformat() if event and event.event_start else None,
            "event_end": event.event_end.isoformat() if event and event.event_end else None,
            "processing_status": event.processing_status if event else None,
        },
        "payout": payout.to_dict() if payout else None,
    }
