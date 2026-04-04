"""
zone_risk.py

Two-layer zone risk multiplier engine:

  Layer 1 (always available): Hardcoded lookup table for the 15 seed pin codes.
                              Used immediately — unblocks Module 1 on Day 1.

  Layer 3 (after training):   XGBoost model loaded from models/zone_risk_model.pkl.
                              get_zone_risk() tries this first; if model doesn't
                              exist yet, silently falls back to Layer 1.

Interface contract (never changes regardless of which layer is active):
  get_zone_risk(pincode: str) -> float          single pin code → multiplier
  get_rider_zone_risk(pincodes: list) -> float  list of zones → weighted avg
  get_zone_risk_full(pincode: str) -> dict      multiplier + explanation
"""

import os
import pickle
import numpy as np

# ── Paths ─────────────────────────────────────────────────────────────────────
_MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "models", "zone_risk_model.pkl")
_model = None   # loaded lazily on first call


# ── Layer 1: Hardcoded lookup ─────────────────────────────────────────────────
# risk_score: manually assigned based on IMD/NDMA/CPCB historical data.
# See data/README.md for the evidence behind each value.

ZONE_RISK_TABLE: dict[str, dict] = {
    # Chennai
    "600017": {
        "area": "T. Nagar",       "city": "chennai", "risk": 1.10,
        "reason": "Moderate flood history, dense urban drainage issues",
    },
    "600020": {
        "area": "Adyar",          "city": "chennai", "risk": 1.05,
        "reason": "Riverine flooding risk from Adyar river, moderate",
    },
    "600032": {
        "area": "Velachery",      "city": "chennai", "risk": 1.15,
        "reason": "High flood history — submerged in 2015, 2021 Chennai floods",
    },
    "600028": {
        "area": "Mylapore",       "city": "chennai", "risk": 0.95,
        "reason": "Elevated terrain, better drainage, historically safer",
    },
    # Mumbai
    "400017": {
        "area": "Dharavi",        "city": "mumbai",  "risk": 1.35,
        "reason": "Very high flood risk — low-lying, poor drainage, 7 NDMA events in a decade",
    },
    "400050": {
        "area": "Bandra West",    "city": "mumbai",  "risk": 0.90,
        "reason": "Coastal but elevated; better civic infrastructure",
    },
    "400069": {
        "area": "Andheri",        "city": "mumbai",  "risk": 1.10,
        "reason": "Underpass flooding during heavy rain, moderate risk",
    },
    # Bangalore
    "560034": {
        "area": "Koramangala",    "city": "bangalore", "risk": 0.85,
        "reason": "Stable zone, good drainage, low historical disruptions",
    },
    "560011": {
        "area": "Jayanagar",      "city": "bangalore", "risk": 0.90,
        "reason": "Established residential area, low flood frequency",
    },
    "560095": {
        "area": "HSR Layout",     "city": "bangalore", "risk": 1.00,
        "reason": "Some waterlogging events, near Bellandur lake",
    },
    # Delhi
    "110001": {
        "area": "Connaught Place", "city": "delhi",   "risk": 1.20,
        "reason": "High civic disruption frequency, monsoon waterlogging",
    },
    "110019": {
        "area": "South Delhi",     "city": "delhi",   "risk": 1.00,
        "reason": "Average risk — mixed history of disruptions",
    },
    "110045": {
        "area": "Dwarka",          "city": "delhi",   "risk": 1.10,
        "reason": "Flood-prone low-lying sectors, moderate risk",
    },
    # Pune
    "411038": {
        "area": "Kothrud",         "city": "pune",    "risk": 0.85,
        "reason": "Historically stable, elevated, low flood frequency",
    },
    "411001": {
        "area": "Shivajinagar",    "city": "pune",    "risk": 1.00,
        "reason": "Central area, moderate civic disruption risk",
    },
}


# ── Model loader ──────────────────────────────────────────────────────────────

def _load_model():
    """Lazy-loads XGBoost model. Returns None if model file not found."""
    global _model
    if _model is not None:
        return _model
    try:
        with open(_MODEL_PATH, "rb") as f:
            _model = pickle.load(f)
        print(f"[zone_risk] XGBoost model loaded from {_MODEL_PATH}")
    except FileNotFoundError:
        print("[zone_risk] Model not found — using hardcoded lookup table (Layer 1)")
        _model = None
    return _model


def _predict_with_model(pincode: str) -> float | None:
    """
    Tries to get a risk score from XGBoost.
    Returns None if model isn't available or pincode isn't in features.
    """
    model = _load_model()
    if model is None:
        return None

    # The XGBoost model was trained on zone features, not raw pincodes.
    # For inference, we use the same feature vector stored alongside the model.
    # If pincode not in model's known zones, return None (fall through to lookup).
    feature_map = getattr(model, "_pincode_features", {})
    if pincode not in feature_map:
        return None

    features = np.array(feature_map[pincode]).reshape(1, -1)
    prediction = model.predict(features)[0]
    # Clamp to valid range
    return float(np.clip(prediction, 0.80, 1.50))


# ── Public API ────────────────────────────────────────────────────────────────

def get_zone_risk(pincode: str) -> float:
    """
    Returns the zone risk multiplier for a single pin code.

    Priority order:
      1. XGBoost model (if trained and pincode in model's feature map)
      2. Hardcoded lookup table
      3. Safe default 1.00

    Args:
        pincode: 6-digit pin code string (e.g. "600017")

    Returns:
        Risk multiplier float between 0.80 and 1.50.
    """
    # Try model first
    ml_score = _predict_with_model(pincode)
    if ml_score is not None:
        return round(ml_score, 2)

    # Fallback to hardcoded table
    zone = ZONE_RISK_TABLE.get(pincode)
    if zone:
        return zone["risk"]

    # Unknown pincode — safe default
    return 1.00


def get_rider_zone_risk(zone_pincodes: list[str]) -> float:
    """
    Weighted average risk across a rider's zones.

    The first zone in the list is assumed to be the primary zone (most hours
    worked) and gets higher weight. Weights: 50% / 30% / 20% for top 3 zones.
    If fewer zones provided, weights are normalised.

    Args:
        zone_pincodes: Ordered list of pin codes (most-visited first)

    Returns:
        Weighted average risk multiplier.
    """
    if not zone_pincodes:
        return 1.00

    weights_map = {0: 0.50, 1: 0.30, 2: 0.20}
    risks, weights = [], []

    for i, pincode in enumerate(zone_pincodes[:3]):
        risks.append(get_zone_risk(pincode))
        weights.append(weights_map.get(i, 0.20))

    # Normalise weights in case fewer than 3 zones
    total_weight = sum(weights)
    normalised = [w / total_weight for w in weights]

    weighted_avg = sum(r * w for r, w in zip(risks, normalised))
    return round(weighted_avg, 2)


def get_zone_risk_full(pincode: str) -> dict:
    """
    Returns the risk multiplier along with a human-readable explanation.
    Used for:
      - Admin dashboard zone risk heatmap
      - Rider-facing premium breakdown ("why does your zone cost more?")
      - Judges reviewing the AI output

    Returns:
        {
            "pincode": "600032",
            "area": "Velachery",
            "city": "chennai",
            "risk_multiplier": 1.15,
            "risk_label": "High Risk",
            "reason": "High flood history — submerged in 2015, 2021 Chennai floods",
            "source": "xgboost_model"  or  "lookup_table"  or  "default"
        }
    """
    ml_score = _predict_with_model(pincode)
    source = "xgboost_model" if ml_score is not None else None

    zone_data = ZONE_RISK_TABLE.get(pincode)

    if ml_score is not None:
        risk = round(ml_score, 2)
        area = zone_data["area"] if zone_data else "Unknown area"
        city = zone_data["city"] if zone_data else "Unknown city"
        reason = zone_data["reason"] if zone_data else "ML model prediction"
    elif zone_data:
        risk = zone_data["risk"]
        area = zone_data["area"]
        city = zone_data["city"]
        reason = zone_data["reason"]
        source = "lookup_table"
    else:
        risk = 1.00
        area = "Unknown area"
        city = "Unknown city"
        reason = "Pin code not in database — default neutral risk applied"
        source = "default"

    return {
        "pincode": pincode,
        "area": area,
        "city": city,
        "risk_multiplier": risk,
        "risk_label": _risk_label(risk),
        "reason": reason,
        "source": source,
    }


def _risk_label(risk: float) -> str:
    if risk >= 1.30:
        return "Very High Risk"
    if risk >= 1.15:
        return "High Risk"
    if risk >= 1.00:
        return "Moderate Risk"
    if risk >= 0.90:
        return "Low Risk"
    return "Very Low Risk"