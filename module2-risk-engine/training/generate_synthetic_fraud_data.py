import os
import numpy as np
import pandas as pd

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT = os.path.join(os.path.dirname(__file__), "..")
DATA_DIR = os.path.join(ROOT, "data", "processed")
os.makedirs(DATA_DIR, exist_ok=True)

SPOOF_CSV = os.path.join(DATA_DIR, "spoofing_training_data.csv")
FRAUD_CSV = os.path.join(DATA_DIR, "zone_fraud_training_data.csv")

def generate_spoof_data(n_samples=15000):
    """Generates synthetic sensor snapshots for GPS Spoofing Classification."""
    np.random.seed(42)
    # 20% of data is spoofed
    is_spoof = np.random.choice([0, 1], p=[0.8, 0.2], size=n_samples)
    
    # Base features (Normal physical movement)
    gps_acc = np.random.uniform(2, 20, size=n_samples)
    accel = np.random.uniform(0.5, 3.0, size=n_samples)
    gyro = np.random.uniform(0.4, 2.5, size=n_samples)
    wifi = np.random.randint(3, 15, size=n_samples)
    
    # Overwrite signals for Spoof (Static/Mock Location App)
    spf_idx = is_spoof == 1
    gps_acc[spf_idx] = np.random.uniform(50, 300, size=spf_idx.sum())
    accel[spf_idx] = np.random.uniform(0.01, 0.08, size=spf_idx.sum())
    gyro[spf_idx] = np.random.uniform(0.01, 0.08, size=spf_idx.sum())
    wifi[spf_idx] = np.random.randint(1, 3, size=spf_idx.sum())
    
    df = pd.DataFrame({
        "rider_id": np.arange(1000, 1000 + n_samples),
        "gps_accuracy_meters": np.round(gps_acc, 1),
        "accelerometer_variance": np.round(accel, 3),
        "gyroscope_variance": np.round(gyro, 3),
        "wifi_ssid_count": wifi,
        "is_spoof": is_spoof
    })
    df.to_csv(SPOOF_CSV, index=False)
    print(f"Generated {n_samples} spoof data rows -> {SPOOF_CSV}")

def generate_fraud_data(n_samples=5000):
    """Generates synthetic claim batch data for Isolation Forest anomaly detection."""
    np.random.seed(42)
    # 5% of data represents organized mass-fraud events
    is_anomaly = np.random.choice([0, 1], p=[0.95, 0.05], size=n_samples)
    
    enrolled = np.random.randint(50, 500, size=n_samples)
    is_api_verified = np.random.choice([True, False], p=[0.4, 0.6], size=n_samples)
    hour = np.random.randint(0, 24, size=n_samples)
    
    # Normal patterns: usually 20-50% claim rate during disruptions
    claim_r = np.random.uniform(0.2, 0.5, size=n_samples)
    
    # Anomalous patterns: Unverified event + highly coordinated claim spike (> 80%)
    anm_idx = is_anomaly == 1
    is_api_verified[anm_idx] = False
    claim_r[anm_idx] = np.random.uniform(0.75, 0.95, size=anm_idx.sum())
    
    claims = np.floor(enrolled * claim_r).astype(int)
    
    df = pd.DataFrame({
        "disruption_event_id": np.arange(1, n_samples + 1),
        "total_enrolled_riders": enrolled,
        "claims_filed": claims,
        "claim_rate": np.round(claims / enrolled, 3),
        "is_api_verified": is_api_verified,
        "hour_of_day": hour,
        "is_anomaly": is_anomaly # We include this specifically to eval our unsupervised clustering later
    })
    df.to_csv(FRAUD_CSV, index=False)
    print(f"Generated {n_samples} fraud data rows -> {FRAUD_CSV}")

if __name__ == "__main__":
    generate_spoof_data()
    generate_fraud_data()
