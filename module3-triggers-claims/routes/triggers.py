from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.connection import get_db
from models.policy import DisruptionEvent
from models.rider import Zone
from monitor import get_polling_log

router = APIRouter(prefix="/api/triggers", tags=["Triggers"])


@router.get("/active")
async def get_active_triggers(db: AsyncSession = Depends(get_db)):
    now = datetime.now(timezone.utc)
    recent_window_start = now - timedelta(hours=6)
    result = await db.execute(
        select(DisruptionEvent, Zone)
        .join(Zone, Zone.zone_id == DisruptionEvent.affected_zone)
        .where(
            and_(
                DisruptionEvent.processing_status != "failed",
                or_(
                    DisruptionEvent.event_end >= now,
                    and_(
                        DisruptionEvent.event_end.is_(None),
                        DisruptionEvent.created_at >= recent_window_start,
                    ),
                ),
            )
        )
        .order_by(DisruptionEvent.event_start.desc())
    )
    rows = result.all()
    return [
        {
            "event_id": event.id,
            "zone_id": event.affected_zone,
            "zone_name": zone.area_name,
            "city": zone.city,
            "event_type": event.event_type,
            "severity": event.severity,
            "severity_rate": float(event.payout_rate),
            "start_time": event.event_start.isoformat() if event.event_start else None,
            "end_time": event.event_end.isoformat() if event.event_end else None,
            "processing_status": event.processing_status,
            "trigger_data": event.trigger_data or {},
        }
        for event, zone in rows
    ]


@router.get("/polling-log")
async def get_trigger_polling_log():
    entries = get_polling_log()
    return {"entries": entries, "count": len(entries)}
