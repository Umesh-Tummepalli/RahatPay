from __future__ import annotations

import os
from datetime import datetime, timezone

import razorpay
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.policy import Payout


def _get_client() -> razorpay.Client:
    key_id = os.getenv("RAZORPAY_KEY_ID")
    key_secret = os.getenv("RAZORPAY_KEY_SECRET")
    if not key_id or not key_secret:
        raise RuntimeError("Razorpay credentials are missing. Set RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET.")
    return razorpay.Client(auth=(key_id, key_secret))


async def disburse_payout(claim_id: int, rider_id: int, amount: float, db_session: AsyncSession) -> dict:
    existing_result = await db_session.execute(
        select(Payout).where(Payout.claim_id == claim_id).order_by(Payout.id.desc())
    )
    payout = existing_result.scalar_one_or_none()
    now = datetime.now(timezone.utc)

    if payout is None:
        payout = Payout(
            claim_id=claim_id,
            rider_id=rider_id,
            amount=round(float(amount), 2),
            gateway="razorpay",
            gateway_response={},
            status="initiated",
            initiated_at=now,
        )
        db_session.add(payout)
        await db_session.flush()

    try:
        client = _get_client()
        order = client.order.create(
            {
                "amount": int(round(float(amount) * 100)),
                "currency": "INR",
                "receipt": f"claim_{claim_id}",
                "notes": {
                    "claim_id": str(claim_id),
                    "rider_id": str(rider_id),
                },
            }
        )
        payout.amount = round(float(amount), 2)
        payout.gateway = "razorpay"
        payout.gateway_reference = order.get("id")
        payout.gateway_response = order
        payout.status = "success"
        payout.completed_at = now
        await db_session.flush()
        return {
            "payout_id": payout.id,
            "gateway_reference": payout.gateway_reference,
            "status": "completed",
            "amount": round(float(amount), 2),
        }
    except Exception as exc:
        payout.amount = round(float(amount), 2)
        payout.gateway = "razorpay"
        payout.gateway_response = {"error": str(exc)}
        payout.status = "failed"
        payout.completed_at = now
        await db_session.flush()
        return {
            "payout_id": payout.id,
            "gateway_reference": payout.gateway_reference,
            "status": "failed",
            "amount": round(float(amount), 2),
            "error": str(exc),
        }
