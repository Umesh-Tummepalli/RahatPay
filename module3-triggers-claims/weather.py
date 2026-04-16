from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

OPENWEATHER_BASE = "https://api.openweathermap.org/data/2.5"


def classify_severity(event_type: str, raw_value: float) -> tuple[str | None, float | None]:
    if event_type == "rainfall_mm_6hr":
        if raw_value > 150:
            return "extreme", 0.75
        if raw_value >= 115:
            return "severe_l2", 0.60
        if raw_value >= 65:
            return "severe_l1", 0.45
        if raw_value >= 35:
            return "moderate", 0.30
        return None, None

    if event_type == "temperature_c":
        return ("moderate", 0.30) if raw_value > 42 else (None, None)

    if event_type == "aqi":
        if raw_value > 300:
            return "severe_l1", 0.45
        if raw_value >= 200:
            return "moderate", 0.30
        return None, None

    if event_type == "civic":
        return "severe_l1", 0.45

    return None, None


def _get_owm_key() -> str:
    key = os.getenv("OPENWEATHERMAP_API_KEY", "").strip()
    if not key:
        raise RuntimeError("OPENWEATHERMAP_API_KEY missing")
    return key


async def fetch_weather(lat: float, lon: float) -> dict[str, Any]:
    key = _get_owm_key()
    url = f"{OPENWEATHER_BASE}/weather"
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url, params={"lat": lat, "lon": lon, "appid": key})
        resp.raise_for_status()
        body = resp.json()
    rain_1h = float((body.get("rain") or {}).get("1h") or 0.0)
    temp_kelvin = float((body.get("main") or {}).get("temp") or 0.0)
    return {
        "rain_mm_6hr": round(rain_1h * 6.0, 2),
        "temp_celsius": round(temp_kelvin - 273.15, 2) if temp_kelvin else 0.0,
        "raw_response": body,
    }


async def fetch_aqi(lat: float, lon: float) -> dict[str, Any]:
    key = _get_owm_key()
    url = f"{OPENWEATHER_BASE}/air_pollution"
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url, params={"lat": lat, "lon": lon, "appid": key})
        resp.raise_for_status()
        body = resp.json()
    list0 = (body.get("list") or [{}])[0]
    pm25 = float((list0.get("components") or {}).get("pm2_5") or 0.0)
    return {"aqi_value": int(pm25 * 2.5), "pm25_raw": pm25, "raw_response": body}


async def create_civic_disruption(zone_id: int, reason: str, db_session: AsyncSession) -> dict[str, Any]:
    from models.policy import DisruptionEvent

    now = datetime.now(timezone.utc)
    event = DisruptionEvent(
        event_type="civic_disruption",
        severity="severe_l1",
        payout_rate=0.45,
        affected_zone=zone_id,
        trigger_data={"source": "civic_verified", "reason": reason, "is_api_verified": True},
        event_start=now,
        event_end=now + timedelta(hours=6),
        processing_status="pending",
    )
    db_session.add(event)
    await db_session.flush()
    return {"event_id": event.id, "zone_id": zone_id, "severity": event.severity, "payout_rate": float(event.payout_rate)}
