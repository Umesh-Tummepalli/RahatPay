"""
integrations/module2_adapter.py
--------------------------------
Integration point with Module 2 (AI Risk Engine & Premium Calculator).

Module 1 calls Module 2 DIRECTLY (same process, function import) — NOT via HTTP.
This adapter:
  - Tries to import from the actual module2 package
  - Falls back to mock implementations when MODULE2_MOCK_MODE=True or import fails

Functions exposed:
  - get_baseline(rider_id, city, is_seasoning) → BaselineResult
  - calculate_premium(income, tier, zones, month) → PremiumResult
"""

from __future__ import annotations
import logging
from dataclasses import dataclass
from typing import Optional
from datetime import datetime

from config import settings, TIER_CONFIG, SEASONAL_FACTORS, CITY_MEDIAN_INCOME, CITY_MEDIAN_HOURS

logger = logging.getLogger(__name__)


# ── Data classes (shared contract between Module 1 and Module 2) ───────────────

@dataclass
class BaselineResult:
    income: float
    hours: float
    hourly_rate: float
    is_provisional: bool    # True when using city-median fallback


@dataclass
class PremiumBreakdown:
    income: float
    tier_rate: float
    zone_risk: float
    seasonal_factor: float
    raw_premium: float
    floor_applied: bool
    cap_applied: bool
    final_premium: float


@dataclass
class PremiumResult:
    weekly_premium: float
    breakdown: PremiumBreakdown


# ── Attempt real Module 2 import ──────────────────────────────────────────────

_module2_available = False

if not settings.MODULE2_MOCK_MODE:
    try:
        # Module 2 lives at ../../module2-risk-engine in the monorepo
        # Adjust sys.path if running as subprocess; in docker-compose they
        # share a volume mount. The import path below matches the tree structure.
        import sys, os
        sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../module2-risk-engine')))

        from baseline.profiler import get_baseline as _m2_get_baseline          # noqa: E402
        from premium.calculator import calculate_premium as _m2_calculate_premium  # noqa: E402

        _module2_available = True
        logger.info("Module 2 loaded successfully (real implementation).")
    except ImportError as e:
        logger.warning(
            f"Module 2 not available ({e}). Falling back to mock implementation. "
            "Set MODULE2_MOCK_MODE=True to suppress this warning."
        )


# ── Public interface ──────────────────────────────────────────────────────────

async def get_baseline(
    rider_id: str,
    city: str,
    is_seasoning: bool,
) -> BaselineResult:
    """
    Returns the rider's 4-week rolling baseline, or city-level median
    if the rider is in their seasoning period (< 4 weeks old).

    Delegates to Module 2's profiler when available.
    """
    if _module2_available:
        try:
            result = await _m2_get_baseline(rider_id, city, is_seasoning)
            return BaselineResult(
                income=result["income"],
                hours=result["hours"],
                hourly_rate=result["hourly_rate"],
                is_provisional=result.get("is_provisional", is_seasoning),
            )
        except Exception as e:
            logger.error(f"Module 2 get_baseline failed for rider {rider_id}: {e}")
            # Fall through to mock

    # ── Mock / provisional fallback ───────────────────────────────────────────
    return _mock_get_baseline(city, is_seasoning)


async def calculate_premium(
    income: float,
    tier: str,
    zones: list[int],
    month: Optional[int] = None,
) -> PremiumResult:
    """
    Calculates weekly premium using the formula:
        income × tier_rate × zone_risk × seasonal_factor
    Applies ₹15 floor and 3.5% income cap.

    Delegates to Module 2's calculator when available.
    """
    if _module2_available:
        try:
            result = await _m2_calculate_premium(income, tier, zones, month)
            bd = result["breakdown"]
            breakdown = PremiumBreakdown(
                income=bd["income"],
                tier_rate=bd["tier_rate"],
                zone_risk=bd["zone_risk"],
                seasonal_factor=bd["seasonal_factor"],
                raw_premium=bd["raw_premium"],
                floor_applied=bd["floor_applied"],
                cap_applied=bd["cap_applied"],
                final_premium=result["weekly_premium"],
            )
            return PremiumResult(
                weekly_premium=result["weekly_premium"],
                breakdown=breakdown,
            )
        except Exception as e:
            logger.error(f"Module 2 calculate_premium failed: {e}")
            # Fall through to mock

    return _mock_calculate_premium(income, tier, zones, month)


# ── Mock implementations ──────────────────────────────────────────────────────

# Zone risk table — mirrors Module 2's XGBoost output for known pincodes.
# Module 5 seed data provides these values.
_ZONE_RISK_TABLE: dict[int, float] = {
    1: 1.20, 2: 1.15, 3: 1.10,
    4: 1.05, 5: 1.00, 6: 0.95,
    7: 1.25, 8: 1.10,
    9: 1.30, 10: 1.20, 11: 1.15, 12: 1.35,
    13: 1.00, 14: 1.05, 15: 1.10, 16: 1.08,
    17: 1.25, 18: 1.15, 19: 1.40, 20: 1.35,
}


def _mock_get_baseline(city: str, is_seasoning: bool) -> BaselineResult:
    """City-level median used as provisional baseline during seasoning."""
    city_key = city.strip().title()
    income = CITY_MEDIAN_INCOME.get(city_key, 3500.00)
    hours  = CITY_MEDIAN_HOURS.get(city_key, 40.0)
    return BaselineResult(
        income=income,
        hours=hours,
        hourly_rate=round(income / hours, 2) if hours > 0 else 0.0,
        is_provisional=True,
    )


def _mock_calculate_premium(
    income: float,
    tier: str,
    zones: list[int],
    month: Optional[int],
) -> PremiumResult:
    """
    Full premium formula:
        raw = income × tier_rate × zone_risk × seasonal_factor
        premium = max(raw, FLOOR) capped at 3.5% of income
    """
    tier_cfg = TIER_CONFIG.get(tier)
    if not tier_cfg:
        raise ValueError(f"Unknown tier: {tier}")

    tier_rate = tier_cfg["tier_rate"]

    # Average zone risk across all rider zones
    risks = [_ZONE_RISK_TABLE.get(z, 1.0) for z in zones if z]
    zone_risk = round(sum(risks) / len(risks), 4) if risks else 1.0

    # Seasonal factor from current month
    current_month = month or datetime.now().month
    seasonal_factor = SEASONAL_FACTORS.get(current_month, 1.0)

    # Core formula
    raw_premium = income * tier_rate * zone_risk * seasonal_factor

    # Apply floor: ₹15 minimum
    floor_applied = raw_premium < settings.PREMIUM_FLOOR
    if floor_applied:
        raw_premium = settings.PREMIUM_FLOOR

    # Apply cap: 3.5% of income
    cap_amount = income * settings.PREMIUM_CAP_PERCENT
    cap_applied = (income > 0) and (raw_premium > cap_amount)
    final_premium = min(raw_premium, cap_amount) if cap_applied else raw_premium
    # Floor must always win over cap
    final_premium = max(final_premium, settings.PREMIUM_FLOOR)
    final_premium = round(final_premium, 2)

    breakdown = PremiumBreakdown(
        income=income,
        tier_rate=tier_rate,
        zone_risk=zone_risk,
        seasonal_factor=seasonal_factor,
        raw_premium=raw_premium,
        floor_applied=floor_applied,
        cap_applied=cap_applied,
        final_premium=final_premium,
    )

    return PremiumResult(
        weekly_premium=final_premium,
        breakdown=breakdown,
    )
