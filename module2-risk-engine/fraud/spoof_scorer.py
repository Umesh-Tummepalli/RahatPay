"""
fraud/spoof_scorer.py
---------------------
GPS and sensor fusion spoof detection using Gradient Boosting classifier for RahatPay.

Detects location spoofing via synthetic sensor payload analysis:
  - GPS accuracy (mock location apps report 50-200m, real GPS reports 5-20m)
  - Accelerometer variance (spoofed phone on table: ~0.05, real bike: 0.6+)
  - Gyroscope variance (similar patterns)
  - Magnetometer variance
  - Wi-Fi SSID count (mock location app tests often at home with 1-3 SSIDs)

Consumed by eligibility.py Gate 4 to reject claims from spoofed locations.
"""

from __future__ import annotations
import os
import pickle
import logging
import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger("rahatpay.fraud.spoof_scorer")

# ── Paths & Models ─────────────────────────────────────────────────────────────
ROOT = os.path.join(os.path.dirname(__file__), "..")
MODEL_PATH = os.path.join(ROOT, "models", "spoof_detector.pkl")

_model = None
_scaler = None

def _get_model():
    """Lazy load the trained Gradient Boosting spoof detector."""
    global _model
    if _model is None:
        if not os.path.exists(MODEL_PATH):
            logger.warning("Spoof detector model missing at %s — skipping spoof checks", MODEL_PATH)
            return None
        with open(MODEL_PATH, "rb") as f:
            _model = pickle.load(f)
        logger.info("Spoof detector model loaded from %s", MODEL_PATH)
    return _model

def _get_scaler():
    """Get scaler attached to model."""
    global _scaler
    model = _get_model()
    if model and hasattr(model, '_scaler'):
        _scaler = model._scaler
    return _scaler

# ── Thresholds ─────────────────────────────────────────────────────────────────
THRESHOLD_SUSPICIOUS = 0.40
THRESHOLD_SPOOF_LIKELY = 0.70

@dataclass
class SpoofCheckResult:
    """Return value from score_sensor_payload()."""
    rider_id: int
    score: float  # 0.0 – 1.0 (probability of spoofing)
    verdict: str  # "clean" | "suspicious" | "spoof_likely"
    signals: dict = field(default_factory=dict)
    reasons: list[str] = field(default_factory=list)

    @property
    def recommended_status(self) -> str:
        """Map verdict to claim status."""
        if self.verdict == "spoof_likely":
            return "rejected"
        elif self.verdict == "suspicious":
            return "in_review"
        else:
            return "approved"

def score_sensor_payload(rider_id: int, sensor_data: Optional[dict] = None) -> SpoofCheckResult:
    """
    Evaluates sensor snapshot through the Gradient Boosting Classifier.
    
    Args:
        rider_id: The rider's ID (for logging)
        sensor_data: Dict with sensor readings:
            - gps_accuracy (float, meters): GPS accuracy from expo-location
            - accel_variance (float, 0-1): variance of accelerometer magnitudes over 2sec
            - gyro_variance (float, 0-1): variance of gyroscope magnitudes
            - mag_variance (float, 0-1): variance of magnetometer magnitudes
            - wifi_ssid_count (int): number of visible Wi-Fi networks
    
    Returns:
        SpoofCheckResult with score (0-1 spoof probability) and verdict.
    
    If sensor_data is None (mobile app hasn't sent it yet):
        Returns clean result with 0.0 score to allow demo to continue without blocking.
    """
    
    if not sensor_data:
        logger.info("Sensor payload missing for rider %s — defaulting to clean", rider_id)
        return SpoofCheckResult(
            rider_id=rider_id,
            score=0.0,
            verdict="clean",
            signals={"sensor_data": "unavailable"},
            reasons=["Sensor payload missing, Gate 4 defaulted to pass."]
        )
    
    model = _get_model()
    scaler = _get_scaler()
    
    if model is None:
        logger.warning("Spoof detector model unavailable for rider %s", rider_id)
        return SpoofCheckResult(
            rider_id=rider_id,
            score=0.0,
            verdict="clean",
            signals={"model": "unavailable"},
            reasons=["Spoof detector model unavailable, defaulting to pass."]
        )
    
    # === Extract Features (defend against None values) ===
    gps_accuracy = float(sensor_data.get("gps_accuracy") or 50.0)
    accel_var = float(sensor_data.get("accel_variance") or 0.0)
    gyro_var = float(sensor_data.get("gyro_variance") or 0.0)
    mag_var = float(sensor_data.get("mag_variance") or 0.0)
    wifi_count = int(sensor_data.get("wifi_ssid_count") or 1)
    
    # Create feature vector matching training schema
    features = np.array([[
        gps_accuracy,
        accel_var,
        gyro_var,
        mag_var,
        wifi_count
    ]]).astype(np.float32)
    
    # === Normalize Features ===
    if scaler is not None:
        features_scaled = scaler.transform(features)
    else:
        features_scaled = features
    
    # === Get Spoof Probability ===
    spoof_probability = float(model.predict_proba(features_scaled)[0][1])
    
    # === Determine Verdict ===
    reasons = []
    signals_dict = {
        "gps_accuracy_meters": gps_accuracy,
        "accel_variance": round(accel_var, 3),
        "gyro_variance": round(gyro_var, 3),
        "mag_variance": round(mag_var, 3),
        "wifi_ssid_count": wifi_count,
    }
    
    if spoof_probability >= THRESHOLD_SPOOF_LIKELY:
        verdict = "spoof_likely"
        reasons.append(
            f"High spoof probability: {spoof_probability*100:.1f}% "
            f"(GPS Acc: {gps_accuracy}m, Accel Var: {accel_var:.3f}). "
            f"Mock location app signature detected."
        )
        logger.warning(
            "Spoof likely detected for rider %s: score=%.3f, gps=%s, accel=%.3f",
            rider_id, spoof_probability, gps_accuracy, accel_var
        )
    
    elif spoof_probability >= THRESHOLD_SUSPICIOUS:
        verdict = "suspicious"
        reasons.append(
            f"Anomaly pattern detected: {spoof_probability*100:.1f}% spoof probability. "
            f"Sending to manual review."
        )
        logger.info(
            "Spoof suspicious for rider %s: score=%.3f",
            rider_id, spoof_probability
        )
    
    else:
        verdict = "clean"
        logger.debug(
            "Spoof check passed for rider %s: score=%.3f",
            rider_id, spoof_probability
        )
    
    return SpoofCheckResult(
        rider_id=rider_id,
        score=round(spoof_probability, 3),
        verdict=verdict,
        signals=signals_dict,
        reasons=reasons,
    )

def batch_score_sensor_payloads(
    rider_sensor_pairs: list[tuple[int, Optional[dict]]]
) -> dict[int, SpoofCheckResult]:
    """
    Score multiple riders' sensor payloads in batch.
    
    Args:
        rider_sensor_pairs: List of (rider_id, sensor_data) tuples
    
    Returns:
        Dict mapping rider_id → SpoofCheckResult
    """
    results = {}
    for rider_id, sensor_data in rider_sensor_pairs:
        results[rider_id] = score_sensor_payload(rider_id, sensor_data)
    return results
