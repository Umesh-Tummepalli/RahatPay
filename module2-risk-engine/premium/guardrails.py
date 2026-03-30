"""
guardrails.py

Affordability guardrails applied to the raw premium before it reaches the rider.

Floor  : ₹15/week  — below this, API/infra costs aren't covered
Ceiling: 3.5% of weekly income — even worst-case monsoon + highest-risk zone
         + Raksha should never go above this
"""

PREMIUM_FLOOR_INR: float = 15.0
PREMIUM_CEILING_PCT: float = 0.035   # 3.5 % of baseline income


def apply_guardrails(raw_premium: float, baseline_income: float) -> float:
    """
    Clamps raw_premium between the floor and the income-proportionate ceiling.

    Args:
        raw_premium     : Result of (income × tier_rate × zone_risk × seasonal)
        baseline_income : Rider's 4-week average weekly income (₹)

    Returns:
        Final premium (₹), rounded to 2 decimal places.
    """
    ceiling = baseline_income * PREMIUM_CEILING_PCT

    # Apply floor first, then ceiling
    premium = max(raw_premium, PREMIUM_FLOOR_INR)
    premium = min(premium, ceiling)

    return round(premium, 2)


def guardrail_reason(raw_premium: float, baseline_income: float) -> str:
    """
    Human-readable explanation of which guardrail (if any) was applied.
    Used in the premium breakdown dict returned to the rider.
    """
    ceiling = baseline_income * PREMIUM_CEILING_PCT

    if raw_premium < PREMIUM_FLOOR_INR:
        return f"Floor applied — raw ₹{raw_premium:.2f} was below minimum ₹{PREMIUM_FLOOR_INR}"
    if raw_premium > ceiling:
        return f"Ceiling applied — raw ₹{raw_premium:.2f} capped at 3.5% of income (₹{ceiling:.2f})"
    return "No guardrail applied"