def get_rider_hourly_rate(rider) -> float:
    """
    Mock wrapper for Module 2's baseline profiler.
    In the final system, this will import `from module2.baseline.profiler import get_baseline`
    and pass the rider details to it. For now, we compute the hourly rate directly 
    off the database object since Module 2 is still being built.
    """
    try:
        if rider.baseline_hours and rider.baseline_hours > 0:
            return round(rider.baseline_income / rider.baseline_hours, 2)
    except Exception:
        pass
    
    return 0.0
