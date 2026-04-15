from __future__ import annotations

import asyncio
import logging
from collections import deque
from datetime import datetime, timezone, timedelta
from typing import Any

from sqlalchemy import select, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from db.connection import AsyncSessionLocal
from models.rider import Zone
from models.policy import DisruptionEvent

from triggers.weather import fetch_weather
from triggers.aqi import fetch_aqi
from triggers.severity import classify_severity

logger = logging.getLogger(__name__)

# In-memory polling log (last 200)
_POLLING_LOG: deque[dict[str, Any]] = deque(maxlen=200)


def get_polling_log_entries() -> list[dict[str, Any]]:
    return list(_POLLING_LOG)


def _polygon_centroid(polygon: Any) -> tuple[float, float] | None:
    """
    polygon is stored as JSONB list of {lat, lng}.
    Seed data uses 3 points (triangle). We'll compute a simple mean centroid.
    """
    if not polygon or not isinstance(polygon, list):
        return None
    lats: list[float] = []
    lngs: list[float] = []
    for p in polygon:
        if not isinstance(p, dict):
            continue
        try:
            lats.append(float(p.get("lat")))
            lngs.append(float(p.get("lng")))
        except (TypeError, ValueError):
            continue
    if not lats or not lngs:
        return None
    return sum(lats) / len(lats), sum(lngs) / len(lngs)


async def _dedupe_exists(
    db: AsyncSession,
    *,
    zone_id: int,
    event_type: str,
    lookback_hours: int = 6,
) -> bool:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
    stmt = (
        select(DisruptionEvent.id)
        .where(
            and_(
                DisruptionEvent.affected_zone == zone_id,
                DisruptionEvent.event_type == event_type,
                DisruptionEvent.event_start >= cutoff,
                DisruptionEvent.processing_status.in_(["pending", "processing"]),
            )
        )
        .order_by(desc(DisruptionEvent.event_start))
        .limit(1)
    )
    res = await db.execute(stmt)
    return res.scalar_one_or_none() is not None


async def _create_event(
    db: AsyncSession,
    *,
    zone: Zone,
    event_type: str,
    severity: str,
    payout_rate: float,
    trigger_data: dict[str, Any],
) -> int:
    now = datetime.now(timezone.utc)
    event = DisruptionEvent(
        event_type=event_type,
        severity=severity,
        payout_rate=payout_rate,
        affected_zone=zone.zone_id,
        trigger_data=trigger_data,
        event_start=now,
        event_end=now + timedelta(hours=6),
        processing_status="pending",
    )
    db.add(event)
    await db.flush()
    return int(event.id)


async def start_trigger_polling_loop() -> None:
    """
    Infinite loop started on Module 3 startup.
    Polls all active zones every 60 seconds and creates DisruptionEvents when thresholds are breached.
    """
    # Lazy import to avoid hard dependency while Person 3 is still building.
    try:
        from claims.processor import process_disruption_claims  # type: ignore
    except Exception:
        process_disruption_claims = None  # type: ignore
        logger.warning("Claims processor not available yet (claims.processor.process_disruption_claims). Trigger events will be created but claims won't run.")

    logger.info("Trigger polling loop started (interval=60s).")

    while True:
        cycle_start = datetime.now(timezone.utc)
        try:
            async with AsyncSessionLocal() as db:
                zones_res = await db.execute(select(Zone).where(Zone.is_active.is_(True)))
                zones = zones_res.scalars().all()
                logger.info(f"Polling cycle start: zones={len(zones)}")
                _POLLING_LOG.append(
                    {
                        "timestamp": cycle_start.isoformat(),
                        "zone_id": None,
                        "zone_name": None,
                        "measurements": {},
                        "threshold_breached": False,
                        "severity": None,
                        "action_taken": "cycle_start",
                    }
                )

                for zone in zones:
                    centroid = _polygon_centroid(zone.polygon)
                    if centroid is None:
                        _POLLING_LOG.append(
                            {
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                                "zone_id": zone.zone_id,
                                "zone_name": zone.area_name,
                                "measurements": {},
                                "threshold_breached": False,
                                "severity": None,
                                "action_taken": "zone_missing_centroid",
                            }
                        )
                        continue

                    lat, lon = centroid

                    # Fetch both signals
                    weather_task = asyncio.create_task(fetch_weather(lat, lon))
                    aqi_task = asyncio.create_task(fetch_aqi(lat, lon))
                    weather = await weather_task
                    aqi = await aqi_task

                    rain_mm_6hr = float(weather.get("rain_mm_6hr") or 0.0)
                    temp_c = weather.get("temp_celsius")
                    aqi_value = aqi.get("aqi_value")

                    breaches: list[dict[str, Any]] = []

                    sev, rate = classify_severity("heavy_rain", rain_mm_6hr)
                    if sev:
                        breaches.append({"event_type": "heavy_rain", "severity": sev, "rate": rate, "raw": rain_mm_6hr})

                    if temp_c is not None:
                        sev, rate = classify_severity("extreme_heat", float(temp_c))
                        if sev:
                            breaches.append({"event_type": "extreme_heat", "severity": sev, "rate": rate, "raw": float(temp_c)})

                    if aqi_value is not None:
                        sev, rate = classify_severity("poor_aqi", float(aqi_value))
                        if sev:
                            breaches.append({"event_type": "poor_aqi", "severity": sev, "rate": rate, "raw": float(aqi_value)})

                    if not breaches:
                        _POLLING_LOG.append(
                            {
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                                "zone_id": zone.zone_id,
                                "zone_name": zone.area_name,
                                "measurements": {"rainfall_mm_6hr": rain_mm_6hr, "temp_c": temp_c, "aqi": aqi_value},
                                "threshold_breached": False,
                                "severity": None,
                                "action_taken": "no_breach",
                            }
                        )
                        continue

                    # For demo, create one event per breached type (rain/heat/aqi)
                    for b in breaches:
                        event_type = b["event_type"]
                        if await _dedupe_exists(db, zone_id=zone.zone_id, event_type=event_type):
                            _POLLING_LOG.append(
                                {
                                    "timestamp": datetime.now(timezone.utc).isoformat(),
                                    "zone_id": zone.zone_id,
                                    "zone_name": zone.area_name,
                                    "measurements": {"rainfall_mm_6hr": rain_mm_6hr, "temp_c": temp_c, "aqi": aqi_value},
                                    "threshold_breached": True,
                                    "severity": b["severity"],
                                    "action_taken": "duplicate_skipped",
                                    "event_type": event_type,
                                }
                            )
                            continue

                        event_id = await _create_event(
                            db,
                            zone=zone,
                            event_type=event_type,
                            severity=b["severity"],
                            payout_rate=float(b["rate"]),
                            trigger_data={
                                "source": "openweathermap",
                                "is_api_verified": True,
                                "zone_centroid": {"lat": lat, "lon": lon},
                                "weather": weather.get("raw_response"),
                                "derived": {
                                    "rain_mm_6hr": rain_mm_6hr,
                                    "temp_celsius": temp_c,
                                    "pm25_raw": aqi.get("pm25_raw"),
                                    "aqi_value": aqi_value,
                                    "breach_raw_value": b["raw"],
                                },
                            },
                        )

                        _POLLING_LOG.append(
                            {
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                                "zone_id": zone.zone_id,
                                "zone_name": zone.area_name,
                                "measurements": {"rainfall_mm_6hr": rain_mm_6hr, "temp_c": temp_c, "aqi": aqi_value},
                                "threshold_breached": True,
                                "severity": b["severity"],
                                "action_taken": "event_created",
                                "event_type": event_type,
                                "event_id": event_id,
                            }
                        )

                        # Handoff to claims processor (Person 3)
                        if process_disruption_claims is not None:
                            try:
                                await process_disruption_claims(event_id, db)
                                # Mark processed if processor didn't already.
                                ev_res = await db.execute(select(DisruptionEvent).where(DisruptionEvent.id == event_id))
                                ev = ev_res.scalar_one_or_none()
                                if ev and ev.processing_status in {"pending", "processing"}:
                                    ev.processing_status = "processed"
                            except Exception as e:
                                logger.exception(f"Claims processing failed for event_id={event_id}: {e}")
                                ev_res = await db.execute(select(DisruptionEvent).where(DisruptionEvent.id == event_id))
                                ev = ev_res.scalar_one_or_none()
                                if ev:
                                    ev.processing_status = "failed"

                await db.commit()

        except Exception as e:
            logger.exception(f"Trigger polling loop cycle failed: {e}")

        # Sleep until next minute boundary-ish
        elapsed = (datetime.now(timezone.utc) - cycle_start).total_seconds()
        sleep_for = max(5.0, 60.0 - elapsed)
        await asyncio.sleep(sleep_for)

