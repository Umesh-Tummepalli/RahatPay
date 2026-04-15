from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from db.connection import get_db
from models.policy import Claim

router = APIRouter(prefix="/api/claims", tags=["Claims"])


@router.get("/rider/{rider_id}")
async def get_rider_claims(rider_id: int, db: AsyncSession = Depends(get_db)):
    stmt = (
        select(Claim)
        .where(Claim.rider_id == rider_id)
        .order_by(desc(Claim.created_at))
        .limit(200)
    )
    res = await db.execute(stmt)
    claims = res.scalars().all()
    return {"rider_id": rider_id, "count": len(claims), "claims": [c.to_dict() for c in claims]}


@router.get("/{claim_id}")
async def get_claim_detail(claim_id: int, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Claim).where(Claim.id == claim_id))
    claim = res.scalar_one_or_none()
    if claim is None:
        raise HTTPException(status_code=404, detail="Claim not found")
    return claim.to_dict()

