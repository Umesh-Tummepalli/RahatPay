"""
routes/fraud.py

API endpoints for fraud detection and ML model management in Module 2.

Endpoints:
  POST /api/fraud/check-zone          → Zone-level anomaly detection
  POST /api/fraud/check-rider         → Individual rider frequency check
  POST /api/fraud/score-spoof         → GPS spoof detection  
  GET /api/model/info                 → Model metadata and performance
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List
import logging
import json
import os

from fraud.detector import check_zone_fraud, check_rider_claim, FraudCheckResult
from fraud.spoof_scorer import score_sensor_payload, SpoofCheckResult

logger = logging.getLogger("rahatpay.fraud_routes")

router = APIRouter(prefix="/api/fraud", tags=["fraud"])
model_router = APIRouter(prefix="/api", tags=["models"])

# ═════════════════════════════════════════════════════════════════════════════════
# REQUEST/RESPONSE MODELS
# ═════════════════════════════════════════════════════════════════════════════════

class ClaimData(BaseModel):
    """Individual claim in a batch."""
    claim_id: int
    rider_id: int
    amount: float

class ZoneFraudCheckRequest(BaseModel):
    """Request for zone-level fraud check."""
    event_id: int
    claims: List[ClaimData]
    is_api_verified: bool = False
    enrolled_riders: int

class ZoneFraudCheckResponse(BaseModel):
    """Response for zone fraud check."""
    event_id: int
    claims_analyzed: int
    flagged_count: int
    ensemble_verdict: str  # "clean" | "suspicious" | "anomaly"
    results: List[dict]

class RiderFraudCheckRequest(BaseModel):
    """Request for individual rider fraud check."""
    rider_id: int
    zone_id: int
    claim_amount: float
    weekly_cap: float = 1000.0
    recent_claim_count_7days: int = 0
    zone_recent_mean_claims_7days: float = 0.0
    event_id: Optional[str] = None
    already_claimed_event_ids: List[str] = Field(default_factory=list)

class RiderFraudCheckResponse(BaseModel):
    """Response for rider fraud check."""
    rider_id: int
    score: float
    verdict: str  # "pass" | "review" | "flag"
    signals: dict
    reasons: List[str]
    recommended_status: str  # "approved" | "in_review" | "rejected"

class SensorData(BaseModel):
    """Sensor readings from mobile app."""
    gps_accuracy: float
    accel_variance: float
    gyro_variance: float
    mag_variance: float
    wifi_ssid_count: int

class SpoofCheckRequest(BaseModel):
    """Request for GPS spoof detection."""
    rider_id: int
    sensor_data: Optional[SensorData] = None

class SpoofCheckResponse(BaseModel):
    """Response for spoof check."""
    rider_id: int
    spoof_probability: float  # 0.0-1.0
    verdict: str  # "clean" | "suspicious" | "spoof_likely"
    signals: dict
    reasons: List[str]
    gate4_pass: bool  # True if score < 0.7

# ═════════════════════════════════════════════════════════════════════════════════
# ZONE-LEVEL FRAUD CHECK
# ═════════════════════════════════════════════════════════════════════════════════

@router.post("/check-zone", response_model=ZoneFraudCheckResponse)
async def zone_fraud_check(request: ZoneFraudCheckRequest) -> ZoneFraudCheckResponse:
    """
    Detect zone-level coordinated claim abuse using ensemble IsolationForest + LOF.
    
    For API-verified events (real weather data): assumes mass claims are legitimate.
    For unverified events: flags anomalous claim density patterns.
    
    Args:
        event_id: Disruption event ID
        claims: List of claims to evaluate
        is_api_verified: Whether trigger came from real weather API
        enrolled_riders: Total riders in the zone
    
    Returns:
        Zone fraud analysis with per-claim flagging
    """
    logger.info(
        "Zone fraud check: event=%s, claims=%d, api_verified=%s, enrolled=%d",
        request.event_id, len(request.claims), request.is_api_verified, request.enrolled_riders
    )
    
    try:
        # Convert to detector format
        claims_list = [
            {"claim_id": c.claim_id, "rider_id": c.rider_id, "amount": c.amount}
            for c in request.claims
        ]
        
        # Run ensemble check
        results = check_zone_fraud(
            event_id=request.event_id,
            claims=claims_list,
            is_api_verified=request.is_api_verified,
            enrolled_riders=request.enrolled_riders
        )
        
        # Count flagged
        flagged_count = sum(1 for r in results if r.get("flagged", False))
        
        # Determine ensemble verdict
        if request.is_api_verified:
            ensemble_verdict = "clean"  # Trust API data
        elif flagged_count >= len(results) * 0.5:
            ensemble_verdict = "anomaly"
        elif flagged_count > 0:
            ensemble_verdict = "suspicious"
        else:
            ensemble_verdict = "clean"
        
        return ZoneFraudCheckResponse(
            event_id=request.event_id,
            claims_analyzed=len(request.claims),
            flagged_count=flagged_count,
            ensemble_verdict=ensemble_verdict,
            results=results
        )
    
    except Exception as e:
        logger.error("Zone fraud check error: %s", str(e))
        raise HTTPException(status_code=500, detail=f"Zone fraud check failed: {str(e)}")

# ═════════════════════════════════════════════════════════════════════════════════
# INDIVIDUAL RIDER FRAUD CHECK
# ═════════════════════════════════════════════════════════════════════════════════

@router.post("/check-rider", response_model=RiderFraudCheckResponse)
async def rider_fraud_check(request: RiderFraudCheckRequest) -> RiderFraudCheckResponse:
    """
    Detect individual rider anomalies:
      - High claim frequency (3x zone mean)
      - Zone mismatch
      - Duplicate event claims
      - Near-cap claim amounts
    
    Args:
        rider_id: The rider being evaluated
        zone_id: The zone affected by the disruption
        claim_amount: Amount rider is claiming
        recent_claim_count_7days: Rider's claims in last 7 days
        zone_recent_mean_claims_7days: Zone average for comparison
    
    Returns:
        Rider fraud verdict with signals
    """
    logger.info(
        "Rider fraud check: rider=%s, zone=%s, recent_claims=%d, zone_mean=%.2f",
        request.rider_id, request.zone_id, request.recent_claim_count_7days,
        request.zone_recent_mean_claims_7days
    )
    
    try:
        result: FraudCheckResult = check_rider_claim(
            rider_id=request.rider_id,
            claim_amount=request.claim_amount,
            weekly_cap=request.weekly_cap,
            disruption_zone_pincode=str(request.zone_id),
            rider_zones=[str(request.zone_id)],  # Simplified: assume current zone in rider zones
            event_start_hour=12,  # Could be passed in request if needed
            shift_start=8,
            shift_end=22,
            recent_claim_count_7days=request.recent_claim_count_7days,
            event_id=request.event_id or "",
            already_claimed_event_ids=request.already_claimed_event_ids,
            zone_recent_mean_claims_7days=request.zone_recent_mean_claims_7days,
        )
        
        return RiderFraudCheckResponse(
            rider_id=result.rider_id,
            score=result.score,
            verdict=result.verdict,
            signals=result.signals,
            reasons=result.reasons,
            recommended_status=result.recommended_status,
        )
    
    except Exception as e:
        logger.error("Rider fraud check error: %s", str(e))
        raise HTTPException(status_code=500, detail=f"Rider fraud check failed: {str(e)}")

# ═════════════════════════════════════════════════════════════════════════════════
# GPS SPOOF DETECTION
# ═════════════════════════════════════════════════════════════════════════════════

@router.post("/score-spoof", response_model=SpoofCheckResponse)
async def spoof_detection(request: SpoofCheckRequest) -> SpoofCheckResponse:
    """
    Detect GPS location spoofing via sensor fusion analysis.
    
    Runs Gradient Boosting classifier on sensor payload:
      - GPS accuracy (real: <20m, spoofed: >50m)
      - Accelerometer variance (real: >0.6, spoofed: <0.1)
      - Gyroscope variance (similar)
      - Magnetometer variance
      - Wi-Fi SSID count
    
    Args:
        rider_id: Rider ID
        sensor_data: Sensor readings from mobile app (optional)
    
    Returns:
        Spoof probability and verdict. Gate 4 rejects if probability > 0.7
    """
    logger.info("Spoof detection: rider=%s", request.rider_id)
    
    try:
        # Convert request to dict for spoof scorer
        sensor_dict = None
        if request.sensor_data:
            sensor_dict = {
                "gps_accuracy": request.sensor_data.gps_accuracy,
                "accel_variance": request.sensor_data.accel_variance,
                "gyro_variance": request.sensor_data.gyro_variance,
                "mag_variance": request.sensor_data.mag_variance,
                "wifi_ssid_count": request.sensor_data.wifi_ssid_count,
            }
        
        result: SpoofCheckResult = score_sensor_payload(
            rider_id=request.rider_id,
            sensor_data=sensor_dict
        )
        
        # Gate 4 decision: reject if spoof_probability > 0.7
        gate4_pass = result.score <= 0.7
        
        return SpoofCheckResponse(
            rider_id=result.rider_id,
            spoof_probability=result.score,
            verdict=result.verdict,
            signals=result.signals,
            reasons=result.reasons,
            gate4_pass=gate4_pass,
        )
    
    except Exception as e:
        logger.error("Spoof detection error: %s", str(e))
        raise HTTPException(status_code=500, detail=f"Spoof detection failed: {str(e)}")

# ═════════════════════════════════════════════════════════════════════════════════
# MODEL INFORMATION
# ═════════════════════════════════════════════════════════════════════════════════

class ModelMetadata(BaseModel):
    """Metadata for a trained model."""
    name: str
    type: str
    accuracy: Optional[float] = None
    training_date: Optional[str] = None
    features: List[str] = []

class ModelInfoResponse(BaseModel):
    """Response containing all model metadata."""
    models: List[ModelMetadata]

@model_router.get("/model/info", response_model=ModelInfoResponse)
async def get_model_info() -> ModelInfoResponse:
    """
    Get metadata about all trained ML models.
    
    Returns info on:
      - XGBoost zone risk model
      - IsolationForest + LOF fraud detectors
      - Gradient Boosting spoof detector
    """
    logger.info("Fetching model metadata...")
    
    models = []
    
    # === XGBoost Zone Risk Model ===
    try:
        metrics_path = os.path.join(
            os.path.dirname(__file__), "..", "models", "xgboost_metrics.txt"
        )
        if os.path.exists(metrics_path):
            with open(metrics_path, 'r') as f:
                xgb_metrics = json.load(f)
            models.append(ModelMetadata(
                name="XGBoost Zone Risk Predictor",
                type="Regression",
                accuracy=xgb_metrics['test_metrics']['r2'],
                training_date=xgb_metrics['training_date'],
                features=xgb_metrics['features']
            ))
    except Exception as e:
        logger.warning("Could not load XGBoost metadata: %s", e)
    
    # === Fraud Detection Ensemble ===
    try:
        metrics_path = os.path.join(
            os.path.dirname(__file__), "..", "models", "fraud_model_metrics.txt"
        )
        if os.path.exists(metrics_path):
            with open(metrics_path, 'r') as f:
                fraud_metrics = json.load(f)
            models.append(ModelMetadata(
                name="Fraud Detection Ensemble (IsolationForest + LOF)",
                type="Anomaly Detection",
                accuracy=fraud_metrics['ensemble_metrics']['test_accuracy'],
                training_date=fraud_metrics['training_date'],
                features=fraud_metrics['features']
            ))
    except Exception as e:
        logger.warning("Could not load fraud metrics: %s", e)
    
    # === Spoof Detector ===
    try:
        metrics_path = os.path.join(
            os.path.dirname(__file__), "..", "models", "spoof_model_metrics.txt"
        )
        if os.path.exists(metrics_path):
            with open(metrics_path, 'r') as f:
                spoof_metrics = json.load(f)
            models.append(ModelMetadata(
                name="GPS Spoof Detector (Gradient Boosting)",
                type="Classification",
                accuracy=spoof_metrics['test_metrics']['accuracy'],
                training_date=spoof_metrics['training_date'],
                features=spoof_metrics['features']
            ))
    except Exception as e:
        logger.warning("Could not load spoof detector metadata: %s", e)
    
    return ModelInfoResponse(models=models)
