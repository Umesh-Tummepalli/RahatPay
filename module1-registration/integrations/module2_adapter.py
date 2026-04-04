"""
integrations/module2_adapter.py
--------------------------------
Integration point with Module 2 (AI Risk Engine & Premium Calculator).

Module 1 calls Module 2 over HTTP (REST API).
This adapter:
  - Makes async HTTP requests to http://localhost:8002/evaluate
  - Connects strictly through strict API contracts.

Functions exposed:
  - get_baseline(rider_id, city, is_seasoning) → BaselineResult
  - calculate_premium(income, tier, zones, month) → PremiumResult
"""

from __future__ import annotations
import logging
from dataclasses import dataclass
from typing import Optional
import httpx

from config import settings

logger = logging.getLogger(__name__)
MODULE_2_URL = "http://localhost:8002"

# ── Data classes (shared contract between Module 1 and Module 2) ───────────────

@dataclass
class BaselineResult:
    income: float
    hours: float
    hourly_rate: float
    is_provisional: bool

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

# ── Public interface ──────────────────────────────────────────────────────────

async def get_baseline(
    rider_id: str,
    city: str,
    is_seasoning: bool,
) -> BaselineResult:
    """
    Returns the rider's 4-week rolling baseline, or city-level median
    if the rider is in their seasoning period (< 4 weeks old) directly from Module 2 API.
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{MODULE_2_URL}/evaluate/baseline",
                json={
                    "rider_id": str(rider_id),
                    "city": city,
                    "is_seasoning": is_seasoning
                },
                timeout=5.0
            )
            response.raise_for_status()
            data = response.json()
            
            return BaselineResult(
                income=data["income"],
                hours=data["hours"],
                hourly_rate=data["hourly_rate"],
                is_provisional=data["is_provisional"],
            )
    except httpx.RequestError as e:
        logger.error(f"Module 2 get_baseline network error for rider {rider_id}: {e}")
        raise
    except httpx.HTTPStatusError as e:
        logger.error(f"Module 2 get_baseline HTTP {e.response.status_code}")
        raise

async def calculate_premium(
    income: float,
    tier: str,
    zones: list[int],
    month: Optional[int] = None,
) -> PremiumResult:
    """
    Calculates weekly premium via Module 2 API.
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{MODULE_2_URL}/evaluate/premium",
                json={
                    "income": income,
                    "tier": tier,
                    "zones": zones,
                    "month": month
                },
                timeout=5.0
            )
            response.raise_for_status()
            data = response.json()
            
            if "error" in data:
                raise ValueError(data["error"])
                
            bd = data["breakdown"]
            breakdown = PremiumBreakdown(
                income=bd["income"],
                tier_rate=bd["tier_rate"],
                zone_risk=bd["zone_risk"],
                seasonal_factor=bd["seasonal_factor"],
                raw_premium=bd["raw_premium"],
                floor_applied=bd["floor_applied"],
                cap_applied=bd["cap_applied"],
                final_premium=bd["final_premium"],
            )
            return PremiumResult(
                weekly_premium=data["weekly_premium"],
                breakdown=breakdown,
            )
    except httpx.RequestError as e:
        logger.error(f"Module 2 calculate_premium network error: {e}")
        raise
    except httpx.HTTPStatusError as e:
        logger.error(f"Module 2 calculate_premium HTTP {e.response.status_code}")
        raise
