from __future__ import annotations

import asyncio
from collections import deque
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import and_, or_, select

from claims.processor import process_disruption_claims
from db.connection import AsyncSessionLocal
from models.policy import DisruptionEvent
from models.rider import Zone
from weather import classify_severity, fetch_aqi, fetch_weather

POLL_SECONDS = 60
POLL_LOG: deque[dict[str, Any]] = deque(maxlen=200)
_POLL_TASK: asyncio.Task | None = None


def _active_event_window_clause(now: datetime):
    recent_window_start = now - timedelta(hours=6)
    return or_(
        DisruptionEvent.event_end >= now,
        and_(
            DisruptionEvent.event_end.is_(None),
            DisruptionEvent.created_at >= recent_window_start,
        ),
    )


def _zone_lat_lon(zone: Zone) -> tuple[float, float] | None:
    polygon = zone.polygon or []
    points = [p for p in polygon if isinstance(p, dict) and "lat" in p and "lng" in p]
    if not points:
        return None
    return (
        sum(float(p["lat"]) for p in points) / len(points),
        sum(float(p["lng"]) for p in points) / len(points),
    )


async def _create_event_if_needed(
    zone: Zone,
    event_type: str,
    severity: str,
    payout_rate: float,
    trigger_data: dict[str, Any],
) -> str:
    async with AsyncSessionLocal() as db:
        now = datetime.now(timezone.utc)
        dup = await db.execute(
            select(DisruptionEvent).where(
                and_(
                    DisruptionEvent.affected_zone == zone.zone_id,
                    DisruptionEvent.event_type == event_type,
                    DisruptionEvent.processing_status != "failed",
                    _active_event_window_clause(now),
                )
            )
        )
        if dup.scalar_one_or_none() is not None:
            return "duplicate_skipped"

        event = DisruptionEvent(
            event_type=event_type,
            severity=severity,
            payout_rate=payout_rate,
            affected_zone=zone.zone_id,
            trigger_data={**trigger_data, "is_api_verified": True},
            event_start=now,
            event_end=now + timedelta(hours=6),
            processing_status="pending",
        )
        db.add(event)
        await db.flush()
        await process_disruption_claims(event.id, db)
        return "event_created"


async def _poll_once() -> None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Zone).where(Zone.is_active.is_(True)))
        zones = result.scalars().all()

    for zone in zones:
        now_iso = datetime.now(timezone.utc).isoformat()
        lat_lon = _zone_lat_lon(zone)
        if lat_lon is None:
            POLL_LOG.append(
                {
                    "timestamp": now_iso,
                    "zone_id": zone.zone_id,
                    "zone_name": zone.area_name,
                    "measurements": {},
                    "threshold_breached": False,
                    "severity": None,
                    "action_taken": "no_centroid",
                }
            )
            continue
        lat, lon = lat_lon

        try:
            weather = await fetch_weather(lat, lon)
            aqi = await fetch_aqi(lat, lon)
        except Exception as exc:
            POLL_LOG.append(
                {
                    "timestamp": now_iso,
                    "zone_id": zone.zone_id,
                    "zone_name": zone.area_name,
                    "measurements": {},
                    "threshold_breached": False,
                    "severity": None,
                    "action_taken": "api_error",
                    "error": str(exc),
                }
            )
            continue

        checks = [
            ("heavy_rain", "rainfall_mm_6hr", float(weather["rain_mm_6hr"])),
            ("extreme_heat", "temperature_c", float(weather["temp_celsius"])),
            ("poor_aqi", "aqi", float(aqi["aqi_value"])),
        ]

        action_taken = "no_breach"
        breach_severity = None
        for event_type, feature, value in checks:
            severity, payout_rate = classify_severity(feature, value)
            if severity is None:
                continue
            breach_severity = severity
            action_taken = await _create_event_if_needed(
                zone=zone,
                event_type=event_type,
                severity=severity,
                payout_rate=float(payout_rate),
                trigger_data={
                    "source": "openweathermap",
                    "weather": weather["raw_response"],
                    "aqi": aqi["raw_response"],
                },
            )
            break

        POLL_LOG.append(
            {
                "timestamp": now_iso,
                "zone_id": zone.zone_id,
                "zone_name": zone.area_name,
                "measurements": {
                    "rainfall_mm": weather["rain_mm_6hr"],
                    "temp_c": weather["temp_celsius"],
                    "aqi": aqi["aqi_value"],
                },
                "threshold_breached": breach_severity is not None,
                "severity": breach_severity,
                "action_taken": action_taken,
            }
        )


async def start_trigger_polling_loop() -> None:
    while True:
        try:
            await _poll_once()
        except Exception:
            pass
        await asyncio.sleep(POLL_SECONDS)


def ensure_trigger_polling_started() -> None:
    global _POLL_TASK
    if _POLL_TASK is None or _POLL_TASK.done():
        _POLL_TASK = asyncio.create_task(start_trigger_polling_loop())


def get_polling_log() -> list[dict[str, Any]]:
    return list(POLL_LOG)
