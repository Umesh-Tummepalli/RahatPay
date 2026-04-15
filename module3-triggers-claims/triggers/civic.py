from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from models.policy import DisruptionEvent
from triggers.severity import classify_severity


async def create_civic_disruption(zone_id: int, reason: str, db_session: AsyncSession) -> dict[str, Any]:
    """
    Creates a civic disruption event (admin/verified manual trigger).
    """
    severity, rate = classify_severity("civic_disruption", 1.0)
    now = datetime.now(timezone.utc)
    event = DisruptionEvent(
        event_type="civic_disruption",
        severity=severity or "severe_l1",
        payout_rate=rate or 0.45,
        affected_zone=zone_id,
        trigger_data={"source": "civic_verified", "reason": reason},
        event_start=now,
        event_end=now + timedelta(hours=6),
        processing_status="pending",
    )
    db_session.add(event)
    await db_session.flush()

    return {"event_id": event.id, "event_type": event.event_type, "severity": event.severity, "severity_rate": float(event.payout_rate)}

