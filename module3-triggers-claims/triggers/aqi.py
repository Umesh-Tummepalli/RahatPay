from __future__ import annotations

import os
from typing import Any

import httpx


async def fetch_aqi(lat: float, lon: float) -> dict[str, Any]:
    """
    Calls OpenWeatherMap air pollution API and returns:
      - aqi_value (spec approximation: int(pm2_5 * 2.5))
      - pm25_raw
    """
    api_key = os.getenv("OPENWEATHERMAP_API_KEY")
    if not api_key:
        raise RuntimeError("OPENWEATHERMAP_API_KEY is not set")

    url = "https://api.openweathermap.org/data/2.5/air_pollution"
    params = {"lat": lat, "lon": lon, "appid": api_key}

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()

    pm25 = None
    try:
        if isinstance(data, dict):
            items = data.get("list") or []
            if items and isinstance(items[0], dict):
                comps = items[0].get("components") or {}
                if isinstance(comps, dict):
                    pm25 = comps.get("pm2_5")
        pm25_f = float(pm25) if pm25 is not None else None
    except (TypeError, ValueError):
        pm25_f = None

    aqi_value = int(pm25_f * 2.5) if pm25_f is not None else None

    return {
        "aqi_value": aqi_value,
        "pm25_raw": pm25_f,
    }

