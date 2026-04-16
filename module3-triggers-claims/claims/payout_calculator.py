from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any


DEFAULT_SHIFT_WINDOWS = [(10, 15), (18, 22)]


def _coerce_dt(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str):
        normalized = value.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    raise ValueError("Expected datetime or ISO datetime string")


def calculate_disrupted_hours(
    event_start: datetime | str,
    event_end: datetime | str | None,
    shift_windows: list[tuple[int, int]] | None = None,
) -> float:
    start_dt = _coerce_dt(event_start)
    end_dt = _coerce_dt(event_end) if event_end is not None else (start_dt + timedelta(hours=8))
    end_dt = max(end_dt, start_dt)
    windows = shift_windows or DEFAULT_SHIFT_WINDOWS

    overlap_hours = 0.0
    for shift_start, shift_end in windows:
        shift_start_dt = start_dt.replace(hour=shift_start, minute=0, second=0, microsecond=0)
        shift_end_dt = start_dt.replace(hour=shift_end, minute=0, second=0, microsecond=0)
        overlap_start = max(start_dt, shift_start_dt)
        overlap_end = min(end_dt, shift_end_dt)
        if overlap_start < overlap_end:
            overlap_hours += (overlap_end - overlap_start).total_seconds() / 3600

    return round(overlap_hours, 2)


def calculate_payout(hourly_rate: float, disrupted_hours: float, severity_rate: float) -> dict:
    disrupted_income = round(float(hourly_rate) * float(disrupted_hours), 2)
    gross_payout = round(disrupted_income * float(severity_rate), 2)
    return {
        "disrupted_hours": round(float(disrupted_hours), 2),
        "hourly_rate": round(float(hourly_rate), 2),
        "disrupted_income": disrupted_income,
        "severity_rate": round(float(severity_rate), 4),
        "gross_payout": gross_payout,
    }
