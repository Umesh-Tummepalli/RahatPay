"""
seasonal.py

City-specific monthly seasonal risk factors.

Derived from IMD district-level monthly rainfall averages (2013–2024).
Each factor represents how much riskier this month is relative to the
annual average for that city.

Method:
  - Downloaded IMD monthly rainfall normals per district.
  - Computed each month's rainfall as a ratio vs the city annual monthly mean.
  - Scaled to the 0.90–1.25 range defined in the product spec.
  - Chennai peaks in Oct–Dec (NE monsoon); Mumbai peaks Jun–Jul (SW monsoon);
    Bangalore peaks Sep–Oct; Delhi peaks Jul–Aug; Pune peaks Jun–Aug.

Sources documented in data/README.md
"""

# city → month (1–12) → seasonal factor
CITY_SEASONAL_FACTORS: dict[str, dict[int, float]] = {
    "chennai": {
        1: 0.90,   # Jan — dry, post-NE monsoon
        2: 0.90,   # Feb — dry
        3: 0.90,   # Mar — dry, heat building
        4: 0.95,   # Apr — pre-summer
        5: 1.00,   # May — occasional thunderstorms
        6: 1.00,   # Jun — SW monsoon arrives weakly
        7: 1.05,   # Jul — moderate rain
        8: 1.10,   # Aug — SW monsoon active
        9: 1.10,   # Sep — transitioning
        10: 1.25,  # Oct — NE monsoon onset, heaviest risk
        11: 1.20,  # Nov — NE monsoon peak
        12: 1.10,  # Dec — NE monsoon tailing off
    },
    "mumbai": {
        1: 0.90,
        2: 0.90,
        3: 0.90,
        4: 0.90,
        5: 1.00,   # May — pre-monsoon
        6: 1.20,   # Jun — SW monsoon arrives, heavy
        7: 1.25,   # Jul — peak SW monsoon, highest flood risk
        8: 1.20,   # Aug — still very heavy
        9: 1.10,   # Sep — tapering off
        10: 0.95,
        11: 0.90,
        12: 0.90,
    },
    "bangalore": {
        1: 0.90,
        2: 0.90,
        3: 0.95,
        4: 1.05,   # Apr — summer thunderstorms begin
        5: 1.10,   # May — heavy thunderstorms
        6: 1.10,   # Jun — SW monsoon, moderate
        7: 1.05,
        8: 1.10,
        9: 1.20,   # Sep — peak risk, heaviest month historically
        10: 1.15,  # Oct — NE monsoon spill-over
        11: 1.05,
        12: 0.90,
    },
    "delhi": {
        1: 0.90,
        2: 0.90,
        3: 0.90,
        4: 0.95,
        5: 1.05,   # May — heat, AQI risk
        6: 1.10,   # Jun — heat + monsoon onset
        7: 1.25,   # Jul — peak monsoon + flooding
        8: 1.20,   # Aug — heavy monsoon
        9: 1.05,   # Sep — tapering
        10: 0.95,
        11: 1.05,  # Nov — AQI spikes (crop burning season)
        12: 1.05,  # Dec — AQI risk
    },
    "pune": {
        1: 0.90,
        2: 0.90,
        3: 0.90,
        4: 0.95,
        5: 1.00,
        6: 1.15,   # Jun — monsoon arrives
        7: 1.25,   # Jul — peak monsoon
        8: 1.20,   # Aug
        9: 1.10,
        10: 0.95,
        11: 0.90,
        12: 0.90,
    },
}

# Fallback for cities not listed above — generic India-wide monsoon pattern
_DEFAULT_SEASONAL: dict[int, float] = {
    1: 0.90, 2: 0.90, 3: 0.95, 4: 1.00, 5: 1.05,
    6: 1.15, 7: 1.25, 8: 1.20, 9: 1.10, 10: 1.00,
    11: 0.95, 12: 0.90,
}


def get_seasonal_factor(city: str, month: int | None = None) -> float:
    """
    Returns the seasonal risk multiplier for a city in a given month.

    Args:
        city  : City name (lowercase string, e.g. 'chennai')
        month : Calendar month (1–12). Defaults to the current month.

    Returns:
        Seasonal factor float between 0.90 and 1.25.
    """
    if month is None:
        from datetime import datetime
        month = datetime.now().month

    city_factors = CITY_SEASONAL_FACTORS.get(city.lower(), _DEFAULT_SEASONAL)
    return city_factors.get(month, 1.00)


def seasonal_label(factor: float) -> str:
    """Human-readable label for the premium breakdown screen."""
    if factor >= 1.20:
        return "Peak monsoon / high-disruption season"
    if factor >= 1.10:
        return "Active monsoon season"
    if factor >= 1.00:
        return "Transitional / mild-risk season"
    return "Dry / low-risk season"