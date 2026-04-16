## Module 2 — AI Risk Engine & Fraud Models

This service hosts premium pricing + Phase 3 fraud APIs used by Module 1 and Module 3.

### What it serves

- Premium endpoints: dynamic premium (`income x tier x zone x season`) and baseline lookup
- Fraud endpoints:
  - `POST /api/fraud/check-zone`: batch density anomaly check (skips API-verified events)
  - `POST /api/fraud/check-rider`: rider-level anomaly checks, including `3x zone mean` frequency rule
  - `POST /api/fraud/score-spoof`: sensor spoof probability scorer
- `GET /api/model/info`: runtime model metadata from actual model files (status, algorithm, last trained timestamp)

### Setup

```bash
pip install -r requirements.txt
```

### Model training flow

```bash
python training/build_dataset.py
python training/train_model.py
python training/train_fraud_models.py
```

Expected artifacts in `models/`:
- `zone_risk_model.pkl`
- `zone_fraud_iforest.pkl`
- `zone_fraud_lof.pkl` (optional ensemble member)
- `spoof_detector_xgb.pkl`

### Run tests

```bash
python -m pytest tests/ -v
```

### Start server

```bash
uvicorn main:app --reload --port 8002
```