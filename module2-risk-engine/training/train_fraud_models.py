import os
import pickle
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor
from imblearn.over_sampling import SMOTE
import warnings
warnings.filterwarnings("ignore", category=UserWarning) # ignore LOF novelty warnings
import xgboost as xgb

ROOT = os.path.join(os.path.dirname(__file__), "..")
DATA_DIR = os.path.join(ROOT, "data", "processed")
MODELS_DIR = os.path.join(ROOT, "models")
os.makedirs(MODELS_DIR, exist_ok=True)

SPOOF_CSV = os.path.join(DATA_DIR, "spoofing_training_data.csv")
FRAUD_CSV = os.path.join(DATA_DIR, "zone_fraud_training_data.csv")
IFOREST_MODEL_PATH = os.path.join(MODELS_DIR, "zone_fraud_iforest.pkl")
LOF_MODEL_PATH = os.path.join(MODELS_DIR, "zone_fraud_lof.pkl")
XGB_SPOOF_MODEL_PATH = os.path.join(MODELS_DIR, "spoof_detector_xgb.pkl")

def train_ensemble_fraud_model():
    print("--- Training Zone Fraud Ensemble (Isolation Forest + LOF) ---")
    if not os.path.exists(FRAUD_CSV):
        raise FileNotFoundError(f"{FRAUD_CSV} missing.")
    
    df = pd.read_csv(FRAUD_CSV)
    
    features = ["total_enrolled_riders", "claims_filed", "claim_rate", "is_api_verified", "hour_of_day"]
    X = df[features].copy()
    X["is_api_verified"] = X["is_api_verified"].astype(int)
    
    # Train Isolation Forest
    clf_if = IsolationForest(n_estimators=100, contamination=0.05, random_state=42)
    clf_if.fit(X)
    
    # Train Local Outlier Factor (novelty=True allows scoring unseen data)
    clf_lof = LocalOutlierFactor(n_neighbors=20, novelty=True, contamination=0.05)
    clf_lof.fit(X)
    
    y_pred_if = clf_if.predict(X)
    y_pred_lof = clf_lof.predict(X)
    
    print(f"Isolation Forest anomalies: {(y_pred_if == -1).sum()} out of {len(df)}")
    print(f"LOF anomalies: {(y_pred_lof == -1).sum()} out of {len(df)}")
    
    with open(IFOREST_MODEL_PATH, "wb") as f:
        pickle.dump(clf_if, f)
    with open(LOF_MODEL_PATH, "wb") as f:
        pickle.dump(clf_lof, f)
    print(f"Ensemble Models saved -> {IFOREST_MODEL_PATH} & {LOF_MODEL_PATH}\n")

def train_xgb_spoof_scorer():
    print("--- Training GPS Spoof XGBoost Classifier ---")
    if not os.path.exists(SPOOF_CSV):
        raise FileNotFoundError(f"{SPOOF_CSV} missing.")
        
    df = pd.read_csv(SPOOF_CSV)
    features = ["gps_accuracy_meters", "accelerometer_variance", "gyroscope_variance", "wifi_ssid_count"]
    target = "is_spoof"
    
    X = df[features]
    y = df[target]
    
    # Inject SMOTE for minority class balancing
    print(f"Original class distribution:\n{y.value_counts().to_dict()}")
    smote = SMOTE(random_state=42)
    X_res, y_res = smote.fit_resample(X, y)
    print(f"Resampled class distribution (SMOTE):\n{y_res.value_counts().to_dict()}")
    
    # Train using hist and cuda for GTX 1650 performance
    model = xgb.XGBClassifier(
        n_estimators=200,
        max_depth=5,
        learning_rate=0.05,
        tree_method="hist",
        device="cuda",
        eval_metric="logloss",
        random_state=42
    )
    
    model.fit(X_res, y_res)
    
    # Eval
    acc = model.score(X_res, y_res)
    print(f"Training Accuracy: {acc * 100:.2f}%")
    
    # Save
    with open(XGB_SPOOF_MODEL_PATH, "wb") as f:
        pickle.dump(model, f)
    print(f"Model saved -> {XGB_SPOOF_MODEL_PATH}\n")

if __name__ == "__main__":
    train_ensemble_fraud_model()
    train_xgb_spoof_scorer()
