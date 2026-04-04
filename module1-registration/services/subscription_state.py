"""
services/subscription_state.py
------------------------------
Shared helpers for trial lifecycle, baseline estimation, and dynamic premium
quotes used by admin and rider-facing APIs.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from math import ceil
from typing import Any

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from config import CITY_MEDIAN_HOURS, CITY_MEDIAN_INCOME, SEASONAL_FACTORS, TIER_CONFIG, settings
from models.policy import Policy
from models.rider import Rider, Zone
from models.subscription import SubscriptionState

TRIAL_DURATION_DAYS = 15
TRIAL_PREMIUM_INR = 100.0
TRIAL_WEEKLY_COVERAGE_INR = 4000.0
TIER_ORDER = ("kavach", "suraksha", "raksha")
RECOMMENDED_TIER = "suraksha"

# ── In-memory pending notification store ──────────────────────────────────────
# Stores attack/disaster notifications keyed by rider_id.
# Written by simulate_attack / simulate_disaster endpoints; cleared on ack.
_pending_event_notifications: dict[int, dict] = {}


def set_event_notification(rider_id: int, notification: dict) -> None:
    """Store a pending event notification for a rider (overwrites previous)."""
    _pending_event_notifications[rider_id] = notification


def get_event_notification(rider_id: int) -> dict | None:
    return _pending_event_notifications.get(rider_id)


def clear_event_notification(rider_id: int) -> None:
    _pending_event_notifications.pop(rider_id, None)


@dataclass
class BaselineSnapshot:
    income: float
    hours: float
    hourly_rate: float
    is_provisional: bool


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def to_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def isoformat(dt: datetime | None) -> str | None:
    normalized = to_utc(dt)
    return normalized.isoformat() if normalized else None


def get_trial_expires_at(trial_started_at: datetime | None) -> datetime:
    started = to_utc(trial_started_at) or utcnow()
    return started + timedelta(days=TRIAL_DURATION_DAYS)


def get_seasonal_factor(month: int | None = None) -> float:
    active_month = month or utcnow().month
    return float(SEASONAL_FACTORS.get(active_month, 1.0))


def get_seasonal_label(factor: float) -> str:
    if factor >= 1.2:
        return "Peak risk season"
    if factor >= 1.05:
        return "Elevated seasonal risk"
    if factor >= 0.95:
        return "Typical seasonal risk"
    return "Lower seasonal risk"


def get_guardrail_message(raw_premium: float, income: float, floor_applied: bool, cap_applied: bool) -> str:
    if income <= 0:
        return "Premium is zero because there is no baseline income yet."
    if floor_applied:
        return f"Minimum weekly floor of Rs. {settings.PREMIUM_FLOOR:.0f} applied."
    if cap_applied:
        cap_amount = income * settings.PREMIUM_CAP_PERCENT
        return (
            f"Premium capped at {settings.PREMIUM_CAP_PERCENT * 100:.1f}% of weekly income "
            f"(Rs. {cap_amount:.2f})."
        )
    return "No affordability guardrail applied."


def get_city_baseline(city: str) -> BaselineSnapshot:
    normalized_city = (city or "").strip().title()
    weekly_income = float(CITY_MEDIAN_INCOME.get(normalized_city, 3500.0))
    weekly_hours = float(CITY_MEDIAN_HOURS.get(normalized_city, 40.0))
    hourly_rate = round(weekly_income / weekly_hours, 2) if weekly_hours > 0 else 0.0
    return BaselineSnapshot(
        income=round(weekly_income, 2),
        hours=round(weekly_hours, 2),
        hourly_rate=hourly_rate,
        is_provisional=True,
    )


def get_history_baseline(daily_history: list[dict[str, Any]] | None) -> BaselineSnapshot | None:
    history = daily_history or []
    if not history:
        return None

    total_income = sum(float(day.get("income") or 0) for day in history)
    total_hours = sum(float(day.get("hours") or 0) for day in history)
    if total_income <= 0 and total_hours <= 0:
        return None

    days = max(len(history), 1)
    weekly_income = round((total_income / days) * 7, 2)
    weekly_hours = round((total_hours / days) * 7, 2)
    hourly_rate = round((weekly_income / weekly_hours), 2) if weekly_hours > 0 else 0.0
    return BaselineSnapshot(
        income=weekly_income,
        hours=weekly_hours,
        hourly_rate=hourly_rate,
        is_provisional=False,
    )


def get_rider_baseline(rider: Rider, is_seasoning: bool | None = None) -> BaselineSnapshot:
    rider_is_seasoning = rider.is_seasoning if is_seasoning is None else is_seasoning
    if not rider_is_seasoning:
        history_baseline = get_history_baseline(rider.daily_income_history)
        if history_baseline:
            return history_baseline
        if rider.baseline_weekly_income is not None and rider.baseline_weekly_hours is not None:
            income = float(rider.baseline_weekly_income)
            hours = float(rider.baseline_weekly_hours)
            return BaselineSnapshot(
                income=round(income, 2),
                hours=round(hours, 2),
                hourly_rate=round((income / hours), 2) if hours > 0 else 0.0,
                is_provisional=False,
            )
    return get_city_baseline(rider.city)


def get_rider_zone_ids(rider: Rider) -> list[int]:
    return [zone_id for zone_id in [rider.zone1_id, rider.zone2_id, rider.zone3_id] if zone_id is not None]


async def get_rider_zone_map(db: AsyncSession, rider: Rider) -> dict[int, Zone]:
    zone_ids = get_rider_zone_ids(rider)
    if not zone_ids:
        return {}
    result = await db.execute(select(Zone).where(Zone.zone_id.in_(zone_ids)))
    return {zone.zone_id: zone for zone in result.scalars().all()}


def calculate_zone_risk(zone_ids: list[int], zone_map: dict[int, Zone]) -> float:
    if not zone_ids:
        return 1.0
    risk_values = [float(zone_map[zone_id].risk_multiplier) for zone_id in zone_ids if zone_id in zone_map]
    if not risk_values:
        return 1.0
    return round(sum(risk_values) / len(risk_values), 4)


def quote_summary_from_quotes(premium_quotes: dict[str, Any] | None) -> dict[str, float]:
    quotes = premium_quotes or {}
    return {
        tier: float(data.get("weekly_premium") or 0.0)
        for tier, data in quotes.items()
        if isinstance(data, dict)
    }


def has_seeded_history(rider: Rider) -> bool:
    return bool(rider.daily_income_history)


def build_premium_quote(
    rider: Rider,
    tier: str,
    zone_map: dict[int, Zone],
    month: int | None = None,
) -> dict[str, Any]:
    baseline = get_rider_baseline(rider, is_seasoning=False)
    income = float(baseline.income)
    tier_cfg = TIER_CONFIG[tier]
    tier_rate = float(tier_cfg["tier_rate"])
    zone_ids = get_rider_zone_ids(rider)
    zone_risk = calculate_zone_risk(zone_ids, zone_map)
    seasonal_factor = get_seasonal_factor(month)
    raw_premium = income * tier_rate * zone_risk * seasonal_factor

    if income > 0:
        raw_with_floor = max(raw_premium, float(settings.PREMIUM_FLOOR))
        cap_amount = income * float(settings.PREMIUM_CAP_PERCENT)
        floor_applied = raw_premium < float(settings.PREMIUM_FLOOR)
        cap_applied = raw_with_floor > cap_amount
        final_premium = round(min(raw_with_floor, cap_amount), 2)
    else:
        floor_applied = False
        cap_applied = False
        cap_amount = 0.0
        final_premium = 0.0

    breakdown = {
        "formula": "Baseline income x tier rate x zone risk x seasonal factor",
        "income": round(income, 2),
        "baseline_income": round(income, 2),
        "weekly_hours": round(float(baseline.hours), 2),
        "hourly_rate": round(float(baseline.hourly_rate), 2),
        "tier": tier,
        "tier_rate": tier_rate,
        "tier_rate_percent": f"{tier_rate * 100:.1f}%",
        "zone_risk": zone_risk,
        "seasonal_factor": seasonal_factor,
        "seasonal_label": get_seasonal_label(seasonal_factor),
        "raw_premium": round(raw_premium, 2),
        "floor_applied": floor_applied,
        "cap_applied": cap_applied,
        "premium_cap_amount": round(cap_amount, 2),
        "premium_cap_percent": f"{settings.PREMIUM_CAP_PERCENT * 100:.1f}%",
        "final_premium": final_premium,
        "guardrail_message": get_guardrail_message(raw_premium, income, floor_applied, cap_applied),
        "quote_generated_at": isoformat(utcnow()),
        "zones": [
            {
                "zone_id": zone.zone_id,
                "area_name": zone.area_name,
                "city": zone.city,
                "risk_multiplier": float(zone.risk_multiplier),
            }
            for zone in zone_map.values()
        ],
    }

    return {
        "tier": tier,
        "display_name": tier_cfg["display_name"],
        "description": tier_cfg["description"],
        "coverage_type": tier_cfg["coverage_type"],
        "coverage_triggers": tier_cfg["coverage_triggers"],
        "weekly_premium": final_premium,
        "weekly_payout_cap": float(tier_cfg["weekly_payout_cap"]),
        "recommended": tier == RECOMMENDED_TIER,
        "premium_breakdown": breakdown,
    }


async def build_premium_quotes(
    db: AsyncSession,
    rider: Rider,
    month: int | None = None,
) -> dict[str, dict[str, Any]]:
    zone_map = await get_rider_zone_map(db, rider)
    quotes: dict[str, dict[str, Any]] = {}
    for tier in TIER_ORDER:
        quotes[tier] = build_premium_quote(rider, tier, zone_map, month=month)
    return quotes


async def get_active_paid_policy(
    db: AsyncSession,
    rider_id: int,
) -> Policy | None:
    result = await db.execute(
        select(Policy).where(
            and_(
                Policy.rider_id == rider_id,
                Policy.status == "active",
                Policy.cycle_end_date >= date.today(),
            )
        )
    )
    return result.scalar_one_or_none()


def sync_subscription_phase(
    subscription_state: SubscriptionState,
    active_policy: Policy | None = None,
    now: datetime | None = None,
) -> str:
    effective_now = now or utcnow()
    if active_policy is not None:
        subscription_state.phase = "paid_active"
        return subscription_state.phase

    if (
        subscription_state.trial_completed_at is not None
        or effective_now >= get_trial_expires_at(subscription_state.trial_started_at)
    ):
        subscription_state.phase = "plan_selection"
    else:
        subscription_state.phase = "trial_active"
    return subscription_state.phase


async def ensure_subscription_state(
    db: AsyncSession,
    rider: Rider,
    active_policy: Policy | None = None,
) -> SubscriptionState:
    result = await db.execute(
        select(SubscriptionState).where(SubscriptionState.rider_id == rider.id)
    )
    subscription_state = result.scalar_one_or_none()

    if subscription_state is None:
        subscription_state = SubscriptionState(
            rider_id=rider.id,
            phase="paid_active" if active_policy is not None else "trial_active",
            trial_started_at=to_utc(rider.created_at) or utcnow(),
            premium_quotes={},
        )
        db.add(subscription_state)
        await db.flush()

    sync_subscription_phase(subscription_state, active_policy=active_policy)
    return subscription_state


def notification_is_unread(subscription_state: SubscriptionState) -> bool:
    if subscription_state.last_notified_at is None:
        return False
    if subscription_state.notification_seen_at is None:
        return True
    return subscription_state.notification_seen_at < subscription_state.last_notified_at


def build_notification_payload(
    subscription_state: SubscriptionState,
    rider_id: int | None = None,
) -> dict[str, Any] | None:
    # Priority 1 — live attack/disaster event notification (unacknowledged)
    if rider_id is not None:
        event_notif = get_event_notification(rider_id)
        if event_notif:
            return event_notif

    # Priority 2 — trial-ended / premium quotes ready
    if not notification_is_unread(subscription_state):
        return None

    quote_summary = quote_summary_from_quotes(subscription_state.premium_quotes)
    preview_tier = RECOMMENDED_TIER if RECOMMENDED_TIER in quote_summary else next(iter(quote_summary), None)
    if preview_tier is None:
        return None

    preview_amount = quote_summary[preview_tier]
    return {
        "type": "trial_ended_quotes_ready",
        "title": "Your trial has ended",
        "body": (
            f"Personalized premiums are ready. "
            f"See {TIER_CONFIG[preview_tier]['name']} from Rs. {preview_amount:.2f} per week."
        ),
        "triggered_at": isoformat(subscription_state.last_notified_at),
        "preview_tier": preview_tier,
        "preview_amount": round(preview_amount, 2),
    }


def serialize_plan_options(subscription_state: SubscriptionState) -> list[dict[str, Any]]:
    quotes = subscription_state.premium_quotes or {}
    return [quotes[tier] for tier in TIER_ORDER if tier in quotes]


def serialize_active_policy(active_policy: Policy | None) -> dict[str, Any] | None:
    if active_policy is None:
        return None
    payload = active_policy.to_dict()
    payload["display_name"] = TIER_CONFIG.get(active_policy.tier, {}).get("display_name", active_policy.tier.title())
    payload["description"] = TIER_CONFIG.get(active_policy.tier, {}).get("description")
    return payload


def build_trial_banner(phase: str, subscription_state: SubscriptionState) -> dict[str, Any]:
    trial_expires_at = get_trial_expires_at(subscription_state.trial_started_at)
    if phase == "paid_active":
        return {
            "variant": "success",
            "title": "Plan active",
            "body": "Your personalized plan is active and backed by the latest premium quote.",
        }
    if phase == "plan_selection":
        if subscription_state.premium_quotes:
            return {
                "variant": "warning",
                "title": "Trial ended",
                "body": "Your dynamic premiums are ready. Compare plans and continue coverage.",
            }
        return {
            "variant": "warning",
            "title": "Trial ended",
            "body": "Your trial period has ended. Premium quotes will appear after earnings data is generated.",
        }
    return {
        "variant": "info",
        "title": "Trial active",
        "body": (
            f"Your 15-day trial is active until "
            f"{trial_expires_at.strftime('%d %b %Y')}."
        ),
    }


def serialize_subscription_state(
    rider: Rider,
    subscription_state: SubscriptionState,
    active_policy: Policy | None = None,
) -> dict[str, Any]:
    current_time = utcnow()
    trial_expires_at = get_trial_expires_at(subscription_state.trial_started_at)
    remaining_seconds = (trial_expires_at - current_time).total_seconds()
    days_remaining = max(0, ceil(remaining_seconds / 86400)) if remaining_seconds > 0 else 0

    return {
        "rider_id": rider.id,
        "phase": subscription_state.phase,
        "trial": {
            "started_at": isoformat(subscription_state.trial_started_at),
            "expires_at": isoformat(trial_expires_at),
            "completed_at": isoformat(subscription_state.trial_completed_at),
            "days_remaining": days_remaining,
            "premium_paid": TRIAL_PREMIUM_INR,
            "weekly_coverage": TRIAL_WEEKLY_COVERAGE_INR,
            "has_seeded_history": has_seeded_history(rider),
            "last_seeded_at": isoformat(subscription_state.last_seeded_at),
        },
        "banner": build_trial_banner(subscription_state.phase, subscription_state),
        "notification": build_notification_payload(subscription_state, rider_id=rider.id),
        "notification_unread": (
            notification_is_unread(subscription_state)
            or get_event_notification(rider.id) is not None
        ),
        "has_seeded_history": has_seeded_history(rider),
        "last_quotes_at": isoformat(subscription_state.last_quotes_at),
        "premium_quotes": subscription_state.premium_quotes or {},
        "plan_options": serialize_plan_options(subscription_state),
        "quote_summary": quote_summary_from_quotes(subscription_state.premium_quotes),
        "current_plan": serialize_active_policy(active_policy),
    }
