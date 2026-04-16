from __future__ import annotations

import os
from typing import Any

import httpx


async def fetch_weather(lat: float, lon: float) -> dict[str, Any]:
    """
    Calls OpenWeatherMap current weather API and returns:
      - rain_mm_6hr (approx: rain.1h * 6)
      - temp_celsius
      - raw_response
    """
    api_key = os.getenv("OPENWEATHERMAP_API_KEY")
    if not api_key:
        raise RuntimeError("OPENWEATHERMAP_API_KEY is not set")

    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {"lat": lat, "lon": lon, "appid": api_key}

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()

    rain_1h = 0.0
    if isinstance(data, dict):
        rain_obj = data.get("rain") or {}
        if isinstance(rain_obj, dict):
            try:
                rain_1h = float(rain_obj.get("1h") or 0.0)
            except (TypeError, ValueError):
                rain_1h = 0.0

    temp_k = None
    main = data.get("main") if isinstance(data, dict) else None
    if isinstance(main, dict):
        temp_k = main.get("temp")
    temp_c = None
    try:
        if temp_k is not None:
            temp_c = float(temp_k) - 273.15
    except (TypeError, ValueError):
        temp_c = None

    return {
        "rain_mm_6hr": rain_1h * 6.0,
        "temp_celsius": temp_c,
        "raw_response": data,
    }

