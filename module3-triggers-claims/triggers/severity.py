from __future__ import annotations


def classify_severity(event_type: str, raw_value: float) -> tuple[str | None, float | None]:
    """
    Maps a raw measurement to (severity, payout_rate).

    Event type mapping is aligned with DB constraints:
      - rainfall -> 'heavy_rain'
      - temperature -> 'extreme_heat'
      - aqi -> 'poor_aqi'
      - civic -> 'civic_disruption'
    """
    if raw_value is None:
        return None, None

    et = (event_type or "").strip().lower()

    # Rainfall thresholds (mm/6hr)
    if et in {"rainfall", "heavy_rain"}:
        v = float(raw_value)
        if 35 <= v < 65:
            return "moderate", 0.30
        if 65 <= v < 115:
            return "severe_l1", 0.45
        if 115 <= v < 150:
            return "severe_l2", 0.60
        if v >= 150:
            return "extreme", 0.75
        return None, None

    # Temperature thresholds (°C)
    if et in {"temperature", "extreme_heat"}:
        v = float(raw_value)
        if v > 42:
            return "moderate", 0.30
        return None, None

    # AQI thresholds (Indian scale)
    if et in {"aqi", "poor_aqi"}:
        v = float(raw_value)
        if 200 <= v <= 300:
            return "moderate", 0.30
        if v > 300:
            return "severe_l1", 0.45
        return None, None

    # Civic triggers
    if et in {"civic", "civic_disruption"}:
        return "severe_l1", 0.45

    return None, None

