import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from db.connection import get_db
from models.rider import Zone
from models.policy import DisruptionEvent

from triggers.monitor import get_polling_log_entries
from triggers.civic import create_civic_disruption
from claims.processor import process_disruption_claims

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/triggers", tags=["Triggers"])


class CivicTriggerRequest(BaseModel):
    zone_id: int = Field(..., gt=0)
    reason: str = Field(..., min_length=3, max_length=500)


@router.get("/active")
async def get_active_disruptions(db: AsyncSession = Depends(get_db)) -> list[dict[str, Any]]:
    """
    Returns disruption events that are currently considered 'active'.
    Since DB has no literal 'active', we map it as:
      active := event_end is in the future (or missing) and not failed
    This keeps events visible even after Person 3 marks them "processed".
    """
    now = datetime.now(timezone.utc)
    stmt = (
        select(DisruptionEvent, Zone)
        .join(Zone, Zone.zone_id == DisruptionEvent.affected_zone)
        .where(DisruptionEvent.processing_status != "failed")
        .order_by(desc(DisruptionEvent.event_start))
        .limit(200)
    )
    result = await db.execute(stmt)
    rows = result.all()
    active_rows = []
    for event, zone in rows:
        if event.event_end is not None and event.event_end < now:
            continue
        active_rows.append((event, zone))

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
        for event, zone in active_rows
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


@router.post("/civic")
async def trigger_civic_disruption(request: CivicTriggerRequest, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """
    Manual civic trigger endpoint (multi-source verified civic alert flow).
    Creates a disruption event and immediately runs claims processor.
    """
    zone_res = await db.execute(select(Zone).where(Zone.zone_id == request.zone_id, Zone.is_active.is_(True)))
    zone = zone_res.scalar_one_or_none()
    if zone is None:
        raise HTTPException(status_code=404, detail="Active zone not found")

    event_payload = await create_civic_disruption(
        zone_id=request.zone_id,
        reason=request.reason,
        db_session=db,
    )
    processor_summary = await process_disruption_claims(event_payload["event_id"], db)

    return {
        "message": "Civic disruption created and processed",
        "event": event_payload,
        "processor_summary": processor_summary,
    }

