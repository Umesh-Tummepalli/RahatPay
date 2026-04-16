"""
training/train_spoof_detector_gpu.py

Trains GradientBoostingClassifier for GPS location spoofing detection.
Uses sensor fusion data (GPS accuracy, accelerometer, gyroscope, magnetometer, Wi-Fi).

Real locations: GPS accurate + high sensor variance (moving bike)
Spoofed locations: GPS inaccurate + low sensor variance (stationary phone)

Run:
    python training/train_spoof_detector_gpu.py

Output:
    models/spoof_detector.pkl (GradientBoosting classifier, ~50KB)
    models/spoof_model_metrics.txt (training statistics)
"""

import os
import pickle
import numpy as np
import pandas as pd
import json
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import confusion_matrix, roc_auc_score, roc_curve, precision_recall_curve
from sklearn.metrics import precision_score, recall_score, f1_score

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT = os.path.join(os.path.dirname(__file__), "..")
MODELS_DIR = os.path.join(ROOT, "models")
os.makedirs(MODELS_DIR, exist_ok=True)

SPOOF_MODEL_PATH = os.path.join(MODELS_DIR, "spoof_detector.pkl")
METRICS_PATH = os.path.join(MODELS_DIR, "spoof_model_metrics.txt")

# ═══════════════════════════════════════════════════════════════════════════════
# SYNTHETIC SENSOR DATA GENERATION
# ═══════════════════════════════════════════════════════════════════════════════

def generate_sensor_training_data(n_samples: int = 1000, seed: int = 42) -> tuple:
    """
    Generate synthetic sensor signatures for real vs spoofed locations.
    
    Real Location Characteristics:
      - GPS accuracy: 5-20m (real GPS chipset)
      - Accelerometer variance: high (0.6-1.0) from bike motion
      - Gyroscope variance: high (0.3-0.8) from bike steering
      - Magnetometer variance: high (0.2-0.6) from environment
      - Wi-Fi SSIDs: moderate-high (4-10) along delivery routes
    
    Spoofed Location Characteristics (Android mock location apps):
      - GPS accuracy: 50-200m (poor spoofing quality)
      - Accelerometer variance: very low (0.01-0.1) phone on table
      - Gyroscope variance: very low (0.01-0.05) stationary
      - Magnetometer variance: very low (0.01-0.1) consistent environment
      - Wi-Fi SSIDs: low (1-3) at fixed location
    """
    rng = np.random.default_rng(seed=seed)
    
    n_real = int(n_samples * 0.70)
    n_spoofed = n_samples - n_real
    
    X_real = []
    X_spoofed = []
    
    # === REAL LOCATIONS ===
    for _ in range(n_real):
        # Rider on bike, GPS working normally
        gps_accuracy = rng.uniform(5, 20)  # meters
        accel_var = rng.uniform(0.60, 1.0)  # High variance from motion
        gyro_var = rng.uniform(0.30, 0.8)  # Steering motion
        mag_var = rng.uniform(0.20, 0.6)  # Environmental changes
        wifi_count = rng.integers(4, 11)  # 4-10 SSIDs
        
        X_real.append([gps_accuracy, accel_var, gyro_var, mag_var, wifi_count])
    
    # === SPOOFED LOCATIONS ===
    for _ in range(n_spoofed):
        # Phone on table, GPS mocked with app
        gps_accuracy = rng.uniform(50, 200)  # Very poor accuracy
        accel_var = rng.uniform(0.01, 0.1)  # Near-zero from stationary phone
        gyro_var = rng.uniform(0.01, 0.05)  # Essentially zero
        mag_var = rng.uniform(0.01, 0.1)  # Consistent environment
        wifi_count = rng.integers(1, 4)  # 1-3 SSIDs (home network)
        
        X_spoofed.append([gps_accuracy, accel_var, gyro_var, mag_var, wifi_count])
    
    X = np.vstack([X_real, X_spoofed]).astype(np.float32)
    y = np.hstack([
        np.zeros(n_real),      # 0 = real
        np.ones(n_spoofed),    # 1 = spoofed
    ])
    
    # Shuffle
    shuffle_idx = rng.permutation(len(X))
    X = X[shuffle_idx]
    y = y[shuffle_idx]
    
    return X, y

# ═══════════════════════════════════════════════════════════════════════════════
# TRAINING
# ═══════════════════════════════════════════════════════════════════════════════

def train_spoof_detector():
    """Train GradientBoosting classifier for GPS spoof detection."""
    
    print("\n" + "=" * 85)
    print("📍 GPS SPOOF DETECTOR — SENSOR FUSION CLASSIFICATION")
    print("=" * 85)
    print()
    
    # === STEP 1: Generate Sensor Data ===
    print("📊 Generating synthetic sensor training data...")
    X, y = generate_sensor_training_data(n_samples=1000, seed=42)
    print(f"✅ Generated {len(X)} sensor signatures")
    print(f"   Real locations (0): {(y == 0).sum()}")
    print(f"   Spoofed locations (1): {(y == 1).sum()}")
    print()
    
    # === STEP 2: Train/Test Split ===
    print("🔀 Creating train/test split...")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    print(f"   Train: {len(X_train)} samples")
    print(f"   Test: {len(X_test)} samples")
    print()
    
    # === STEP 3: Feature Normalization ===
    print("⚙️  Normalizing features...")
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train).astype(np.float32)
    X_test_scaled = scaler.transform(X_test).astype(np.float32)
    
    print("✅ Features normalized")
    print("   Features:")
    print("   - gps_accuracy (meters)")
    print("   - accelerometer_variance (0-1)")
    print("   - gyroscope_variance (0-1)")
    print("   - magnetometer_variance (0-1)")
    print("   - wifi_ssid_count (number)")
    print()
    
    # === STEP 4: Train Gradient Boosting ===
    print("🚀 Training GradientBoostingClassifier (high accuracy spoof detection)...")
    
    gb_model = GradientBoostingClassifier(
        n_estimators=150,           # More trees = higher accuracy
        learning_rate=0.05,         # Conservative learning
        max_depth=4,                # Moderate depth
        subsample=0.8,              # Row sampling
        max_features='sqrt',        # Feature sampling
        random_state=42,
        verbose=0,
    )
    
    gb_model.fit(X_train_scaled, y_train)
    
    # Evaluate
    gb_train_score = gb_model.score(X_train_scaled, y_train)
    gb_test_score = gb_model.score(X_test_scaled, y_test)
    
    print(f"✅ GradientBoosting trained")
    print(f"   Train accuracy: {gb_train_score:.4f}")
    print(f"   Test accuracy: {gb_test_score:.4f}")
    print()
    
    # === STEP 5: Cross-Validation ===
    print("🔄 Running 5-fold cross-validation...")
    cv_scores = cross_val_score(
        gb_model, X_train_scaled, y_train,
        cv=5, scoring='roc_auc'
    )
    print(f"✅ Cross-validation ROC-AUC: {cv_scores.mean():.4f} ± {cv_scores.std():.4f}")
    print()
    
    # === STEP 6: Predictions & Probabilities ===
    print("🎯 Evaluating on test set...")
    
    y_pred = gb_model.predict(X_test_scaled)
    y_pred_proba = gb_model.predict_proba(X_test_scaled)[:, 1]  # Probability of spoof
    
    # Confusion matrix
    tn, fp, fn, tp = confusion_matrix(y_test, y_pred).ravel()
    
    print("   Confusion Matrix:")
    print(f"   ┌───────────────┬──────────────────────┐")
    print(f"   │               │ Predicted            │")
    print(f"   │               │ Real │ Spoofed      │")
    print(f"   ├───────────────┼──────┼──────────────┤")
    print(f"   │ Actual        │ Real │ {tn:>4} │ {fp:>6} │")
    print(f"   │               │Spoofed│ {fn:>4} │ {tp:>6} │")
    print(f"   └───────────────┴──────┴──────────────┘")
    print()
    
    # Metrics
    precision = precision_score(y_test, y_pred, zero_division=0)
    recall = recall_score(y_test, y_pred, zero_division=0)
    f1 = f1_score(y_test, y_pred, zero_division=0)
    roc_auc = roc_auc_score(y_test, y_pred_proba)
    
    print(f"   Precision (catch spoofs): {precision:.4f}")
    print(f"   Recall (minimize false negatives): {recall:.4f}")
    print(f"   F1 Score: {f1:.4f}")
    print(f"   ROC-AUC: {roc_auc:.4f}")
    print()
    
    # === STEP 7: Feature Importance ===
    print("🎨 Feature Importances:")
    print("-" * 85)
    feature_names = ["gps_accuracy", "accel_variance", "gyro_variance", "mag_variance", "wifi_count"]
    importances = gb_model.feature_importances_
    
    for name, imp in sorted(zip(feature_names, importances), key=lambda x: -x[1]):
        bar_length = int(imp * 50)
        bar = "█" * bar_length + "░" * (50 - bar_length)
        print(f"   {name:<25} {imp:.3f}  {bar}")
    print()
    
    # === STEP 8: Sample Predictions ===
    print("✨ Sample Predictions (Sanity Check):")
    print("-" * 85)
    print(f"   {'Case':<20} {'GPS Acc':<12} {'Accel':<8} {'Gyro':<8} {'Result':<20}")
    print("   " + "-" * 75)
    
    # Sample 1: Real location
    real_sample = np.array([[12, 0.75, 0.55, 0.4, 7]]).astype(np.float32)
    real_scaled = scaler.transform(real_sample)
    real_prob = gb_model.predict_proba(real_scaled)[0][1]
    print(f"   {'Real Location':<20} {'12m':<12} {'0.75':<8} {'0.55':<8} {'Prob={:.2f} ✓'.format(real_prob):<20}")
    
    # Sample 2: Spoofed location
    spoof_sample = np.array([[100, 0.05, 0.03, 0.08, 2]]).astype(np.float32)
    spoof_scaled = scaler.transform(spoof_sample)
    spoof_prob = gb_model.predict_proba(spoof_scaled)[0][1]
    print(f"   {'Spoofed Location':<20} {'100m':<12} {'0.05':<8} {'0.03':<8} {'Prob={:.2f} ✓'.format(spoof_prob):<20}")
    print()
    
    # === STEP 9: Save Model ===
    print("💾 Saving spoof detector model...")
    
    # Attach metadata
    gb_model._feature_names = feature_names
    gb_model._scaler = scaler
    gb_model._training_date = datetime.now().isoformat()
    gb_model._test_accuracy = float(gb_test_score)
    gb_model._roc_auc = float(roc_auc)
    
    with open(SPOOF_MODEL_PATH, "wb") as f:
        pickle.dump(gb_model, f)
    print(f"✅ Model saved to {SPOOF_MODEL_PATH}")
    print(f"   File size: {os.path.getsize(SPOOF_MODEL_PATH) / 1024:.1f} KB")
    print()
    
    # === STEP 10: Save Metrics ===
    print("📊 Saving metrics...")
    
    metrics = {
        "training_date": datetime.now().isoformat(),
        "model_type": "GradientBoostingClassifier",
        "training_samples": len(X_train),
        "test_samples": len(X_test),
        "features": feature_names,
        "cross_validation": {
            "roc_auc_mean": float(cv_scores.mean()),
            "roc_auc_std": float(cv_scores.std()),
        },
        "test_metrics": {
            "accuracy": float(gb_test_score),
            "precision": float(precision),
            "recall": float(recall),
            "f1_score": float(f1),
            "roc_auc": float(roc_auc),
        },
        "confusion_matrix": {
            "true_negatives": int(tn),
            "false_positives": int(fp),
            "false_negatives": int(fn),
            "true_positives": int(tp),
        },
        "feature_importance": {feat: float(imp) for feat, imp in zip(feature_names, importances)},
    }
    
    with open(METRICS_PATH, "w") as f:
        json.dump(metrics, f, indent=2)
    print(f"✅ Metrics saved to {METRICS_PATH}")
    print()
    
    # === SUMMARY ===
    print("=" * 85)
    print("✨ GPS SPOOF DETECTOR TRAINING COMPLETE ✨")
    print("=" * 85)
    print(f"🎯 Accuracy: {gb_test_score:.4f} ({gb_test_score*100:.1f}%)")
    print(f"🎯 Spoof Detection Recall: {recall:.4f} (catches {recall*100:.1f}% of spoofs)")
    print(f"💾 Model saved: {os.path.basename(SPOOF_MODEL_PATH)}")
    print()

if __name__ == "__main__":
    train_spoof_detector()
