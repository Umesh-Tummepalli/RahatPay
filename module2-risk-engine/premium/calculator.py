"""
calculator.py

The core premium formula:

    Weekly Premium = Baseline Income × Tier Rate × Zone Risk × Seasonal Factor
    (then clamped by guardrails)

This is the function Module 1 calls when creating a policy.
It returns not just the number but a full breakdown dict —
every intermediate value is exposed so the rider and admin can
see exactly how the premium was calculated.
"""

from .zone_risk import get_rider_zone_risk, get_zone_risk_full
from .seasonal import get_seasonal_factor, seasonal_label
from .guardrails import apply_guardrails, guardrail_reason
from .profiler import get_baseline


# ── Tier configuration ────────────────────────────────────────────────────────

TIER_RATES: dict[str, float] = {
    "kavach":   0.010,   # 1.0 %
    "suraksha": 0.018,   # 1.8 %
    "raksha":   0.025,   # 2.5 %
}

TIER_PAYOUT_CAPS: dict[str, float] = {
    "kavach":   0.35,    # 35 % of income
    "suraksha": 0.55,    # 55 % of income
    "raksha":   0.70,    # 70 % of income
}

TIER_COVERAGE_LABEL: dict[str, str] = {
    "kavach":   "Environmental disruptions only",
    "suraksha": "Environmental + Social disruptions",
    "raksha":   "Environmental + Social + Composite disruptions",
}

TIER_CLAIM_SPEED: dict[str, str] = {
    "kavach":   "24–48 hours",
    "suraksha": "6–12 hours",
    "raksha":   "2–4 hours",
}


# ── Main calculator ───────────────────────────────────────────────────────────

def calculate_premium(
    baseline_weekly_income: float,
    tier: str,
    zone_pincodes: list[str],
    city: str,
    month: int | None = None,
) -> dict:
    """
    Calculates the weekly premium and returns a complete breakdown.

    Args:
        baseline_weekly_income : Rider's 4-week average weekly income (₹)
        tier                   : "kavach", "suraksha", or "raksha"
        zone_pincodes          : Ordered list of rider's top zone pin codes
        city                   : Rider's city (for city-specific seasonal factor)
        month                  : Calendar month 1–12 (defaults to current month)

    Returns:
        Full premium dict — see structure below.

    Raises:
        ValueError: if tier is not one of the three valid options.
    """
    tier = tier.lower()
    if tier not in TIER_RATES:
        raise ValueError(f"Invalid tier '{tier}'. Must be one of: {list(TIER_RATES.keys())}")

    # ── Step 1: Get each component ────────────────────────────────────────────
    tier_rate   = TIER_RATES[tier]
    zone_risk   = get_rider_zone_risk(zone_pincodes)
    seasonal    = get_seasonal_factor(city, month)

    # ── Step 2: Raw formula ───────────────────────────────────────────────────
    raw_premium = baseline_weekly_income * tier_rate * zone_risk * seasonal

    # ── Step 3: Apply guardrails ──────────────────────────────────────────────
    final_premium   = apply_guardrails(raw_premium, baseline_weekly_income)
    guardrail_note  = guardrail_reason(raw_premium, baseline_weekly_income)

    # ── Step 4: Derived values ────────────────────────────────────────────────
    payout_cap      = baseline_weekly_income * TIER_PAYOUT_CAPS[tier]
    pct_of_income   = (final_premium / baseline_weekly_income * 100) if baseline_weekly_income > 0 else 0

    # ── Step 5: Zone-level explanations (one per zone) ────────────────────────
    zone_details = [get_zone_risk_full(p) for p in zone_pincodes[:3]]

    # ── Step 6: Build full response dict ─────────────────────────────────────
    return {
        # The number the rider sees
        "weekly_premium_inr": final_premium,

        # Formula breakdown — visible on premium breakdown screen
        "breakdown": {
            "baseline_income":    baseline_weekly_income,
            "tier":               tier,
            "tier_rate":          tier_rate,
            "tier_rate_pct":      f"{tier_rate * 100:.1f}%",
            "zone_risk":          zone_risk,
            "zone_risk_label":    _zone_risk_label(zone_risk),
            "seasonal_factor":    seasonal,
            "seasonal_label":     seasonal_label(seasonal),
            "raw_premium":        round(raw_premium, 2),
            "guardrail_applied":  guardrail_note,
        },

        # Coverage details
        "coverage": {
            "weekly_payout_cap_inr": round(payout_cap, 2),
            "coverage_label":        TIER_COVERAGE_LABEL[tier],
            "claim_speed":           TIER_CLAIM_SPEED[tier],
        },

        # Summary stats
        "pct_of_income": round(pct_of_income, 2),

        # Zone-level explanations (feeds admin dashboard + rider app)
        "zone_details": zone_details,
    }


def calculate_premium_for_rider(rider_id: int, tier: str, month: int | None = None) -> dict:
    """
    Convenience wrapper — looks up rider's baseline from profiler and
    then calls calculate_premium.

    Module 1 can call this directly with just a rider_id and tier.
    """
    baseline = get_baseline(rider_id)

    # If rider is in seasoning with no zone history, use empty list
    # (zone_risk will default to 1.00 — fair neutral default)
    zone_pincodes = baseline["top_3_zones"]

    # Get city from dummy_db (on integration day, comes from DB)
    import dummy_db as db
    rider = db.get_rider(rider_id)
    city = rider["city"] if rider else "chennai"

    result = calculate_premium(
        baseline_weekly_income=baseline["weekly_income"],
        tier=tier,
        zone_pincodes=zone_pincodes,
        city=city,
        month=month,
    )

    # Attach baseline source info for transparency
    result["baseline_source"] = baseline["source"]
    result["rider_id"] = rider_id
    return result


# ── Helpers ───────────────────────────────────────────────────────────────────

def _zone_risk_label(risk: float) -> str:
    if risk >= 1.30:
        return "Very High Risk zone — frequent flooding/disruptions"
    if risk >= 1.15:
        return "High Risk zone — above-average disruption history"
    if risk >= 1.00:
        return "Moderate Risk zone — average disruption frequency"
    if risk >= 0.90:
        return "Low Risk zone — historically stable"
    return "Very Low Risk zone — minimal disruption history"