"""
fraud/detector.py
-----------------
ML-based fraud detection for RahatPay claims.

Uses an Ensemble of IsolationForest + LocalOutlierFactor (LOF) to detect
coordinated claim abuse (density fraud) during unverified disruptions.
If EITHER model flags an anomaly, the batch is sent to manual review.

Also provides an individual rider frequency check for standalone anomaly tracking.

Production-grade: uses Python logging, graceful model fallback, and
ensemble voting for higher detection accuracy.
"""

from __future__ import annotations
import os
import pickle
import logging
import pandas as pd
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger("rahatpay.fraud.detector")

# ── Paths & Models ─────────────────────────────────────────────────────────────
ROOT = os.path.join(os.path.dirname(__file__), "..")
IFOREST_PATH = os.path.join(ROOT, "models", "zone_fraud_iforest.pkl")
LOF_PATH = os.path.join(ROOT, "models", "zone_fraud_lof.pkl")

_iforest_model = None
_lof_model = None

def _get_iforest_model():
    """Lazy load the sklearn Isolation Forest model."""
    global _iforest_model
    if _iforest_model is None:
        if not os.path.exists(IFOREST_PATH):
            raise FileNotFoundError(f"IsolationForest model missing at {IFOREST_PATH}")
        with open(IFOREST_PATH, "rb") as f:
            _iforest_model = pickle.load(f)
        logger.info("IsolationForest model loaded from %s", IFOREST_PATH)
    return _iforest_model

def _get_lof_model():
    """Lazy load the sklearn Local Outlier Factor model."""
    global _lof_model
    if _lof_model is None:
        if not os.path.exists(LOF_PATH):
            logger.warning("LOF model missing at %s — falling back to IsolationForest only", LOF_PATH)
            return None
        with open(LOF_PATH, "rb") as f:
            _lof_model = pickle.load(f)
        logger.info("LOF model loaded from %s", LOF_PATH)
    return _lof_model

# ── Zone Batch Fraud (Ensemble Voting) ────────────────────────────────────────

def check_zone_fraud(event_id: int, claims: list[dict], is_api_verified: bool, enrolled_riders: int) -> list[dict]:
    """
    Evaluates a batch of claims using an ensemble of IsolationForest + LOF.
    If EITHER model detects an anomaly, ALL claims in the batch are flagged.

    Args:
        event_id: The ID of the disruption event.
        claims: List of dicts representing individual claims. Each must have a 'claim_id'.
        is_api_verified: Whether the trigger was verified by external API.
        enrolled_riders: Total riders enrolled in the affected zone.

    Returns:
        List of dicts: {"claim_id": X, "flagged": bool, "reason": str}
    """
    if is_api_verified:
        logger.info(
            "Zone fraud check skipped for event %s because trigger is API-verified.",
            event_id,
        )
        return [
            {
                "claim_id": c["claim_id"],
                "flagged": False,
                "reason": "skipped_api_verified_event",
            }
            for c in claims
        ]

    iforest = _get_iforest_model()
    lof = _get_lof_model()

    claims_filed = len(claims)
    if enrolled_riders == 0 or claims_filed == 0:
        return [{"claim_id": c["claim_id"], "flagged": False, "reason": "clean"} for c in claims]

    claim_rate = round(claims_filed / enrolled_riders, 3)

    # Construct feature row matching training schema
    df = pd.DataFrame([{
        "total_enrolled_riders": enrolled_riders,
        "claims_filed": claims_filed,
        "claim_rate": claim_rate,
        "is_api_verified": int(is_api_verified),
        "hour_of_day": 12
    }])

    # ── Ensemble Voting ───────────────────────────────────────────────────
    if_pred = iforest.predict(df)[0]  # -1 = anomaly, 1 = normal
    if_anomaly = (if_pred == -1)

    lof_anomaly = False
    if lof is not None:
        lof_pred = lof.predict(df)[0]
        lof_anomaly = (lof_pred == -1)

    # If EITHER model flags it, the batch is suspicious
    is_anomaly = if_anomaly or lof_anomaly

    vote_detail = (
        f"IsolationForest={'ANOMALY' if if_anomaly else 'NORMAL'}, "
        f"LOF={'ANOMALY' if lof_anomaly else 'NORMAL' if lof is not None else 'UNAVAILABLE'}"
    )
    logger.info(
        "Zone fraud check for event %s: claim_rate=%.1f%%, ensemble=[%s], flagged=%s",
        event_id, claim_rate * 100, vote_detail, is_anomaly
    )

    results = []
    for c in claims:
        if is_anomaly:
            results.append({
                "claim_id": c["claim_id"],
                "flagged": True,
                "reason": (
                    f"Ensemble Anomaly Detected: Batch claim rate ({claim_rate * 100:.1f}%) "
                    f"flagged by [{vote_detail}] for unverified event."
                )
            })
        else:
            results.append({
                "claim_id": c["claim_id"],
                "flagged": False,
                "reason": "clean"
            })

    return results

# ── Individual Rider Frequency ────────────────────────────────────────────────

@dataclass
class FraudCheckResult:
    """Return value from check_rider_claim()."""
    rider_id:   int
    score:      float
    verdict:    str                  # "pass" | "review" | "flag"
    signals:    dict = field(default_factory=dict)
    reasons:    list[str] = field(default_factory=list)
    claim_id:   Optional[int] = None

    @property
    def recommended_status(self) -> str:
        return "approved" if self.verdict == "pass" else "in_review"

def check_rider_claim(
    rider_id: int,
    claim_amount: float,
    weekly_cap: float,
    disruption_zone_pincode: str,
    rider_zones: list[str],
    event_start_hour: int,
    shift_start: int,
    shift_end: int,
    recent_claim_count_7days: int,
    event_id: str,
    already_claimed_event_ids: list[str],
    zone_recent_mean_claims_7days: float = 0.0,
    claim_id: Optional[int] = None,
) -> FraudCheckResult:
    """
    Individual rider evaluation looking for frequency spikes, zone mismatches,
    and duplicate event claims.
    """
    reasons = []
    signals = {}
    flagged = False

    # Signal 1: High individual claim frequency vs zone baseline (Phase 3: 3x mean)
    if zone_recent_mean_claims_7days > 0:
        frequency_ratio = recent_claim_count_7days / zone_recent_mean_claims_7days
    else:
        # If no baseline exists, fail open to avoid penalizing sparse zones.
        frequency_ratio = 0.0

    if frequency_ratio >= 3.0:
        flagged = True
        reasons.append(
            "High individual frequency: "
            f"{recent_claim_count_7days} claims in 7 days "
            f"({frequency_ratio:.2f}x zone mean {zone_recent_mean_claims_7days:.2f})."
        )
        signals["frequency_spike"] = {
            "claims_7d": recent_claim_count_7days,
            "zone_mean_claims_7d": round(zone_recent_mean_claims_7days, 3),
            "ratio_vs_zone_mean": round(frequency_ratio, 3),
        }

    # Signal 2: Zone mismatch
    if disruption_zone_pincode not in rider_zones:
        flagged = True
        reasons.append(f"Zone {disruption_zone_pincode} not in rider registered zones.")
        signals["zone_mismatch"] = True

    # Signal 3: Duplicate event claim
    if event_id in already_claimed_event_ids:
        flagged = True
        reasons.append("Duplicate event claim attempt.")
        signals["duplicate_event"] = True

    # Signal 4: Claim amount suspiciously close to weekly cap
    cap_ratio = claim_amount / weekly_cap if weekly_cap > 0 else 0
    if cap_ratio > 0.95:
        reasons.append(f"Claim amount is {cap_ratio * 100:.0f}% of weekly cap — near-cap claim.")
        signals["near_cap_claim"] = round(cap_ratio, 3)

    score = 0.8 if flagged else 0.1
    verdict = "flag" if flagged else "pass"

    logger.info(
        "Rider fraud check: rider=%s, score=%.2f, verdict=%s, signals=%s",
        rider_id, score, verdict, signals
    )

    return FraudCheckResult(
        rider_id=rider_id,
        claim_id=claim_id,
        score=score,
        verdict=verdict,
        signals=signals,
        reasons=reasons
    )
