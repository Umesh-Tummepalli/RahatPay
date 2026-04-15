from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _default_shift_windows() -> list[tuple[int, int]]:
    # Split-shift fallback from spec.
    return [(10, 15), (18, 22)]


def _derive_shift_windows_from_history(history: list[dict[str, Any]]) -> list[tuple[int, int]]:
    """
    Attempts to infer shift windows from history entries.
    If granular timestamps are unavailable (current seed data), fallback to split shifts.
    """
    # Most current seed data has only date/hours/income, no hour-level timestamps.
    # Keep fallback deterministic for now.
    if not history:
        return _default_shift_windows()
    return _default_shift_windows()


def _hour_in_windows(hour: int, windows: list[tuple[int, int]]) -> bool:
    for start, end in windows:
        if start <= hour < end:
            return True
    return False


def _extract_event_hour(event: dict[str, Any]) -> int:
    ts = event.get("event_start")
    if isinstance(ts, datetime):
        dt = ts
    elif isinstance(ts, str):
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except Exception:
            dt = datetime.now(timezone.utc)
    else:
        dt = datetime.now(timezone.utc)
    return dt.astimezone(timezone.utc).hour


def evaluate_eligibility(rider: dict, event: dict, sensor_data: dict | None = None, spoof_score: float | None = None) -> dict:
    """
    4-gate eligibility evaluator.
    """
    rider_id = rider.get("id")
    rider_zones = {z for z in [rider.get("zone1_id"), rider.get("zone2_id"), rider.get("zone3_id")] if z is not None}
    event_zone = event.get("affected_zone")
    event_hour = _extract_event_hour(event)

    # Gate 1: zone match
    gate1_zone_match = event_zone in rider_zones
    if not gate1_zone_match:
        return {
            "rider_id": rider_id,
            "gate1_zone_match": False,
            "gate2_shift_overlap": False,
            "gate3_platform_inactive": False,
            "gate4_sensor_verified": False,
            "all_gates_passed": False,
            "rejection_reason": f"Disruption in zone {event_zone} is not in your registered zones.",
            "gate_details": {"event_zone": event_zone, "rider_zones": sorted(list(rider_zones))},
        }

    # Gate 2: shift overlap
    history = rider.get("daily_income_history") or []
    windows = _derive_shift_windows_from_history(history if isinstance(history, list) else [])
    gate2_shift_overlap = _hour_in_windows(event_hour, windows)
    if not gate2_shift_overlap:
        return {
            "rider_id": rider_id,
            "gate1_zone_match": True,
            "gate2_shift_overlap": False,
            "gate3_platform_inactive": False,
            "gate4_sensor_verified": False,
            "all_gates_passed": False,
            "rejection_reason": f"Disruption at {event_hour}:00 is outside your shift window.",
            "gate_details": {"shift_windows": windows, "event_hour": event_hour},
        }

    # Gate 3: platform inactivity on event date
    event_date = None
    ev_start = event.get("event_start")
    if isinstance(ev_start, datetime):
        event_date = ev_start.date().isoformat()
    elif isinstance(ev_start, str):
        try:
            event_date = datetime.fromisoformat(ev_start.replace("Z", "+00:00")).date().isoformat()
        except Exception:
            event_date = None

    income_on_event_date = None
    if isinstance(history, list) and event_date:
        for entry in history:
            if not isinstance(entry, dict):
                continue
            if entry.get("date") == event_date:
                income_on_event_date = float(entry.get("income") or entry.get("amount") or 0.0)
                break

    # If there is recorded income on event date, treat as active -> fail.
    gate3_platform_inactive = not (income_on_event_date is not None and income_on_event_date > 0)
    if not gate3_platform_inactive:
        return {
            "rider_id": rider_id,
            "gate1_zone_match": True,
            "gate2_shift_overlap": True,
            "gate3_platform_inactive": False,
            "gate4_sensor_verified": False,
            "all_gates_passed": False,
            "rejection_reason": "Platform activity detected during disruption window.",
            "gate_details": {"event_date": event_date, "income_on_event_date": income_on_event_date},
        }

    # Gate 4: spoof score
    gate4_sensor_verified = True
    gate4_note = None
    if spoof_score is None:
        gate4_note = "sensor_data_unavailable_or_scorer_unreachable"
    else:
        gate4_sensor_verified = float(spoof_score) <= 0.7
        if not gate4_sensor_verified:
            return {
                "rider_id": rider_id,
                "gate1_zone_match": True,
                "gate2_shift_overlap": True,
                "gate3_platform_inactive": True,
                "gate4_sensor_verified": False,
                "all_gates_passed": False,
                "rejection_reason": f"Location verification failed — sensor inconsistency detected (score: {spoof_score:.2f}).",
                "gate_details": {"spoof_score": round(float(spoof_score), 4)},
            }

    return {
        "rider_id": rider_id,
        "gate1_zone_match": True,
        "gate2_shift_overlap": True,
        "gate3_platform_inactive": True,
        "gate4_sensor_verified": True,
        "all_gates_passed": True,
        "rejection_reason": None,
        "gate_details": {
            "shift_windows": windows,
            "event_hour": event_hour,
            "event_date": event_date,
            "income_on_event_date": income_on_event_date,
            "spoof_score": None if spoof_score is None else round(float(spoof_score), 4),
            "gate4_note": gate4_note,
            "sensor_data_present": sensor_data is not None,
        },
    }

