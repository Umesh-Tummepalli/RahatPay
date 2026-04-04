"""
profiler.py

Rolling Baseline Profiler — the single source of truth for:
  - A rider's baseline weekly income (used in premium calculation)
  - A rider's hourly rate (used in payout calculation by Module 3)
  - A rider's top 3 delivery zones (used in eligibility checking by Module 3)

Two modes:
  SEASONING (< 2 weeks of real data): returns city-level median from CITY_MEDIANS.
  ESTABLISHED (>= 2 weeks of data):  calculates true rolling 4-week averages.

Integration note:
  Currently reads from dummy_db.py.
  On integration day: replace the `import dummy_db` block with real DB queries.
  Function signatures do NOT change — Module 1 and Module 3 call these the same way.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import dummy_db as db
from collections import Counter


# ── City-level medians (provisional baseline during seasoning) ─────────────────
# Source: published gig economy reports (Swiggy/Zomato economic surveys, 2023-24)
CITY_MEDIANS: dict[str, dict] = {
    "chennai":   {"weekly_income": 3000, "weekly_hours": 50},
    "mumbai":    {"weekly_income": 3500, "weekly_hours": 50},
    "bangalore": {"weekly_income": 3200, "weekly_hours": 48},
    "delhi":     {"weekly_income": 2800, "weekly_hours": 45},
    "pune":      {"weekly_income": 3000, "weekly_hours": 50},
    "hyderabad": {"weekly_income": 2900, "weekly_hours": 48},
    "kolkata":   {"weekly_income": 2600, "weekly_hours": 46},
}

_NATIONAL_MEDIAN = {"weekly_income": 3000, "weekly_hours": 48}
SEASONING_WEEKS = 2   # weeks before personal data replaces city median


def get_baseline(rider_id: int) -> dict:
    """
    Main entry point. Returns the rider's baseline profile.

    Args:
        rider_id: Integer rider ID

    Returns:
        {
            "rider_id": 101,
            "weekly_income": 3500.0,
            "weekly_hours": 50.0,
            "hourly_rate": 70.0,
            "top_3_zones": ["600017", "600020", "600032"],
            "source": "rolling_4week"   or   "city_median_chennai"
        }

    Raises:
        ValueError: if rider_id not found in database
    """
    rider = db.get_rider(rider_id)
    if not rider:
        raise ValueError(f"Rider {rider_id} not found in database")

    city = rider["city"]

    # --- Seasoning check ---
    if not rider["seasoning_complete"]:
        return _city_median_baseline(rider_id, city)

    # --- Real rolling calculation ---
    history = db.get_activity_history(rider_id, last_n_weeks=4)
    if len(history) < SEASONING_WEEKS:
        return _city_median_baseline(rider_id, city)

    return _calculate_rolling_baseline(rider_id, history)


def _calculate_rolling_baseline(rider_id: int, history: list) -> dict:
    """
    Calculates true 4-week rolling averages from activity records.
    """
    total_income = sum(w["earnings"] for w in history)
    total_hours = sum(w["hours_worked"] for w in history)
    n_weeks = len(history)

    avg_income = total_income / n_weeks
    avg_hours = total_hours / n_weeks
    hourly_rate = avg_income / avg_hours if avg_hours > 0 else 0.0

    top_3 = _get_top_3_zones(history)

    return {
        "rider_id": rider_id,
        "weekly_income": round(avg_income, 2),
        "weekly_hours": round(avg_hours, 2),
        "hourly_rate": round(hourly_rate, 2),
        "top_3_zones": top_3,
        "weeks_used": n_weeks,
        "source": "rolling_4week",
    }


def _city_median_baseline(rider_id: int, city: str) -> dict:
    """
    Returns city-level median as provisional baseline during seasoning.
    """
    median = CITY_MEDIANS.get(city.lower(), _NATIONAL_MEDIAN)
    weekly_income = median["weekly_income"]
    weekly_hours = median["weekly_hours"]
    hourly_rate = weekly_income / weekly_hours

    # For seasoning riders, we don't have zone history yet.
    # Return empty list — Module 3 should use city-level zone defaults.
    return {
        "rider_id": rider_id,
        "weekly_income": float(weekly_income),
        "weekly_hours": float(weekly_hours),
        "hourly_rate": round(hourly_rate, 2),
        "top_3_zones": [],
        "weeks_used": 0,
        "source": f"city_median_{city.lower()}",
    }


def _get_top_3_zones(history: list) -> list[str]:
    """
    Identifies the top 3 most-visited zones from activity history.

    Strategy: Count zone appearances across all weeks.
    The zone that appears in the most weeks is ranked first.
    Ties broken by recency (earlier week_number = more recent = higher rank).
    """
    zone_counter: Counter = Counter()
    for week in history:
        for zone in week.get("zones_visited", []):
            zone_counter[zone] += 1

    # Get top 3 by frequency
    top = [zone for zone, _ in zone_counter.most_common(3)]
    return top


# ── Convenience function for Module 3 ────────────────────────────────────────

def get_hourly_rate(rider_id: int) -> float:
    """
    Quick accessor for Module 3's payout calculator.
    Returns the rider's hourly rate (₹/hour).
    """
    baseline = get_baseline(rider_id)
    return baseline["hourly_rate"]


def get_top_zones(rider_id: int) -> list[str]:
    """
    Quick accessor for Module 3's eligibility validator.
    Returns the rider's top 3 delivery zones as a list of pin codes.
    """
    baseline = get_baseline(rider_id)
    return baseline["top_3_zones"]