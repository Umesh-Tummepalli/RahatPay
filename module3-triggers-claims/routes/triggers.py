import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc

from db.connection import get_db
from models.rider import Zone
from models.policy import DisruptionEvent

from triggers.monitor import get_polling_log_entries

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/triggers", tags=["Triggers"])


@router.get("/active")
async def get_active_disruptions(db: AsyncSession = Depends(get_db)) -> list[dict[str, Any]]:
    """
    Returns disruption events that are currently considered 'active'.
    Since the DB constraint does not include a literal 'active' status, we map:
      active := processing_status IN ('pending','processing')
    """
    stmt = (
        select(DisruptionEvent, Zone)
        .join(Zone, Zone.zone_id == DisruptionEvent.affected_zone)
        .where(DisruptionEvent.processing_status.in_(["pending", "processing"]))
        .order_by(desc(DisruptionEvent.event_start))
        .limit(200)
    )
    result = await db.execute(stmt)
    rows = result.all()

    return [
        {
            "event_id": event.id,
            "event_type": event.event_type,
            "severity": event.severity,
            "severity_rate": float(event.payout_rate),
            "start_time": event.event_start.isoformat() if event.event_start else None,
            "end_time": event.event_end.isoformat() if event.event_end else None,
            "processing_status": event.processing_status,
            "zone": zone.to_dict(),
            "trigger_data": event.trigger_data,
        }
        for event, zone in rows
    ]


@router.get("/polling-log")
async def get_polling_log() -> dict[str, Any]:
    """
    Live in-memory feed of the last poll entries (max 200).
    """
    entries = get_polling_log_entries()
    return {
        "server_time": datetime.now(timezone.utc).isoformat(),
        "count": len(entries),
        "entries": entries,
    }

