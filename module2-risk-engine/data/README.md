# Module 2 — Data Sources & Methodology

This document explains where every number in `zone_features.csv` comes from.
Judges reviewing this module should read this before looking at the training code.

---

## Why We Have a Training Dataset

RahatPay's zone risk multiplier is not a hand-tuned lookup table.
It's a regression model trained to predict how risky a delivery zone is
based on measurable historical data from four official sources.

The zone risk multiplier (0.80–1.50) feeds directly into every rider's weekly
premium — so it must be defensible, auditable, and free from arbitrary guesswork.

---

## Feature Columns

| Feature | Source | What It Measures |
|---|---|---|
| `avg_red_alert_days` | IMD (India Meteorological Department) | Average days per year where rainfall ≥ 115mm in 6 hours (Red Alert threshold) |
| `flood_events_per_decade` | NDMA (National Disaster Management Authority) | Declared flood events per district over the past 10 years |
| `avg_monsoon_rainfall_mm` | IMD Monthly Rainfall Normals | Average total rainfall (mm) during the primary monsoon months for that city |
| `aqi_exceedance_days` | CPCB (Central Pollution Control Board) | Days per year where AQI exceeds 200 (Severe category) |
| `heatwave_days` | IMD Heat Wave Bulletins | Days per year where temperature exceeds 42°C |
| `civic_disruptions_per_year` | News archive research + NDMA civic logs | Verified bandhs, hartals, curfews that halted delivery operations |

---

## Where to Download the Raw Data

### IMD Rainfall
- **URL:** https://imdpune.gov.in/lrfindex.php (district rainfall data portal)
- **Alternate:** https://data.gov.in → search "District Wise Rainfall"
- **What to download:** District-level monthly/daily rainfall normals, 2013–2024
- **Format:** CSV

### NDMA Disaster Logs
- **URL:** https://ndma.gov.in/en/disaster-data-statistics
- **What to download:** State/district level disaster incident reports
- **Format:** PDF tables (manually extract to CSV) or data.gov.in NDMA datasets

### CPCB AQI
- **URL:** https://cpcb.nic.in/National-Ambient-Air-Quality-Standards.php
- **Alternate:** https://app.cpcbccr.com/ccr/#/caaqm-dashboard-all/caaqm-landing
- **What to download:** Station-wise annual AQI summary
- **Format:** CSV/Excel

### Civic Disruptions
- **Method:** Manual research via Google News archives
- **Search terms used:** `"bandh" + city + year`, `"hartal" + city + year`, `"curfew" + city + year`
- **Cross-referenced with:** Government press releases, Wikipedia lists of major bandhs in India
- **Coverage:** 2015–2024 for Chennai, Mumbai, Bangalore, Delhi, Pune
- **Note:** This is the hardest data to find in structured form. Values in `zone_features.csv` are
  domain-estimated based on the above research and clearly labelled.

---

## Training Data Strategy

Since we're in Phase 2 (pre-deployment), we don't yet have real RahatPay claim data.
The training dataset is built using a **synthetic augmentation** approach:

1. **15 seed zones** are manually profiled using the real data sources above.
   Each seed zone gets one row with 6 real/estimated features and a manually assigned
   risk label (0.80–1.50) based on the evidence.

2. **Synthetic augmentation** creates ~16 copies of each seed row with small Gaussian
   noise added to the features (std = 5% of each feature value). The label also
   receives tiny noise (±0.02) to prevent the model from memorising exact values.

3. This gives ~256 training rows — sufficient for a well-regularised XGBoost regressor
   on 6 features.

**From Phase 3 onward:** Real RahatPay claim and payout data will replace synthetic rows
using a warm-start transfer approach. The model improves as real data accumulates.

---

## Risk Score Labels — How They Were Assigned

Risk scores were assigned by weighing the four data sources according to the
product specification (same weights used in the zone risk multiplier formula):

| Data Source | Weight | Rationale |
|---|---|---|
| Weather history (IMD) | 40% | Most direct driver of delivery income loss |
| Disaster frequency (NDMA) | 25% | Severe events with multi-day platform suspension |
| Civic disruptions | 20% | Unpredictable but high-impact events |
| Environmental hazards | 15% | AQI, heatwave — smaller but real income risk |

A zone scoring high on the top two dimensions (weather + disasters) will
be rated 1.25–1.50. A zone scoring low on all four will be rated 0.80–0.90.

---

## Reproducibility

To regenerate the training dataset from scratch:

```bash
cd module2
python training/build_dataset.py   # → data/processed/zone_features.csv
python training/train_model.py     # → models/zone_risk_model.pkl
```

All random operations use `numpy.random.default_rng(seed=42)` — output is deterministic.