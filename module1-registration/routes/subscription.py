"""
routes/subscription.py
----------------------
Trial/subscription lifecycle endpoints for the rider-facing app.
"""

from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from config import TIER_CONFIG
from db.connection import get_db
from models.policy import Policy
from models.rider import Rider
from services.subscription_state import (
    build_premium_quotes,
    ensure_subscription_state,
    get_active_paid_policy,
    notification_is_unread,
    serialize_subscription_state,
    sync_subscription_phase,
    utcnow,
)

router = APIRouter(tags=["Subscription State"])


async def _get_rider_or_404(rider_id: int, db: AsyncSession) -> Rider:
    result = await db.execute(select(Rider).where(Rider.id == rider_id))
    rider = result.scalar_one_or_none()
    if rider is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rider not found.")
    return rider


@router.get(
    "/rider/{rider_id}/subscription-state",
    summary="Get rider subscription state",
    description="Returns trial lifecycle, notification state, and per-tier dynamic premium options.",
)
async def get_subscription_state(
    rider_id: int,
    db: AsyncSession = Depends(get_db),
):
    rider = await _get_rider_or_404(rider_id, db)
    active_policy = await get_active_paid_policy(db, rider.id)
    subscription_state = await ensure_subscription_state(db, rider, active_policy=active_policy)
    sync_subscription_phase(subscription_state, active_policy=active_policy)
    return serialize_subscription_state(rider, subscription_state, active_policy=active_policy)


@router.post(
    "/rider/{rider_id}/subscription-state/ack-notification",
    summary="Acknowledge rider subscription notification",
)
async def acknowledge_subscription_notification(
    rider_id: int,
    db: AsyncSession = Depends(get_db),
):
    rider = await _get_rider_or_404(rider_id, db)
    active_policy = await get_active_paid_policy(db, rider.id)
    subscription_state = await ensure_subscription_state(db, rider, active_policy=active_policy)

    if subscription_state.last_notified_at and notification_is_unread(subscription_state):
        subscription_state.notification_seen_at = utcnow()
        await db.commit()
        await db.refresh(subscription_state)

    return {
        "rider_id": rider.id,
        "notification_unread": notification_is_unread(subscription_state),
        "notification_seen_at": subscription_state.notification_seen_at.isoformat()
        if subscription_state.notification_seen_at
        else None,
    }


class ActivatePlanResponse(BaseModel):
    rider_id: int
    policy_id: int
    tier: str
    weekly_premium: float
    weekly_payout_cap: float
    cycle_start_date: str
    cycle_end_date: str
    phase: str
    message: str


@router.post(
    "/rider/{rider_id}/plans/{tier}/activate",
    response_model=ActivatePlanResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Activate a quoted plan",
    description="Creates a paid policy using the latest stored dynamic quote for the requested tier.",
)
async def activate_plan(
    rider_id: int,
    tier: str,
    db: AsyncSession = Depends(get_db),
):
    tier_key = tier.lower().strip()
    if tier_key not in TIER_CONFIG:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid tier '{tier}'. Must be one of: {list(TIER_CONFIG.keys())}",
        )

    rider = await _get_rider_or_404(rider_id, db)
    active_policy = await get_active_paid_policy(db, rider.id)
    if active_policy is not None:
        active_policy.status = "expired"

    subscription_state = await ensure_subscription_state(db, rider, active_policy=None)
    if not subscription_state.premium_quotes:
        subscription_state.premium_quotes = await build_premium_quotes(db, rider)
        subscription_state.last_quotes_at = utcnow()

    quote = (subscription_state.premium_quotes or {}).get(tier_key)
    if not quote:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No premium quote available for this rider yet. Generate earnings data first.",
        )

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

    rider.tier = tier_key
    cycle_start = date.today()
    cycle_end = cycle_start + timedelta(days=28)
    policy = Policy(
        rider_id=rider.id,
        tier=tier_key,
        weekly_premium=float(quote["weekly_premium"]),
        premium_breakdown=quote["premium_breakdown"],
        weekly_payout_cap=float(quote["weekly_payout_cap"]),
        coverage_type=quote["coverage_type"],
        status="active",
        cycle_start_date=cycle_start,
        cycle_end_date=cycle_end,
    )
    db.add(policy)
    await db.flush()

    subscription_state.phase = "paid_active"
    if subscription_state.last_notified_at and subscription_state.notification_seen_at is None:
        subscription_state.notification_seen_at = utcnow()

    await db.commit()
    await db.refresh(policy)

    return ActivatePlanResponse(
        rider_id=rider.id,
        policy_id=policy.id,
        tier=tier_key,
        weekly_premium=float(policy.weekly_premium),
        weekly_payout_cap=float(policy.weekly_payout_cap),
        cycle_start_date=policy.cycle_start_date.isoformat(),
        cycle_end_date=policy.cycle_end_date.isoformat(),
        phase=subscription_state.phase,
        message=f"{TIER_CONFIG[tier_key]['display_name']} is now active.",
    )
