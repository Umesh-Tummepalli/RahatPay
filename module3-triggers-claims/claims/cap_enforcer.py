from __future__ import annotations

from datetime import datetime, timezone, timedelta

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.policy import Claim


_TIER_CAP_PERCENT = {
    "kavach": 0.35,
    "suraksha": 0.55,
    "raksha": 0.70,
}


def _week_start_utc(dt: datetime | None = None) -> datetime:
    now = dt or datetime.now(timezone.utc)
    # Monday = 0
    delta_days = now.weekday()
    monday = (now - timedelta(days=delta_days)).replace(hour=0, minute=0, second=0, microsecond=0)
    return monday


async def enforce_cap(
    gross_payout: float,
    tier: str,
    baseline_income: float,
    rider_id: int,
    db_session: AsyncSession,
) -> dict:
    tier_pct = _TIER_CAP_PERCENT.get((tier or "").lower(), 0.35)
    weekly_cap = max(0.0, float(baseline_income or 0.0) * tier_pct)

    stmt = select(func.coalesce(func.sum(Claim.final_payout), 0)).where(
        Claim.rider_id == rider_id,
        Claim.created_at >= _week_start_utc(),
        Claim.status.in_(["approved", "paid"]),
    )
    res = await db_session.execute(stmt)
    already_paid = float(res.scalar() or 0.0)

    remaining_headroom = max(0.0, weekly_cap - already_paid)
    final_payout = min(float(gross_payout or 0.0), remaining_headroom)
    final_payout = max(0.0, final_payout)
    final_payout = min(5000.0, final_payout)  # DB safety ceiling mirror

    return {
        "weekly_cap": round(weekly_cap, 2),
        "already_paid": round(already_paid, 2),
        "remaining_headroom": round(remaining_headroom, 2),
        "final_payout": round(final_payout, 2),
        "was_capped": final_payout < float(gross_payout or 0.0),
    }

