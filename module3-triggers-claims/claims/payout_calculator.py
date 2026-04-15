from __future__ import annotations


def calculate_payout(hourly_rate: float, disrupted_hours: float, severity_rate: float) -> dict:
    """
    Pure payout arithmetic:
      disrupted_income = disrupted_hours * hourly_rate
      gross_payout = disrupted_income * severity_rate
    """
    hrs = max(0.0, float(disrupted_hours or 0.0))
    rate = max(0.0, float(hourly_rate or 0.0))
    sev = max(0.0, float(severity_rate or 0.0))

    disrupted_income = hrs * rate
    gross_payout = disrupted_income * sev

    return {
        "disrupted_hours": round(hrs, 2),
        "hourly_rate": round(rate, 2),
        "disrupted_income": round(disrupted_income, 2),
        "severity_rate": round(sev, 4),
        "gross_payout": round(gross_payout, 2),
    }

