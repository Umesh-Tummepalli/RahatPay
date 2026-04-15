from __future__ import annotations

from typing import Any


async def disburse_payout(claim_id: int, rider_id: int, amount: float, db_session) -> dict[str, Any]:
    """
    Razorpay integration is intentionally deferred.
    This placeholder keeps processor contract stable for now.
    """
    return {
        "claim_id": claim_id,
        "rider_id": rider_id,
        "amount": round(float(amount or 0.0), 2),
        "status": "deferred",
        "gateway_reference": None,
        "message": "Razorpay integration deferred for current phase.",
    }

