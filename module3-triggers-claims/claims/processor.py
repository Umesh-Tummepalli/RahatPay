from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import httpx
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from models.rider import Rider
from models.policy import Policy, Claim, DisruptionEvent
from config import TIER_CONFIG

from claims.eligibility import evaluate_eligibility
from claims.payout_calculator import calculate_payout
from claims.cap_enforcer import enforce_cap

logger = logging.getLogger(__name__)

MODULE2_BASE_URL = "http://localhost:8002"


def _event_is_covered(policy_tier: str, event_type: str) -> bool:
    tier_cfg = TIER_CONFIG.get(policy_tier, {})
    allowed_triggers = tier_cfg.get("coverage_triggers", [])

    if event_type in allowed_triggers:
        return True
    if "weather_conditions" in allowed_triggers and event_type in ("heavy_rain", "cyclone", "flood", "extreme_heat"):
        return True
    if "platform_outages" in allowed_triggers and event_type == "civic_disruption":
        return True
    if "civic_disruptions" in allowed_triggers and event_type == "civic_disruption":
        return True
    if event_type == "other":
        return True
    return False


def _event_duration_hours(event: DisruptionEvent) -> float:
    if event.event_start and event.event_end:
        dur = (event.event_end - event.event_start).total_seconds() / 3600.0
        return max(0.5, round(dur, 2))
    return 8.0


async def _fetch_baseline_from_module2(rider_id: int) -> dict[str, Any] | None:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{MODULE2_BASE_URL}/api/baseline/{rider_id}")
            if resp.status_code == 200:
                return resp.json()
    except Exception:
        return None
    return None


async def _fetch_spoof_score(sensor_data: dict[str, Any] | None) -> float | None:
    if sensor_data is None:
        return None
    # Person 2 endpoint may not exist yet. Fail open.
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(f"{MODULE2_BASE_URL}/api/fraud/score-spoof", json={"sensor_data": sensor_data})
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, dict):
                    if "score" in data:
                        return float(data["score"])
                    if "spoof_probability" in data:
                        return float(data["spoof_probability"])
    except Exception:
        return None
    return None


async def _run_fraud_checks(event: DisruptionEvent, claims_payload: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    """
    Returns a map claim_id -> fraud_result.
    Current Module 2 may not expose these endpoints yet, so this degrades gracefully.
    """
    flagged_map: dict[int, dict[str, Any]] = {}

    zone_payload = {
        "event_id": event.id,
        "event_type": event.event_type,
        "affected_zone": event.affected_zone,
        "is_api_verified": bool((event.trigger_data or {}).get("is_api_verified", False)),
        "claims": claims_payload,
    }

    try:
        async with httpx.AsyncClient(timeout=6.0) as client:
            zone_resp = await client.post(f"{MODULE2_BASE_URL}/api/fraud/check-zone", json=zone_payload)
            if zone_resp.status_code == 200:
                zone_data = zone_resp.json()
                if isinstance(zone_data, dict) and isinstance(zone_data.get("results"), list):
                    for row in zone_data["results"]:
                        claim_id = row.get("claim_id")
                        if claim_id is not None and row.get("flagged"):
                            flagged_map[int(claim_id)] = row
    except Exception:
        pass

    # Rider-level fraud checks, best effort
    for cp in claims_payload:
        claim_id = cp["claim_id"]
        rider_id = cp["rider_id"]
        if claim_id in flagged_map:
            continue
        try:
            async with httpx.AsyncClient(timeout=6.0) as client:
                rr = await client.post(
                    f"{MODULE2_BASE_URL}/api/fraud/check-rider",
                    json={"rider_id": rider_id, "zone_id": event.affected_zone},
                )
                if rr.status_code == 200:
                    data = rr.json()
                    flagged = bool(data.get("flagged")) if isinstance(data, dict) else False
                    if flagged:
                        flagged_map[claim_id] = {
                            "claim_id": claim_id,
                            "flagged": True,
                            "reason": data.get("reason", "rider_fraud_flagged"),
                        }
        except Exception:
            continue

    return flagged_map


async def process_disruption_claims(event_id: int, db_session: AsyncSession) -> dict[str, Any]:
    """
    Master claims orchestrator for both:
      - Person 1 auto-trigger polling loop
      - Admin simulate endpoint
    """
    event_res = await db_session.execute(select(DisruptionEvent).where(DisruptionEvent.id == event_id))
    event = event_res.scalar_one_or_none()
    if event is None:
        return {"event_id": event_id, "error": "Disruption event not found"}

    event.processing_status = "processing"
    await db_session.flush()

    rider_stmt = select(Rider).where(
        or_(
            Rider.zone1_id == event.affected_zone,
            Rider.zone2_id == event.affected_zone,
            Rider.zone3_id == event.affected_zone,
        )
    )
    rider_res = await db_session.execute(rider_stmt)
    riders = rider_res.scalars().all()

    total_affected = len(riders)
    eligible = 0
    approved = 0
    flagged = 0
    rejected = 0
    total_payout = 0.0
    claim_rows: list[dict[str, Any]] = []

    for rider in riders:
        pol_stmt = select(Policy).where(
            and_(
                Policy.rider_id == rider.id,
                Policy.status == "active",
                Policy.cycle_end_date >= datetime.now(timezone.utc).date(),
            )
        )
        pol_res = await db_session.execute(pol_stmt)
        policy = pol_res.scalar_one_or_none()
        if policy is None:
            continue

        if not _event_is_covered(policy.tier, event.event_type):
            continue

        baseline_payload = await _fetch_baseline_from_module2(rider.id)
        baseline_income = float(rider.baseline_weekly_income or 0.0)
        baseline_hours = float(rider.baseline_weekly_hours or 0.0)
        hourly_rate = float(rider.baseline_hourly_rate or 0.0)

        if isinstance(baseline_payload, dict):
            baseline_income = float(baseline_payload.get("weekly_income") or baseline_payload.get("baseline_weekly_income") or baseline_income or 0.0)
            baseline_hours = float(baseline_payload.get("weekly_hours") or baseline_payload.get("baseline_weekly_hours") or baseline_hours or 0.0)
            if baseline_hours > 0:
                hourly_rate = baseline_income / baseline_hours

        disrupted_hours = _event_duration_hours(event)

        # Sensor data placeholder (can be stored by Module 1 later)
        sensor_data = None
        spoof_score = await _fetch_spoof_score(sensor_data)

        eligibility = evaluate_eligibility(
            rider=rider.to_dict(),
            event={
                "affected_zone": event.affected_zone,
                "event_start": event.event_start,
                "event_end": event.event_end,
                "event_type": event.event_type,
            },
            sensor_data=sensor_data,
            spoof_score=spoof_score,
        )

        if not eligibility["all_gates_passed"]:
            claim = Claim(
                rider_id=rider.id,
                policy_id=policy.id,
                disruption_event_id=event.id,
                gate_results=eligibility,
                is_eligible=False,
                ineligibility_reason=eligibility["rejection_reason"],
                lost_hours=0.0,
                hourly_rate=hourly_rate,
                severity_rate=float(event.payout_rate),
                calculated_payout=0.0,
                final_payout=0.0,
                status="rejected",
            )
            db_session.add(claim)
            await db_session.flush()
            rejected += 1
            claim_rows.append({"claim_id": claim.id, "rider_id": rider.id, "status": "rejected", "reason": eligibility["rejection_reason"]})
            continue

        eligible += 1
        payout_math = calculate_payout(
            hourly_rate=hourly_rate,
            disrupted_hours=disrupted_hours,
            severity_rate=float(event.payout_rate),
        )
        cap_result = await enforce_cap(
            gross_payout=float(payout_math["gross_payout"]),
            tier=policy.tier,
            baseline_income=baseline_income,
            rider_id=rider.id,
            db_session=db_session,
        )

        final_payout = float(cap_result["final_payout"])
        status = "approved" if final_payout > 0 else "rejected"
        if status == "approved":
            approved += 1
            total_payout += final_payout
        else:
            rejected += 1

        gate_results = {
            **eligibility,
            "payout_math": payout_math,
            "cap_enforcement": cap_result,
        }

        claim = Claim(
            rider_id=rider.id,
            policy_id=policy.id,
            disruption_event_id=event.id,
            gate_results=gate_results,
            is_eligible=(status == "approved"),
            ineligibility_reason=None if status == "approved" else "Zero payout after cap/headroom check",
            lost_hours=float(payout_math["disrupted_hours"]),
            hourly_rate=float(payout_math["hourly_rate"]),
            severity_rate=float(payout_math["severity_rate"]),
            calculated_payout=float(payout_math["gross_payout"]),
            final_payout=final_payout,
            status=status,
        )
        db_session.add(claim)
        await db_session.flush()
        claim_rows.append({"claim_id": claim.id, "rider_id": rider.id, "status": status, "final_payout": final_payout})

    # Fraud checks (best effort)
    flagged_map = await _run_fraud_checks(event, claim_rows)
    if flagged_map:
        for row in claim_rows:
            claim_id = row["claim_id"]
            if claim_id not in flagged_map:
                continue
            c_res = await db_session.execute(select(Claim).where(Claim.id == claim_id))
            claim_obj = c_res.scalar_one_or_none()
            if claim_obj is None:
                continue
            # DB status doesn't currently support "in_review"; keep pending + annotate.
            claim_obj.status = "pending"
            claim_obj.gate_results = {
                **(claim_obj.gate_results or {}),
                "fraud_flagged": True,
                "fraud_reason": flagged_map[claim_id].get("reason", "fraud_flagged"),
            }
            flagged += 1
            if row.get("status") == "approved":
                approved = max(0, approved - 1)

    event.processing_status = "processed"
    await db_session.flush()

    summary = {
        "event_id": event.id,
        "total_affected": total_affected,
        "eligible": eligible,
        "approved": approved,
        "flagged": flagged,
        "rejected": rejected,
        "total_payout": round(total_payout, 2),
        "claims": claim_rows,
    }
    logger.info(f"Processed disruption claims: {summary}")
    return summary

