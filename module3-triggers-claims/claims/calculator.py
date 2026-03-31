def calculate_payout(
    hourly_rate: float,
    disrupted_hours: float,
    severity_rate: float,
    weekly_cap: float,
    already_paid: float
) -> dict:
    """
    Computes the final payout for an approved claim, tightly enforcing systemic constraints.
    
    Args:
        hourly_rate: The rider's baseline hourly rate.
        disrupted_hours: How long the disruption event lasted.
        severity_rate: The payout modifier (e.g., 0.30 for moderate, 0.45 for severe L1).
        weekly_cap: The max total amount this rider can be paid in a week.
        already_paid: What the rider has already earned from approved claims this week.
        
    Returns:
        dict: Fully unrolled calculation steps so it transparently saves to DB metrics later.
    """
    
    # Base calculation
    disrupted_income = disrupted_hours * hourly_rate
    gross_payout = disrupted_income * severity_rate
    
    # Cap enforcement - determining headroom
    remaining_headroom = max(0.0, weekly_cap - already_paid)
    final_payout = min(gross_payout, remaining_headroom)
    
    return {
        "disrupted_hours": round(disrupted_hours, 2),
        "hourly_rate": round(hourly_rate, 2),
        "disrupted_income": round(disrupted_income, 2),
        "severity_rate": round(severity_rate, 2),
        "gross_payout": round(gross_payout, 2),
        "weekly_cap": round(weekly_cap, 2),
        "already_paid": round(already_paid, 2),
        "final_payout": round(final_payout, 2)
    }
