"""
routes/sensor_data.py
---------------------
Endpoints for receiving GPS/accelerometer sensor data from mobile app.
Used for anti-spoofing detection (Module 2, Gateway 4) and eligibility validation.

DPDP Act 2023 Compliance:
- Sensor data auto-deleted after 7 days
- Mobile app must have explicit consent before collection
- Only GPS location + motion sensors collected (no personal identifiers)
"""

from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.connection import get_db
from models.policy import SensorLog
from models.rider import Rider

router = APIRouter(prefix="/rider", tags=["Sensor Data"])


class SensorDataPayload(BaseModel):
    """Mobile app sensor snapshot payload."""
    gps_latitude: float = Field(..., ge=-90, le=90, description="Latitude")
    gps_longitude: float = Field(..., ge=-180, le=180, description="Longitude")
    gps_accuracy_meters: float = Field(..., gt=0, description="GPS accuracy in meters")
    accelerometer_variance: float = Field(..., ge=0, le=10, description="Accel variance 0-10")
    gyroscope_variance: float = Field(..., ge=0, le=10, description="Gyro variance 0-10")
    magnetometer_variance: float = Field(None, ge=0, le=10, description="Mag variance 0-10")
    wifi_ssid_count: int = Field(..., ge=0, description="Count of visible Wi-Fi networks")
    device_id: str = Field(None, description="Mobile device identifier")
    app_version: str = Field(None, description="App version (e.g., 1.0.0)")
    recorded_at: str = Field(None, description="ISO datetime when sensor was captured")


@router.post("/{rider_id}/sensor-data")
async def store_sensor_data(
    rider_id: int,
    payload: SensorDataPayload,
    db: AsyncSession = Depends(get_db),
):
    """
    Store GPS and motion sensor readings from mobile app.
    
    Called by Person 4's mobile app every ~5 seconds during active ride.
    Data is used by Module 2 (spoof detection) and Module 3 (eligibility gate 4).
    
    Args:
        rider_id: Rider ID
        payload: Sensor snapshot with GPS, accelerometer, gyroscope readings
        
    Returns:
        201 Created with sensor log ID
        
    DPDP Act: Data stored for 7 days max (auto-pruned by scheduled job)
    """
    
    # Verify rider exists
    rider_result = await db.execute(select(Rider).where(Rider.id == rider_id))
    rider = rider_result.scalar_one_or_none()
    if rider is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rider not found")
    
    # Parse recorded_at or default to now
    try:
        if payload.recorded_at:
            recorded_dt = datetime.fromisoformat(payload.recorded_at.replace("Z", "+00:00"))
        else:
            recorded_dt = datetime.now(timezone.utc)
    except (ValueError, AttributeError):
        recorded_dt = datetime.now(timezone.utc)
    
    # Create sensor log entry
    sensor_log = SensorLog(
        rider_id=rider_id,
        gps_latitude=payload.gps_latitude,
        gps_longitude=payload.gps_longitude,
        gps_accuracy_meters=payload.gps_accuracy_meters,
        accelerometer_variance=payload.accelerometer_variance,
        gyroscope_variance=payload.gyroscope_variance,
        magnetometer_variance=payload.magnetometer_variance,
        wifi_ssid_count=payload.wifi_ssid_count,
        device_id=payload.device_id,
        app_version=payload.app_version,
        recorded_at=recorded_dt,
        sensor_payload={
            "gps_accuracy": payload.gps_accuracy_meters,
            "accel_variance": payload.accelerometer_variance,
            "gyro_variance": payload.gyroscope_variance,
            "mag_variance": payload.magnetometer_variance,
            "wifi_ssid_count": payload.wifi_ssid_count,
        }
    )
    
    db.add(sensor_log)
    await db.commit()
    await db.refresh(sensor_log)
    
    return {
        "status": "stored",
        "sensor_log_id": sensor_log.id,
        "rider_id": rider_id,
        "recorded_at": sensor_log.recorded_at.isoformat(),
        "expires_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
    }


@router.get("/{rider_id}/sensor-data/latest")
async def get_latest_sensor_data(
    rider_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Get the latest sensor reading for a rider.
    Used by Module 3 eligibility checks (Gate 4 - spoof detection).
    
    Returns latest reading or None if not available.
    """
    
    # Verify rider exists
    rider_result = await db.execute(select(Rider).where(Rider.id == rider_id))
    rider = rider_result.scalar_one_or_none()
    if rider is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rider not found")
    
    # Get latest sensor log
    result = await db.execute(
        select(SensorLog)
        .where(SensorLog.rider_id == rider_id)
        .order_by(SensorLog.recorded_at.desc())
        .limit(1)
    )
    sensor_log = result.scalar_one_or_none()
    
    if sensor_log is None:
        return {
            "rider_id": rider_id,
            "latest_sensor_data": None,
            "message": "No sensor data available for this rider"
        }
    
    return {
        "rider_id": rider_id,
        "latest_sensor_data": sensor_log.to_dict(),
        "age_seconds": (datetime.now(timezone.utc) - sensor_log.recorded_at).total_seconds(),
    }


@router.delete("/{rider_id}/sensor-data")
async def delete_rider_sensor_data(
    rider_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Delete all sensor data for a rider (DPDP Act right to deletion).
    Also called by background job to purge data older than 7 days.
    
    Args:
        rider_id: Rider ID (or -1 to purge all data older than 7 days)
        
    Returns:
        Count of deleted records
    """
    
    if rider_id > 0:
        # Delete for specific rider
        result = await db.execute(
            select(SensorLog).where(SensorLog.rider_id == rider_id)
        )
        logs = result.scalars().all()
        count = len(logs)
        
        for log in logs:
            await db.delete(log)
    else:
        # Special case: delete all data older than 7 days (called by cleanup job)
        cutoff_dt = datetime.now(timezone.utc) - timedelta(days=7)
        result = await db.execute(
            select(SensorLog).where(SensorLog.created_at < cutoff_dt)
        )
        logs = result.scalars().all()
        count = len(logs)
        
        for log in logs:
            await db.delete(log)
    
    await db.commit()
    
    return {
        "status": "deleted",
        "count_deleted": count,
        "message": f"Deleted {count} sensor records" + (" (DPDP compliance - 7 day purge)" if rider_id < 0 else "")
    }
