from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx


DEFAULT_SHIFT_WINDOWS = [(10, 15), (18, 22)]
SPOOF_ENDPOINT = "http://localhost:8002/api/fraud/score-spoof"
SPOOF_REJECT_THRESHOLD = 0.70


def _coerce_dt(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str):
        normalized = value.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    return None


def _get_zone_ids(rider: dict) -> list[int]:
    return [
        zone_id
        for zone_id in [rider.get("zone1_id"), rider.get("zone2_id"), rider.get("zone3_id")]
        if zone_id is not None
    ]


def _extract_latest_sensor_data(history: list[dict] | None) -> dict | None:
    latest_snapshot = None
    latest_ts = None

    for entry in history or []:
        if not isinstance(entry, dict):
            continue
        snapshot = entry.get("latest_sensor_snapshot")
        if not isinstance(snapshot, dict):
            continue

        ts = _coerce_dt(snapshot.get("timestamp"))
        if ts is None:
            ts = _coerce_dt(entry.get("date"))
        if ts is None:
            continue

        if latest_ts is None or ts > latest_ts:
            latest_ts = ts
            latest_snapshot = snapshot

    return latest_snapshot


def _normalize_shift_windows(raw_windows: Any) -> list[tuple[int, int]]:
    normalized: list[tuple[int, int]] = []
    for item in raw_windows or []:
        if isinstance(item, (list, tuple)) and len(item) == 2:
            start, end = int(item[0]), int(item[1])
            if 0 <= start <= 23 and 0 <= end <= 23 and start < end:
                normalized.append((start, end))
    return normalized


def _infer_shift_windows_from_history(history: list[dict] | None) -> list[tuple[int, int]]:
    hour_hits: dict[int, int] = {}
    for entry in history or []:
        if not isinstance(entry, dict):
            continue
        intervals = entry.get("shift_intervals")
        if isinstance(intervals, list):
            for interval in intervals:
                if isinstance(interval, dict):
                    start_hour = interval.get("start_hour")
                    end_hour = interval.get("end_hour")
                    if isinstance(start_hour, int) and isinstance(end_hour, int):
                        for hour in range(max(0, start_hour), min(24, end_hour)):
                            hour_hits[hour] = hour_hits.get(hour, 0) + 1

    if not hour_hits:
        return []

    active_hours = sorted(h for h, count in hour_hits.items() if count >= 3)
    if not active_hours:
        return []

    windows: list[tuple[int, int]] = []
    start = active_hours[0]
    prev = active_hours[0]
    for hour in active_hours[1:]:
        if hour == prev + 1:
            prev = hour
            continue
        windows.append((start, prev + 1))
        start = hour
        prev = hour
    windows.append((start, prev + 1))
    return windows


def _event_overlaps_shift_windows(
    event_start: datetime,
    event_end: datetime | None,
    shift_windows: list[tuple[int, int]],
) -> tuple[bool, dict]:
    event_end = event_end or event_start
    event_end = max(event_end, event_start)

    matched_windows = []
    for shift_start, shift_end in shift_windows:
        shift_start_dt = event_start.replace(hour=shift_start, minute=0, second=0, microsecond=0)
        shift_end_dt = event_start.replace(hour=shift_end, minute=0, second=0, microsecond=0)
        overlaps = max(event_start, shift_start_dt) < min(event_end, shift_end_dt)
        if overlaps:
            matched_windows.append(f"{shift_start:02d}:00-{shift_end:02d}:00")

    return bool(matched_windows), {
        "matched_windows": matched_windows,
        "candidate_windows": [f"{s:02d}:00-{e:02d}:00" for s, e in shift_windows],
    }


def _platform_inactive_for_event(history: list[dict] | None, event_start: datetime) -> tuple[bool, dict]:
    event_date = event_start.date().isoformat()
    for entry in history or []:
        if not isinstance(entry, dict):
            continue
        if entry.get("date") != event_date:
            continue
        income = float(entry.get("income") or 0)
        hours = float(entry.get("hours") or 0)
        return (income <= 0 and hours <= 0), {
            "event_date": event_date,
            "income": income,
            "hours": hours,
            "orders": int(entry.get("orders") or 0),
        }

    return True, {"event_date": event_date, "income": 0.0, "hours": 0.0, "orders": 0}


async def evaluate_eligibility(rider: dict, event: dict, sensor_data: dict | None = None) -> dict:
    event_start = _coerce_dt(event.get("event_start")) or datetime.now(timezone.utc)
    event_end = _coerce_dt(event.get("event_end"))
    affected_zone = event.get("affected_zone")

    rider_zone_ids = _get_zone_ids(rider)
    gate1_zone_match = affected_zone in rider_zone_ids
    if not gate1_zone_match:
        rejection_reason = f"Disruption in zone {affected_zone} is not in your registered zones."
        return {
            "gate1_zone_match": False,
            "gate2_shift_overlap": False,
            "gate3_platform_inactive": False,
            "gate4_sensor_verified": False,
            "all_gates_passed": False,
            "rejection_reason": rejection_reason,
            "gate_details": {
                "zone_ids": rider_zone_ids,
                "matched_zone": None,
            },
        }

    history = rider.get("daily_income_history") or []
    preferred_windows = _normalize_shift_windows(rider.get("typical_shift_windows"))
    inferred_windows = _infer_shift_windows_from_history(history)
    shift_windows = preferred_windows or inferred_windows or DEFAULT_SHIFT_WINDOWS

    gate2_shift_overlap, shift_details = _event_overlaps_shift_windows(event_start, event_end, shift_windows)
    shift_details["source"] = (
        "module2_endpoint"
        if preferred_windows
        else "daily_income_history"
        if inferred_windows
        else "default_fallback"
    )
    if not gate2_shift_overlap:
        rejection_reason = f"Disruption at {event_start.hour:02d}:00 is outside your shift window."
        return {
            "gate1_zone_match": True,
            "gate2_shift_overlap": False,
            "gate3_platform_inactive": False,
            "gate4_sensor_verified": False,
            "all_gates_passed": False,
            "rejection_reason": rejection_reason,
            "gate_details": {
                "zone_ids": rider_zone_ids,
                "shift_window": shift_details,
            },
        }

    gate3_platform_inactive, activity_details = _platform_inactive_for_event(history, event_start)
    if not gate3_platform_inactive:
        rejection_reason = "Platform activity detected during disruption window."
        return {
            "gate1_zone_match": True,
            "gate2_shift_overlap": True,
            "gate3_platform_inactive": False,
            "gate4_sensor_verified": False,
            "all_gates_passed": False,
            "rejection_reason": rejection_reason,
            "gate_details": {
                "zone_ids": rider_zone_ids,
                "shift_window": shift_details,
                "activity": activity_details,
            },
        }

    sensor_payload = sensor_data or _extract_latest_sensor_data(history)
    gate4_sensor_verified = True
    sensor_details: dict[str, Any] = {}

    if sensor_payload:
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                response = await client.post(
                    SPOOF_ENDPOINT,
                    json={
                        "rider_id": int(rider["id"]),
                        "gps_accuracy_m": sensor_payload.get("gps_accuracy_meters"),
                        "accelerometer_variance": sensor_payload.get("accelerometer_variance"),
                        "gyroscope_variance": sensor_payload.get("gyroscope_variance"),
                        "wifi_ssid_count": sensor_payload.get("wifi_ssid_count"),
                    },
                )
                response.raise_for_status()
                body = response.json()
                spoof_score = float(body.get("spoof_score") or 0.0)
                gate4_sensor_verified = spoof_score <= SPOOF_REJECT_THRESHOLD
                sensor_details = {
                    "sensor_data_used": True,
                    "spoof_score": spoof_score,
                    "verdict": body.get("verdict"),
                    "signals": body.get("signals", {}),
                    "reasons": body.get("reasons", []),
                }
        except Exception as exc:
            gate4_sensor_verified = True
            sensor_details = {
                "sensor_data_used": bool(sensor_payload),
                "sensor_check_failed_open": True,
                "error": str(exc),
            }
    else:
        sensor_details = {
            "sensor_data": "unavailable",
            "gate_defaulted_to_pass": True,
        }

    rejection_reason = None
    if not gate4_sensor_verified:
        spoof_score = sensor_details.get("spoof_score", 0.0)
        rejection_reason = (
            f"Location verification failed — sensor inconsistency detected (score: {spoof_score})."
        )

    return {
        "gate1_zone_match": True,
        "gate2_shift_overlap": gate2_shift_overlap,
        "gate3_platform_inactive": gate3_platform_inactive,
        "gate4_sensor_verified": gate4_sensor_verified,
        "all_gates_passed": gate2_shift_overlap and gate3_platform_inactive and gate4_sensor_verified,
        "rejection_reason": rejection_reason,
        "gate_details": {
            "zone_ids": rider_zone_ids,
            "shift_window": shift_details,
            "activity": activity_details,
            "sensor": sensor_details,
        },
    }
