def evaluate_rainfall(mm_6hr: float) -> tuple[str, float]:
    """
    Evaluates rainfall based on 6-hour accumulation.
    Returns: (severity_level, payout_rate)
    Thresholds:
      35-65mm = Moderate (30%)
      65-115mm = Severe L1 (45%)
      115mm+ = Severe L2 (60%)
    """
    if mm_6hr >= 115:
        return ("Severe L2", 0.60)
    elif mm_6hr >= 65:
        return ("Severe L1", 0.45)
    elif mm_6hr >= 35:
        return ("Moderate", 0.30)
    return (None, 0.0)

def evaluate_heat(temp_c: float, duration_hours: float) -> tuple[str, float]:
    """
    Evaluates extreme heat.
    Returns: (severity_level, payout_rate)
    Thresholds:
      > 42°C for 3+ hours = Moderate (30%)
    """
    if temp_c > 42.0 and duration_hours >= 3.0:
        return ("Moderate", 0.30)
    return (None, 0.0)

def evaluate_aqi(aqi_val: float) -> tuple[str, float]:
    """
    Evaluates air quality index.
    Returns: (severity_level, payout_rate)
    Thresholds:
      200 <= AQI <= 300 = Moderate (30%)
      AQI > 300 = Severe L1 (45%)
    """
    if aqi_val > 300:
        return ("Severe L1", 0.45)
    elif aqi_val >= 200:
        return ("Moderate", 0.30)
    return (None, 0.0)

def evaluate_metric(event_type: str, measurement: float, duration_hours: float = 0.0) -> tuple[str, float]:
    """
    Wrapper to route the correct evaluation logic based on event_type.
    """
    if event_type == "rainfall":
        return evaluate_rainfall(measurement)
    elif event_type == "heat":
        return evaluate_heat(measurement, duration_hours)
    elif event_type == "aqi":
        return evaluate_aqi(measurement)
    
    return (None, 0.0)
