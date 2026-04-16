from __future__ import annotations

from datetime import date, timedelta

import httpx
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from claims.cap_enforcer import enforce_cap
from claims.disbursement import disburse_payout
from claims.eligibility import evaluate_eligibility
from claims.payout_calculator import calculate_disrupted_hours, calculate_payout
from config import TIER_CONFIG
from models.policy import Claim, DisruptionEvent, Policy
from models.rider import Rider


FRAUD_ZONE_ENDPOINT = "http://localhost:8002/api/fraud/check-zone"
FRAUD_RIDER_ENDPOINT = "http://localhost:8002/api/fraud/check-rider"
SHIFT_WINDOW_ENDPOINT = "http://localhost:8002/api/rider/{rider_id}/shift-window"


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
    return event_type == "other"


async def _get_active_policy(db_session: AsyncSession, rider_id: int) -> Policy | None:
    result = await db_session.execute(
        select(Policy).where(
            and_(
                Policy.rider_id == rider_id,
                Policy.status == "active",
                Policy.cycle_end_date >= date.today(),
            )
        )
    )
    return result.scalar_one_or_none()


def _extract_shift_window_bounds(gate_details: dict) -> tuple[int, int]:
    windows = ((gate_details or {}).get("shift_window") or {}).get("candidate_windows", [])
    if not windows:
        return 10, 22
    parsed: list[tuple[int, int]] = []
    for win in windows:
        try:
            start_raw, end_raw = win.split("-")
            start_h = int(start_raw.split(":")[0])
            end_h = int(end_raw.split(":")[0])
            if 0 <= start_h <= 23 and 0 <= end_h <= 23 and start_h < end_h:
                parsed.append((start_h, end_h))
        except Exception:
            continue
    if not parsed:
        return 10, 22
    return min(x[0] for x in parsed), max(x[1] for x in parsed)


async def process_disruption_claims(event_id: int, db_session: AsyncSession) -> dict:
    event_result = await db_session.execute(select(DisruptionEvent).where(DisruptionEvent.id == event_id))
    event = event_result.scalar_one_or_none()
    if event is None:
        raise ValueError(f"Disruption event {event_id} not found")

    event.processing_status = "processing"
    await db_session.flush()

    rider_result = await db_session.execute(
        select(Rider).where(
            or_(
                Rider.zone1_id == event.affected_zone,
                Rider.zone2_id == event.affected_zone,
                Rider.zone3_id == event.affected_zone,
            )
        )
    )
    riders = rider_result.scalars().all()

    created_claims: list[Claim] = []
    claim_payloads: list[dict] = []
    rejected_count = 0

    async with httpx.AsyncClient(timeout=6.0) as client:
        for rider in riders:
            existing_claim_result = await db_session.execute(
                select(Claim).where(
                    and_(
                        Claim.rider_id == rider.id,
                        Claim.disruption_event_id == event.id,
                    )
                )
            )
            if existing_claim_result.scalar_one_or_none() is not None:
                continue

            policy = await _get_active_policy(db_session, rider.id)
            if policy is None or not _event_is_covered(policy.tier, event.event_type):
                continue

            rider_dict = rider.to_dict()
            try:
                shift_resp = await client.get(SHIFT_WINDOW_ENDPOINT.format(rider_id=rider.id))
                if shift_resp.is_success:
                    shift_body = shift_resp.json()
                    windows = shift_body.get("shift_windows") or shift_body.get("windows") or []
                    if isinstance(windows, list):
                        rider_dict["typical_shift_windows"] = windows
            except Exception:
                pass

            event_dict = {
                "id": event.id,
                "event_type": event.event_type,
                "severity": event.severity,
                "affected_zone": event.affected_zone,
                "payout_rate": float(event.payout_rate),
                "event_start": event.event_start,
                "event_end": event.event_end,
            }

            eligibility = await evaluate_eligibility(rider_dict, event_dict)
            hourly_rate = float(rider.baseline_hourly_rate or 0.0)
            baseline_income = float(rider.baseline_weekly_income or 0.0)
            shift_windows: list[tuple[int, int]] = []
            for candidate in ((eligibility.get("gate_details") or {}).get("shift_window") or {}).get("candidate_windows", []):
                try:
                    start_raw, end_raw = candidate.split("-")
                    shift_windows.append((int(start_raw.split(":")[0]), int(end_raw.split(":")[0])))
                except Exception:
                    continue
            disrupted_hours = calculate_disrupted_hours(
                event.event_start,
                event.event_end,
                shift_windows=shift_windows or None,
            )

            payout_math = calculate_payout(
                hourly_rate=hourly_rate,
                disrupted_hours=disrupted_hours,
                severity_rate=float(event.payout_rate),
            )
            cap_details = await enforce_cap(
                gross_payout=payout_math["gross_payout"],
                tier=policy.tier,
                baseline_income=baseline_income,
                rider_id=rider.id,
                db_session=db_session,
                policy_weekly_cap=float(policy.weekly_payout_cap),
                as_of=event.event_start,
            )

            initial_status = "pending" if eligibility["all_gates_passed"] else "rejected"
            if initial_status == "rejected":
                rejected_count += 1

            claim = Claim(
                rider_id=rider.id,
                policy_id=policy.id,
                disruption_event_id=event.id,
                gate_results={
                    **eligibility["gate_details"],
                    "payout_math": payout_math,
                    "cap_details": cap_details,
                },
                is_eligible=bool(eligibility["all_gates_passed"]),
                ineligibility_reason=eligibility["rejection_reason"],
                lost_hours=payout_math["disrupted_hours"],
                hourly_rate=payout_math["hourly_rate"],
                severity_rate=payout_math["severity_rate"],
                calculated_payout=payout_math["gross_payout"],
                final_payout=cap_details["final_payout"],
                status=initial_status,
            )
            db_session.add(claim)
            await db_session.flush()

            created_claims.append(claim)
            claim_payloads.append(
                {
                    "claim_id": claim.id,
                    "claim": claim,
                    "rider": rider,
                    "policy": policy,
                    "eligibility": eligibility,
                    "payout_math": payout_math,
                    "cap_details": cap_details,
                }
            )

    approved_count = 0
    flagged_count = 0
    paid_count = 0
    total_payout = 0.0

    clean_claims = [item for item in claim_payloads if item["claim"].status == "pending" and item["claim"].is_eligible]
    if clean_claims:
        async with httpx.AsyncClient(timeout=8.0) as client:
            try:
                zone_response = await client.post(
                    FRAUD_ZONE_ENDPOINT,
                    json={
                        "event_id": event.id,
                        "zone_pincode": str(event.affected_zone),
                        "event_type": event.event_type,
                        "event_hour": event.event_start.hour,
                        "num_riders_claiming": len(clean_claims),
                        "enrolled_riders": max(len(riders), 1),
                        "claims": [{"claim_id": item["claim"].id} for item in clean_claims],
                        "is_api_verified": bool((event.trigger_data or {}).get("is_api_verified", False)),
                    },
                )
                zone_response.raise_for_status()
                zone_body = zone_response.json()
                zone_flags = {
                    item["claim_id"]: item
                    for item in zone_body.get("claim_evaluations", [])
                    if item.get("flagged")
                }
            except Exception as exc:
                zone_flags = {}
                for item in clean_claims:
                    item["claim"].gate_results["zone_fraud_check_error"] = str(exc)

            for item in clean_claims:
                claim = item["claim"]
                rider = item["rider"]
                policy = item["policy"]
                if claim.id in zone_flags:
                    claim.status = "in_review"
                    claim.is_eligible = False
                    claim.ineligibility_reason = zone_flags[claim.id].get("reason")
                    claim.gate_results["fraud_review"] = {
                        "zone_flagged": True,
                        "reason": zone_flags[claim.id].get("reason"),
                    }
                    flagged_count += 1
                    continue

                recent_claim_count_result = await db_session.execute(
                    select(Claim).where(
                        and_(
                            Claim.rider_id == rider.id,
                            Claim.created_at >= (event.event_start - timedelta(days=7)),
                        )
                    )
                )
                recent_claim_count = len(recent_claim_count_result.scalars().all())
                zone_recent_claims_result = await db_session.execute(
                    select(Claim).where(
                        and_(
                            Claim.rider_id.in_([x["rider"].id for x in clean_claims]),
                            Claim.created_at >= (event.event_start - timedelta(days=7)),
                        )
                    )
                )
                zone_recent_claims = len(zone_recent_claims_result.scalars().all())
                zone_recent_mean_claims = (
                    float(zone_recent_claims) / float(max(len(clean_claims), 1))
                )
                shift_start, shift_end = _extract_shift_window_bounds(item["eligibility"]["gate_details"])

                try:
                    rider_response = await client.post(
                        FRAUD_RIDER_ENDPOINT,
                        json={
                            "rider_id": rider.id,
                            "claim_amount": float(claim.final_payout or 0.0),
                            "weekly_cap": float(policy.weekly_payout_cap),
                            "disruption_zone_pincode": str(event.affected_zone),
                            "rider_zones": [str(zone_id) for zone_id in [rider.zone1_id, rider.zone2_id, rider.zone3_id] if zone_id],
                            "event_start_hour": event.event_start.hour,
                            "shift_start": shift_start,
                            "shift_end": shift_end,
                            "recent_claim_count_7days": recent_claim_count,
                            "zone_recent_mean_claims_7days": round(zone_recent_mean_claims, 3),
                            "event_id": str(event.id),
                            "already_claimed_event_ids": [],
                            "claim_id": claim.id,
                        },
                    )
                    rider_response.raise_for_status()
                    rider_body = rider_response.json()
                except Exception as exc:
                    rider_body = {
                        "recommended_status": "approved",
                        "reasons": [],
                        "signals": {"fraud_endpoint_error": str(exc)},
                    }

                claim.gate_results["fraud_review"] = {
                    "zone_flagged": False,
                    "recommended_status": rider_body.get("recommended_status"),
                    "reasons": rider_body.get("reasons", []),
                    "signals": rider_body.get("signals", {}),
                }

                if rider_body.get("recommended_status") != "approved":
                    claim.status = "in_review"
                    claim.is_eligible = False
                    claim.ineligibility_reason = "; ".join(rider_body.get("reasons", [])) or "Flagged for fraud review"
                    flagged_count += 1
                    continue

                claim.status = "approved"
                claim.is_eligible = True
                approved_count += 1

                payout_result = await disburse_payout(
                    claim_id=claim.id,
                    rider_id=rider.id,
                    amount=float(claim.final_payout or 0.0),
                    db_session=db_session,
                )
                claim.gate_results["disbursement"] = payout_result
                if payout_result["status"] == "completed":
                    claim.status = "paid"
                    paid_count += 1
                    total_payout += float(claim.final_payout or 0.0)
                else:
                    claim.status = "failed"

    event.processing_status = "processed"
    await db_session.commit()

    return {
        "event_id": event.id,
        "total_affected": len(riders),
        "claims_created": len(created_claims),
        "eligible": approved_count,
        "approved": approved_count,
        "paid": paid_count,
        "flagged": flagged_count,
        "rejected": rejected_count,
        "total_payout": round(total_payout, 2),
        "claims": [
            {
                "claim_id": claim.id,
                "rider_id": claim.rider_id,
                "status": claim.status,
                "final_payout": float(claim.final_payout or 0.0),
            }
            for claim in created_claims
        ],
    }
