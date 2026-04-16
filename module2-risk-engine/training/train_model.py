"""
training/train_model.py

Trains the XGBoost zone risk regression model and saves it to models/.

Run AFTER build_dataset.py:
    cd module2
    python training/build_dataset.py    # produces data/processed/zone_features.csv
    python training/train_model.py      # produces models/zone_risk_model.pkl

The saved model file has an extra attribute (_pincode_features) attached to it.
This is a dict mapping pincode → feature vector, so zone_risk.py can do inference
on a known pincode without needing the full feature CSV at runtime.
"""

import os
import pickle
import pandas as pd
import numpy as np
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.metrics import mean_absolute_error, r2_score
from xgboost import XGBRegressor

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT = os.path.join(os.path.dirname(__file__), "..")
FEATURES_PATH = os.path.join(ROOT, "data", "processed", "zone_features.csv")
MODEL_PATH    = os.path.join(ROOT, "models", "zone_risk_model.pkl")
os.makedirs(os.path.join(ROOT, "models"), exist_ok=True)

FEATURE_COLS = [
    "avg_red_alert_days",
    "flood_events_per_decade",
    "avg_monsoon_rainfall_mm",
    "aqi_exceedance_days",
    "heatwave_days",
    "civic_disruptions_per_year",
]
LABEL_COL = "risk_score"


def train():
    # ── Load data ─────────────────────────────────────────────────────────────
    if not os.path.exists(FEATURES_PATH):
        raise FileNotFoundError(
            f"Training data not found at {FEATURES_PATH}\n"
            "Run: python training/build_dataset.py  first."
        )

    df = pd.read_csv(FEATURES_PATH)
    print(f"Loaded {len(df)} rows from {FEATURES_PATH}")

    X = df[FEATURE_COLS].values
    y = df[LABEL_COL].values

    # ── Train / test split ────────────────────────────────────────────────────
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.15, random_state=42
    )

    # ── Hyperparameter Optimization with GridSearchCV ─────────────────────────
    from sklearn.model_selection import GridSearchCV

    base_model = XGBRegressor(
        random_state=42,
        verbosity=0,
        tree_method="hist",
        device="cuda",  # Enforce GTX 1650 CUDA hardware
    )

    param_grid = {
        'n_estimators': [100, 150, 200],
        'max_depth': [3, 4, 5],
        'learning_rate': [0.01, 0.05, 0.1],
        'subsample': [0.8, 1.0],
        'colsample_bytree': [0.8, 1.0],
    }

    print("Running GridSearchCV on GTX 1650 to find optimal hyperparameters...")
    grid_search = GridSearchCV(
        estimator=base_model,
        param_grid=param_grid,
        cv=5,       # 5-fold cross-validation
        scoring='r2',
        verbose=1
    )

    # ── Final fit ─────────────────────────────────────────────────────────────
    grid_search.fit(X_train, y_train)

    print(f"\nBest parameters found: {grid_search.best_params_}")
    print(f"Best CV R² score: {grid_search.best_score_:.3f}")

    # Extract the optimal model for evaluation
    model = grid_search.best_estimator_

    # ── Test set evaluation ───────────────────────────────────────────────────
    y_pred = model.predict(X_test)
    y_pred_clamped = np.clip(y_pred, 0.80, 1.50)

    mae = mean_absolute_error(y_test, y_pred_clamped)
    r2  = r2_score(y_test, y_pred_clamped)
    print(f"\nTest set — MAE: {mae:.4f}  |  R²: {r2:.4f}")

    # ── Feature importances ───────────────────────────────────────────────────
    importances = model.feature_importances_
    print("\nFeature Importances:")
    for feat, imp in sorted(zip(FEATURE_COLS, importances), key=lambda x: -x[1]):
        bar = "*" * int(imp * 40)
        print(f"  {feat:<35} {imp:.3f}  {bar}")

    # ── Attach pincode → feature vector map ──────────────────────────────────
    # This lets zone_risk.py do inference at runtime without loading the CSV.
    # Only seed rows (not augmented) are stored — one canonical vector per zone.
    seed_df = df.drop_duplicates(subset=["pincode"], keep="first")
    pincode_features = {
        str(row["pincode"]): [row[col] for col in FEATURE_COLS]
        for _, row in seed_df.iterrows()
        if "pincode" in seed_df.columns
    }
    model._pincode_features = pincode_features
    print(f"\nPincode feature map attached for {len(pincode_features)} zones")

    # ── Validate predictions on known seed zones ──────────────────────────────
    print("\nPredictions on seed zones (sanity check):")
    print(f"  {'Pincode':<10} {'Area':<20} {'Actual':>8} {'Predicted':>10}")
    print("  " + "-" * 52)
    for _, row in seed_df.iterrows():
        features = np.array([row[col] for col in FEATURE_COLS]).reshape(1, -1)
        pred = float(np.clip(model.predict(features)[0], 0.80, 1.50))
        print(f"  {row.get('pincode',''):<10} {row.get('area',''):<20} {row[LABEL_COL]:>8.2f} {pred:>10.2f}")

    # ── Save model ────────────────────────────────────────────────────────────
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(model, f)
    print(f"\nModel saved to {MODEL_PATH}")
    print("Training complete.")


if __name__ == "__main__":
    train()