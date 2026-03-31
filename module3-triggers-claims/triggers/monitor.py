import os
import asyncio
import httpx
import logging
from datetime import datetime

from .evaluator import evaluate_metric

logger = logging.getLogger(__name__)

# Config
OWM_API_KEY = os.getenv("OWM_API_KEY", "")

# Sample pre-defined coordinates for demo zones.
MONITORED_ZONES = [
    {"pincode": "600017", "lat": 13.0405, "lon": 80.2337, "city": "Chennai"},
    {"pincode": "110001", "lat": 28.6328, "lon": 77.2197, "city": "Delhi"},
    {"pincode": "400017", "lat": 19.0494, "lon": 72.8404, "city": "Mumbai"},
]

async def fetch_weather_and_aqi(zone: dict, client: httpx.AsyncClient):
    """
    Simulates making calls to OWM Weather & Air Pollution API 
    and returns parsed rainfall, temp, and aqi.
    """
    if not OWM_API_KEY:
        # Without an API key, fallback mock behavior
        print(f"[MONITOR MOCK] Would poll weather API for {zone['city']} ({zone['pincode']})")
        return {"rainfall": 0, "temp_c": 30.0, "aqi": 50}

    try:
        # 1. Weather fetching
        w_url = f"https://api.openweathermap.org/data/2.5/weather?lat={zone['lat']}&lon={zone['lon']}&appid={OWM_API_KEY}&units=metric"
        w_resp = await client.get(w_url)
        w_data = w_resp.json() if w_resp.status_code == 200 else {}
        
        temp_c = w_data.get("main", {}).get("temp", 0)
        
        # OWM gives rain loosely by 1h or 3h. Let's rough-extrapolate it to 6h scale required.
        rain_3h = w_data.get("rain", {}).get("3h", 0)
        rainfall_6h = rain_3h * 2 

        # 2. AQI fetching
        aqi_url = f"http://api.openweathermap.org/data/2.5/air_pollution?lat={zone['lat']}&lon={zone['lon']}&appid={OWM_API_KEY}"
        aqi_resp = await client.get(aqi_url)
        aqi_data = aqi_resp.json() if aqi_resp.status_code == 200 else {}
        
        # Extrapolate PM2.5 to Indian AQI scale
        pm25 = 0
        try:
            pm25 = aqi_data["list"][0]["components"]["pm2_5"]
        except (KeyError, IndexError):
            pass
            
        # Very rough fallback mapping for Demo PM2.5 -> AQI
        calculated_aqi = pm25 * 3.5  
        
        return {"rainfall": rainfall_6h, "temp_c": temp_c, "aqi": calculated_aqi}
        
    except httpx.RequestError as e:
        logger.error(f"[MONITOR] HTTP Request error for zone {zone['pincode']}: {e}")
        return {"rainfall": 0, "temp_c": 0, "aqi": 0}

async def trigger_monitor_loop():
    """
    Main background process loop executed by FastAPI on startup.
    Runs every 60 seconds.
    """
    print("[MONITOR] Starting 60-second weather tracking service...")
    while True:
        try:
            async with httpx.AsyncClient() as client:
                for zone in MONITORED_ZONES:
                    metrics = await fetch_weather_and_aqi(zone, client)
                    
                    # Log evaluations
                    r_sev, r_rate = evaluate_metric("rainfall", metrics["rainfall"])
                    t_sev, t_rate = evaluate_metric("heat", metrics["temp_c"], duration_hours=3)
                    a_sev, a_rate = evaluate_metric("aqi", metrics["aqi"])
                    
                    # Logic here to trigger API to endpoint locally or internally insert to DB if 
                    # threshold is crossed. This triggers the module 3 claims pipeline...
                    
                    if r_sev or t_sev or a_sev:
                        print(f"[MONITOR HIT] Crossed threshold in {zone['pincode']}! (Weather conditions critical)")
                        
        except Exception as e:
            logger.error(f"[MONITOR] Unexpected loop error: {e}")
            
        await asyncio.sleep(60)
