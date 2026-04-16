from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.policy import Claim


TIER_CAP_PERCENT = {
    "kavach": 0.35,
    "suraksha": 0.55,
    "raksha": 0.70,
}


async def enforce_cap(
    gross_payout: float,
    tier: str,
    baseline_income: float,
    rider_id: int,
    db_session: AsyncSession,
    policy_weekly_cap: float | None = None,
    as_of: datetime | None = None,
) -> dict:
    now = as_of or datetime.now(timezone.utc)
    week_start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)

    result = await db_session.execute(
        select(func.coalesce(func.sum(Claim.final_payout), 0)).where(
            and_(
                Claim.rider_id == rider_id,
                Claim.created_at >= week_start,
                Claim.status.in_(["approved", "paid"]),
            )
        )
    )
    already_paid = float(result.scalar_one() or 0.0)

    dynamic_cap = round(float(baseline_income or 0.0) * TIER_CAP_PERCENT.get(tier, 0.35), 2)
    weekly_cap = dynamic_cap
    if policy_weekly_cap is not None:
        weekly_cap = min(dynamic_cap, float(policy_weekly_cap))

    remaining_headroom = max(0.0, round(weekly_cap - already_paid, 2))
    final_payout = min(float(gross_payout), remaining_headroom, 5000.0)
    final_payout = max(0.0, round(final_payout, 2))

    return {
        "weekly_cap": round(weekly_cap, 2),
        "already_paid": round(already_paid, 2),
        "remaining_headroom": round(remaining_headroom, 2),
        "final_payout": final_payout,
        "was_capped": round(final_payout, 2) < round(float(gross_payout), 2),
        "dynamic_cap": dynamic_cap,
        "policy_cap": float(policy_weekly_cap) if policy_weekly_cap is not None else None,
    }
