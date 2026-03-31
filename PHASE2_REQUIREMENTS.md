# RahatPay — Phase 2 Implementation Guide
# 5-Module Requirements Document

---

## Project Folder Hierarchy

Everyone clones this repo. Each person works inside their assigned folder. Nobody touches another person's folder until integration day.

```
rahatpay/
├── README.md
├── docker-compose.yml              # (optional) for local dev
├── .gitignore
│
├── module1-registration/            # Person 1: Registration & Policy
│   ├── requirements.txt
│   ├── main.py                      # FastAPI app entry point
│   ├── config.py                    # DB connection, env vars
│   ├── db/
│   │   ├── schema.sql               # Full PostgreSQL schema
│   │   ├── seed.sql                 # Insert seed riders/zones
│   │   └── connection.py            # DB connection helper
│   ├── routes/
│   │   ├── auth.py                  # OTP login endpoints
│   │   ├── registration.py          # Rider registration endpoints
│   │   └── policy.py                # Policy CRUD endpoints
│   ├── models/
│   │   ├── rider.py                 # Rider Pydantic models
│   │   └── policy.py                # Policy Pydantic models
│   └── tests/
│       ├── test_registration.py
│       └── test_policy.py
│
├── module2-risk-engine/             # Person 2: Premium & Risk
│   ├── requirements.txt
│   ├── main.py                      # Can run standalone for testing
│   ├── premium/
│   │   ├── calculator.py            # The premium formula function
│   │   ├── zone_risk.py             # Zone risk lookup / XGBoost model
│   │   ├── seasonal.py              # Seasonal factor logic
│   │   └── guardrails.py            # Floor/ceiling enforcement
│   ├── baseline/
│   │   ├── profiler.py              # Rolling 4-week baseline calculator
│   │   └── provisional.py           # City-median fallback for new riders
│   ├── data/
│   │   ├── zone_risk_table.json     # Hardcoded zone multipliers (smart approach)
│   │   ├── city_medians.json        # City-level median incomes
│   │   └── seasonal_factors.json    # Month-wise seasonal multipliers
│   ├── routes/
│   │   └── premium.py               # Premium calculation endpoints
│   └── tests/
│       ├── test_premium.py
│       └── test_baseline.py
│
├── module3-triggers-claims/         # Person 3: Triggers & Claims
│   ├── requirements.txt
│   ├── main.py
│   ├── triggers/
│   │   ├── monitor.py               # Polling loop (background task)
│   │   ├── weather.py               # OpenWeatherMap integration
│   │   ├── aqi.py                   # CPCB AQI integration
│   │   ├── civic.py                 # Mock civic disruption trigger
│   │   └── severity.py              # Threshold → severity lookup table
│   ├── claims/
│   │   ├── eligibility.py           # 4-gate validator
│   │   ├── payout_calculator.py     # Lost hours × rate × severity
│   │   ├── cap_enforcer.py          # Weekly cap + safety ceiling
│   │   └── disbursement.py          # Razorpay test mode integration
│   ├── routes/
│   │   ├── triggers.py              # Trigger status endpoints
│   │   ├── claims.py                # Claim evaluation endpoints
│   │   └── admin.py                 # Simulate disruption endpoint
│   └── tests/
│       ├── test_triggers.py
│       ├── test_eligibility.py
│       └── test_payout.py
│
├── module4-mobile-app/              # Person 4: React Native App
│   ├── package.json
│   ├── App.js
│   ├── src/
│   │   ├── screens/
│   │   │   ├── LoginScreen.js
│   │   │   ├── RegisterStep1.js     # Partner ID
│   │   │   ├── RegisterStep2.js     # KYC (Aadhaar/PAN)
│   │   │   ├── RegisterStep3.js     # Tier selection
│   │   │   ├── DashboardScreen.js   # Home — tier, premium, zones
│   │   │   ├── PremiumBreakdown.js  # Formula visualization
│   │   │   ├── PayoutHistory.js     # Past claims and amounts
│   │   │   └── ClaimDetail.js       # Single claim gate results
│   │   ├── components/
│   │   │   ├── TierCard.js
│   │   │   ├── PremiumFormula.js
│   │   │   ├── ZoneMap.js
│   │   │   └── PayoutCard.js
│   │   ├── api/
│   │   │   └── client.js            # Axios/fetch wrapper, base URL config
│   │   └── config/
│   │       └── firebase.js          # Firebase Auth config
│   └── __tests__/
│       └── screens.test.js
│
├── module5-integration/             # Person 5: Data, Integration, Demo
│   ├── api-contract.md              # THE master API spec (Day 1 deliverable)
│   ├── seed_data/
│   │   ├── riders.json              # 10 pre-built rider profiles
│   │   ├── zones.json               # 10 pin codes with risk data
│   │   ├── activity_history.json    # 4 weeks of fake activity per rider
│   │   └── disruption_scenarios.json # 4 pre-built demo scenarios
│   ├── integration_tests/
│   │   ├── test_registration_flow.py
│   │   ├── test_premium_flow.py
│   │   ├── test_claim_flow.py
│   │   └── test_full_e2e.py
│   ├── demo/
│   │   ├── simulate_disruption.py   # Script to trigger demo scenario
│   │   └── demo_script.md           # Step-by-step video recording guide
│   └── postman/
│       └── rahatpay.postman_collection.json
```

---

## Git Branching Strategy

```
main (protected — nobody pushes directly)
├── module1/registration    ← Person 1's branch
├── module2/risk-engine     ← Person 2's branch
├── module3/triggers-claims ← Person 3's branch
├── module4/mobile-app      ← Person 4's branch
└── module5/integration     ← Person 5's branch
```

Each person works on their branch. When a module is ready, create a pull request to main. Person 5 (integration owner) reviews and merges. On integration day (Day 4), everyone pulls the latest main and tests together.

---

---

# MODULE 1 — Registration & Policy Management

**Owner:** Person 1
**Tech Stack:** Python 3.11, FastAPI, PostgreSQL, Firebase Admin SDK
**Install:** `pip install fastapi uvicorn psycopg2-binary firebase-admin pydantic`

---

## What You're Building

The identity and policy layer of the entire application. Every other module reads from your database tables. You own the schema, the registration flow, and the policy lifecycle. You are also the one who sets up the shared FastAPI app structure that Module 2 and Module 3 will plug their routes into.

---

## Database Schema (Your First Task — Do This Before Anything Else)

```sql
-- zones table: pre-populated with seed data
CREATE TABLE zones (
    pin_code VARCHAR(6) PRIMARY KEY,
    city VARCHAR(50) NOT NULL,
    area_name VARCHAR(100) NOT NULL,
    risk_multiplier DECIMAL(4,2) NOT NULL DEFAULT 1.00
        CHECK (risk_multiplier >= 0.80 AND risk_multiplier <= 1.50)
);

-- riders table
CREATE TABLE riders (
    rider_id SERIAL PRIMARY KEY,
    partner_id VARCHAR(50) UNIQUE NOT NULL,
    platform VARCHAR(20) NOT NULL CHECK (platform IN ('swiggy', 'zomato')),
    name VARCHAR(100) NOT NULL,
    aadhaar_last4 VARCHAR(4),
    pan VARCHAR(10),
    phone VARCHAR(10) NOT NULL,
    city VARCHAR(50) NOT NULL,
    tier VARCHAR(20) NOT NULL CHECK (tier IN ('kavach', 'suraksha', 'raksha')),
    zone1_pincode VARCHAR(6) REFERENCES zones(pin_code),
    zone2_pincode VARCHAR(6) REFERENCES zones(pin_code),
    zone3_pincode VARCHAR(6) REFERENCES zones(pin_code),
    baseline_weekly_income DECIMAL(10,2) DEFAULT 0,
    baseline_weekly_hours DECIMAL(5,1) DEFAULT 0,
    is_seasoning BOOLEAN DEFAULT TRUE,
    trust_score INTEGER DEFAULT 50 CHECK (trust_score >= 0 AND trust_score <= 100),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- policies table
CREATE TABLE policies (
    policy_id SERIAL PRIMARY KEY,
    rider_id INTEGER REFERENCES riders(rider_id),
    tier VARCHAR(20) NOT NULL,
    weekly_premium DECIMAL(10,2) NOT NULL CHECK (weekly_premium >= 15),
    premium_income_component DECIMAL(10,2),
    premium_tier_rate DECIMAL(5,4),
    premium_zone_risk DECIMAL(4,2),
    premium_seasonal_factor DECIMAL(4,2),
    weekly_payout_cap DECIMAL(10,2) NOT NULL,
    coverage_types VARCHAR(100) NOT NULL,
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'lapsed', 'cancelled')),
    cycle_start DATE NOT NULL,
    cycle_end DATE NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- disruption_events table (Module 3 writes, you just create the table)
CREATE TABLE disruption_events (
    event_id SERIAL PRIMARY KEY,
    zone_pincode VARCHAR(6) REFERENCES zones(pin_code),
    event_type VARCHAR(50) NOT NULL,
    severity VARCHAR(20) NOT NULL
        CHECK (severity IN ('moderate', 'severe_l1', 'severe_l2', 'extreme')),
    severity_rate DECIMAL(4,2) NOT NULL,
    source_api VARCHAR(50) NOT NULL,
    raw_value DECIMAL(10,2),
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP,
    duration_hours DECIMAL(4,1),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- claims table
CREATE TABLE claims (
    claim_id SERIAL PRIMARY KEY,
    rider_id INTEGER REFERENCES riders(rider_id),
    event_id INTEGER REFERENCES disruption_events(event_id),
    policy_id INTEGER REFERENCES policies(policy_id),
    disrupted_hours DECIMAL(4,1) NOT NULL,
    hourly_rate DECIMAL(10,2) NOT NULL,
    disrupted_income DECIMAL(10,2) NOT NULL,
    severity_rate DECIMAL(4,2) NOT NULL,
    gross_payout DECIMAL(10,2) NOT NULL,
    weekly_cap DECIMAL(10,2) NOT NULL,
    already_paid_this_week DECIMAL(10,2) DEFAULT 0,
    final_payout DECIMAL(10,2) NOT NULL
        CHECK (final_payout >= 0 AND final_payout <= 5000),
    gate1_zone_match BOOLEAN DEFAULT FALSE,
    gate2_shift_overlap BOOLEAN DEFAULT FALSE,
    gate3_platform_inactive BOOLEAN DEFAULT FALSE,
    gate4_sensor_verified BOOLEAN DEFAULT TRUE,
    all_gates_passed BOOLEAN DEFAULT FALSE,
    status VARCHAR(20) DEFAULT 'pending'
        CHECK (status IN ('pending', 'approved', 'rejected', 'in_review', 'paid')),
    rejection_reason TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- payouts table
CREATE TABLE payouts (
    payout_id SERIAL PRIMARY KEY,
    claim_id INTEGER REFERENCES claims(claim_id),
    rider_id INTEGER REFERENCES riders(rider_id),
    amount DECIMAL(10,2) NOT NULL CHECK (amount > 0 AND amount <= 5000),
    payment_method VARCHAR(20) DEFAULT 'upi',
    razorpay_payment_id VARCHAR(100),
    status VARCHAR(20) DEFAULT 'initiated'
        CHECK (status IN ('initiated', 'processing', 'completed', 'failed')),
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## API Endpoints You Must Build

### Auth

```
POST /api/auth/send-otp
    Request:  { "phone": "9876543210" }
    Response: { "success": true, "message": "OTP sent" }

POST /api/auth/verify-otp
    Request:  { "phone": "9876543210", "otp": "123456" }
    Response: { "success": true, "token": "jwt_token_here", "rider_id": null }
    Note: rider_id is null if phone not yet registered
```

### Registration

```
POST /api/rider/register
    Request: {
        "partner_id": "SWG-CHN-12345",
        "platform": "swiggy",
        "name": "Ravi Kumar",
        "phone": "9876543210",
        "aadhaar_last4": "4321",
        "city": "chennai",
        "zones": ["600017", "600020", "600032"],
        "tier": "suraksha"
    }
    Response: {
        "rider_id": 1,
        "name": "Ravi Kumar",
        "tier": "suraksha",
        "is_seasoning": true,
        "provisional_baseline": {
            "weekly_income": 3000,
            "weekly_hours": 50,
            "hourly_rate": 60,
            "source": "city_median_chennai"
        },
        "premium": {
            "weekly_amount": 72.45,
            "breakdown": {
                "baseline_income": 3000,
                "tier_rate": 0.018,
                "zone_risk": 1.10,
                "seasonal_factor": 1.15
            }
        },
        "policy_id": 1,
        "coverage": {
            "weekly_payout_cap": 1650,
            "types": ["environmental", "social"],
            "claim_speed": "6-12 hours"
        }
    }

    Logic:
    1. Validate partner_id format and uniqueness
    2. Validate all 3 zone pin codes exist in zones table
    3. Since new rider → is_seasoning = true → use city median baseline
    4. Call Module 2's premium calculator with the baseline + zones + tier
    5. Create rider record, then create policy record
    6. Return the full response
```

### Policy Management

```
GET /api/rider/{rider_id}/dashboard
    Response: {
        "rider_id": 1,
        "name": "Ravi Kumar",
        "tier": "suraksha",
        "premium_weekly": 72.45,
        "premium_breakdown": { ... },
        "zones": [
            { "pin_code": "600017", "area": "T. Nagar", "risk": 1.10 },
            { "pin_code": "600020", "area": "Adyar", "risk": 1.05 },
            { "pin_code": "600032", "area": "Velachery", "risk": 1.15 }
        ],
        "baseline": {
            "weekly_income": 3000,
            "weekly_hours": 50,
            "hourly_rate": 60,
            "source": "city_median"
        },
        "coverage": {
            "weekly_payout_cap": 1650,
            "already_paid_this_week": 0,
            "remaining_headroom": 1650
        },
        "policy_status": "active",
        "cycle_end": "2026-04-10"
    }

GET /api/rider/{rider_id}/payouts
    Response: {
        "rider_id": 1,
        "total_payouts": 2,
        "total_amount": 220.50,
        "payouts": [
            {
                "payout_id": 1,
                "date": "2026-03-25",
                "event_type": "heavy_rainfall",
                "severity": "severe_l1",
                "disrupted_hours": 3,
                "amount": 94.50,
                "status": "completed",
                "gates": {
                    "zone_match": true,
                    "shift_overlap": true,
                    "platform_inactive": true,
                    "sensor_verified": true
                }
            },
            ...
        ]
    }

GET /api/zones/available?city=chennai
    Response: {
        "city": "chennai",
        "zones": [
            { "pin_code": "600017", "area": "T. Nagar", "risk_multiplier": 1.10 },
            { "pin_code": "600020", "area": "Adyar", "risk_multiplier": 1.05 },
            ...
        ]
    }

GET /api/tiers
    Response: {
        "tiers": [
            {
                "id": "kavach",
                "name": "Kavach",
                "rate": 0.01,
                "payout_cap_pct": 0.35,
                "coverage": ["environmental"],
                "claim_speed": "24-48 hours",
                "trust_score_required": 0
            },
            {
                "id": "suraksha",
                "name": "Suraksha",
                "rate": 0.018,
                "payout_cap_pct": 0.55,
                "coverage": ["environmental", "social"],
                "claim_speed": "6-12 hours",
                "trust_score_required": 30
            },
            {
                "id": "raksha",
                "name": "Raksha",
                "rate": 0.025,
                "payout_cap_pct": 0.70,
                "coverage": ["environmental", "social", "composite"],
                "claim_speed": "2-4 hours",
                "trust_score_required": 60
            }
        ]
    }
```

---

## How to Unit Test This Module

Run the FastAPI server locally with a test PostgreSQL database. Use pytest + httpx:

```python
# test_registration.py
import httpx

BASE = "http://localhost:8000/api"

def test_register_rider():
    resp = httpx.post(f"{BASE}/rider/register", json={
        "partner_id": "SWG-CHN-99999",
        "platform": "swiggy",
        "name": "Test Rider",
        "phone": "9999999999",
        "aadhaar_last4": "1234",
        "city": "chennai",
        "zones": ["600017", "600020", "600032"],
        "tier": "suraksha"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["tier"] == "suraksha"
    assert data["premium"]["weekly_amount"] > 15  # above floor
    assert data["is_seasoning"] == True
    assert data["provisional_baseline"]["source"] == "city_median_chennai"

def test_duplicate_partner_id():
    # Register same partner_id twice → should fail
    resp = httpx.post(f"{BASE}/rider/register", json={...same as above...})
    assert resp.status_code == 409  # conflict

def test_invalid_zone():
    resp = httpx.post(f"{BASE}/rider/register", json={
        ...
        "zones": ["999999", "600020", "600032"],  # invalid pin
    })
    assert resp.status_code == 400

def test_dashboard():
    resp = httpx.get(f"{BASE}/rider/1/dashboard")
    assert resp.status_code == 200
    data = resp.json()
    assert "premium_weekly" in data
    assert "coverage" in data
    assert data["coverage"]["remaining_headroom"] >= 0
```

**Checklist before you call this module done:**
- [ ] PostgreSQL schema created and running
- [ ] Seed data inserted (zones + 10 riders from Module 5)
- [ ] POST /api/rider/register works and creates rider + policy
- [ ] GET /api/rider/{id}/dashboard returns all expected fields
- [ ] GET /api/rider/{id}/payouts returns empty list for new rider
- [ ] GET /api/zones/available returns zones for a city
- [ ] GET /api/tiers returns all 3 tiers with correct rates
- [ ] Duplicate partner_id is rejected
- [ ] Invalid zones are rejected
- [ ] Premium is calculated via Module 2's function (import it or call its endpoint)
- [ ] CHECK constraints on DB prevent bad data

---

---

# MODULE 2 — AI Risk Engine & Premium Calculator

**Owner:** Person 2
**Tech Stack:** Python 3.11, FastAPI (for standalone testing), pandas, scikit-learn (optional XGBoost)
**Install:** `pip install fastapi uvicorn pandas scikit-learn`

---

## What You're Building

The brain that prices every policy. You deliver two things: a zone risk multiplier for any pin code, and a complete premium calculation for any rider. Module 1 calls your functions when creating a policy. Module 3 calls your baseline profiler when calculating payouts.

---

## Smart Approach — Build in Layers

**Layer 1 (Day 1 — must have):** Hardcoded zone risk lookup table + pure-function premium calculator. This takes 2-3 hours and immediately unblocks Module 1.

**Layer 2 (Day 2 — should have):** Rolling baseline profiler that reads activity history and returns a rider's average income/hours/zones.

**Layer 3 (Day 3-4 — nice to have):** Replace the hardcoded table with a trained XGBoost model. Same input/output interface, just smarter internals.

---

## Files You Must Build

### zone_risk.py — Zone Risk Multiplier

```python
# Smart approach: hardcoded lookup table
# Same output format as the XGBoost model would produce
# Can be swapped for ML model later without changing the interface

ZONE_RISK_TABLE = {
    # Chennai
    "600017": {"area": "T. Nagar", "city": "chennai", "risk": 1.10},
    "600020": {"area": "Adyar", "city": "chennai", "risk": 1.05},
    "600032": {"area": "Velachery", "city": "chennai", "risk": 1.15},
    "600028": {"area": "Mylapore", "city": "chennai", "risk": 0.95},
    # Mumbai
    "400017": {"area": "Dharavi", "city": "mumbai", "risk": 1.35},
    "400050": {"area": "Bandra West", "city": "mumbai", "risk": 0.90},
    "400069": {"area": "Andheri", "city": "mumbai", "risk": 1.10},
    # Bangalore
    "560034": {"area": "Koramangala", "city": "bangalore", "risk": 0.85},
    "560011": {"area": "Jayanagar", "city": "bangalore", "risk": 0.90},
    # Delhi
    "110001": {"area": "Connaught Place", "city": "delhi", "risk": 1.20},
    "110019": {"area": "South Delhi", "city": "delhi", "risk": 1.00},
}

def get_zone_risk(pin_code: str) -> float:
    """Returns risk multiplier for a zone. Default 1.0 if unknown."""
    zone = ZONE_RISK_TABLE.get(pin_code)
    return zone["risk"] if zone else 1.00

def get_rider_zone_risk(zone_pincodes: list) -> float:
    """Average risk across rider's top zones."""
    risks = [get_zone_risk(z) for z in zone_pincodes]
    return round(sum(risks) / len(risks), 2)
```

### seasonal.py — Seasonal Factor

```python
SEASONAL_FACTORS = {
    1: 0.90,   # Jan — dry
    2: 0.90,   # Feb — dry
    3: 0.95,   # Mar — pre-summer
    4: 1.05,   # Apr — heat starts
    5: 1.10,   # May — peak heat
    6: 1.20,   # Jun — monsoon onset
    7: 1.25,   # Jul — peak monsoon
    8: 1.20,   # Aug — monsoon
    9: 1.15,   # Sep — monsoon tailing
    10: 1.05,  # Oct — post-monsoon
    11: 0.95,  # Nov — stable
    12: 0.90,  # Dec — dry/winter
}

def get_seasonal_factor(month: int = None) -> float:
    if month is None:
        from datetime import datetime
        month = datetime.now().month
    return SEASONAL_FACTORS.get(month, 1.00)
```

### calculator.py — The Premium Formula

```python
from .zone_risk import get_rider_zone_risk
from .seasonal import get_seasonal_factor
from .guardrails import apply_guardrails

TIER_RATES = {
    "kavach": 0.01,
    "suraksha": 0.018,
    "raksha": 0.025,
}

TIER_PAYOUT_CAPS = {
    "kavach": 0.35,
    "suraksha": 0.55,
    "raksha": 0.70,
}

def calculate_premium(
    baseline_weekly_income: float,
    tier: str,
    zone_pincodes: list,
    month: int = None
) -> dict:
    """
    The core premium formula.
    Returns premium amount + full breakdown.
    """
    tier_rate = TIER_RATES[tier]
    zone_risk = get_rider_zone_risk(zone_pincodes)
    seasonal = get_seasonal_factor(month)

    raw_premium = baseline_weekly_income * tier_rate * zone_risk * seasonal
    final_premium = apply_guardrails(raw_premium, baseline_weekly_income)

    payout_cap = baseline_weekly_income * TIER_PAYOUT_CAPS[tier]

    return {
        "weekly_amount": round(final_premium, 2),
        "breakdown": {
            "baseline_income": baseline_weekly_income,
            "tier_rate": tier_rate,
            "zone_risk": zone_risk,
            "seasonal_factor": seasonal,
            "raw_premium": round(raw_premium, 2),
        },
        "weekly_payout_cap": round(payout_cap, 2),
        "pct_of_income": round((final_premium / baseline_weekly_income) * 100, 2),
    }
```

### guardrails.py — Affordability Limits

```python
PREMIUM_FLOOR = 15.0       # Minimum ₹15/week
PREMIUM_CEILING_PCT = 0.035  # Maximum 3.5% of income

def apply_guardrails(raw_premium: float, baseline_income: float) -> float:
    ceiling = baseline_income * PREMIUM_CEILING_PCT
    premium = max(raw_premium, PREMIUM_FLOOR)
    premium = min(premium, ceiling)
    return round(premium, 2)
```

### profiler.py — Rolling Baseline

```python
CITY_MEDIANS = {
    "chennai": {"weekly_income": 3000, "weekly_hours": 50},
    "mumbai": {"weekly_income": 3500, "weekly_hours": 50},
    "bangalore": {"weekly_income": 3200, "weekly_hours": 48},
    "delhi": {"weekly_income": 2800, "weekly_hours": 45},
    "pune": {"weekly_income": 3000, "weekly_hours": 50},
}

def get_baseline(rider_id: int, city: str, is_seasoning: bool, db=None) -> dict:
    """
    Returns the rider's baseline income/hours.
    If seasoning, returns city median. Otherwise, calculates rolling 4-week average.
    """
    if is_seasoning:
        median = CITY_MEDIANS.get(city, {"weekly_income": 3000, "weekly_hours": 50})
        return {
            "weekly_income": median["weekly_income"],
            "weekly_hours": median["weekly_hours"],
            "hourly_rate": round(median["weekly_income"] / median["weekly_hours"], 2),
            "source": f"city_median_{city}"
        }

    # For demo: read from seeded activity_history
    # In production: query last 4 weeks of rider activity from DB
    # For now, return seeded data
    return {
        "weekly_income": 3500,
        "weekly_hours": 50,
        "hourly_rate": 70.0,
        "source": "rolling_4week"
    }
```

---

## API Endpoints (For Standalone Testing)

```
POST /api/premium/calculate
    Request: {
        "baseline_weekly_income": 3500,
        "tier": "suraksha",
        "zone_pincodes": ["600017", "600020", "600032"],
        "month": 7
    }
    Response: {
        "weekly_amount": 79.70,
        "breakdown": {
            "baseline_income": 3500,
            "tier_rate": 0.018,
            "zone_risk": 1.10,
            "seasonal_factor": 1.25,
            "raw_premium": 86.63
        },
        "weekly_payout_cap": 1925.00,
        "pct_of_income": 2.28
    }

GET /api/premium/zone-risk/{pin_code}
    Response: { "pin_code": "600017", "area": "T. Nagar", "risk_multiplier": 1.10 }

GET /api/baseline/{rider_id}
    Response: {
        "weekly_income": 3500,
        "weekly_hours": 50,
        "hourly_rate": 70.0,
        "source": "rolling_4week"
    }
```

---

## How to Unit Test

```python
# test_premium.py
from premium.calculator import calculate_premium

def test_ravi_premium():
    """Ravi from README: 3500 × 1.8% × 1.10 × 1.15 = ~80"""
    result = calculate_premium(
        baseline_weekly_income=3500,
        tier="suraksha",
        zone_pincodes=["600017", "600020", "600032"],
        month=7  # July monsoon
    )
    assert 70 <= result["weekly_amount"] <= 90
    assert result["weekly_payout_cap"] == 1925.0

def test_arjun_premium():
    """Arjun: 1400 × 1.0% × 0.85 × 0.90 = ~11 → clamped to 15"""
    result = calculate_premium(
        baseline_weekly_income=1400,
        tier="kavach",
        zone_pincodes=["560034"],  # Koramangala
        month=2  # February dry
    )
    assert result["weekly_amount"] == 15.0  # floor kicks in

def test_guardrail_ceiling():
    """High earner shouldn't exceed 3.5% of income"""
    result = calculate_premium(
        baseline_weekly_income=10000,
        tier="raksha",
        zone_pincodes=["400017"],  # Dharavi high risk
        month=7  # Monsoon
    )
    assert result["weekly_amount"] <= 10000 * 0.035
```

**Checklist:**
- [ ] calculate_premium returns correct result for Ravi (README example)
- [ ] calculate_premium returns correct result for Arjun (README example)
- [ ] Floor (₹15) activates for low premium calculations
- [ ] Ceiling (3.5%) activates for high-income + high-risk combos
- [ ] Zone risk lookup works for all 10+ seeded pin codes
- [ ] Seasonal factor changes by month
- [ ] Baseline profiler returns city median for seasoning riders
- [ ] Baseline profiler returns seeded data for established riders
- [ ] Module 1 can import and call calculate_premium directly

---

---

# MODULE 3 — Trigger Monitor & Claims Engine

**Owner:** Person 3
**Tech Stack:** Python 3.11, FastAPI, httpx (for API calls), Razorpay SDK
**Install:** `pip install fastapi uvicorn httpx razorpay python-dotenv`

---

## What You're Building

The engine room. You detect disruptions, evaluate claims, calculate payouts, and disburse money. This is the most complex module and the one that makes the product "parametric."

---

## Trigger Monitor — Background Polling

### weather.py — OpenWeatherMap Integration

```python
import httpx

OWM_API_KEY = "your_key_here"  # Free tier: 60 calls/min
OWM_BASE = "https://api.openweathermap.org/data/2.5"

MONITORED_ZONES = {
    "600017": {"lat": 13.0418, "lon": 80.2341},  # T. Nagar
    "400017": {"lat": 19.0176, "lon": 72.8562},   # Dharavi
    "560034": {"lat": 12.9352, "lon": 77.6245},   # Koramangala
    # ... add all seeded zones
}

async def check_weather(pin_code: str) -> dict:
    coords = MONITORED_ZONES[pin_code]
    resp = await httpx.AsyncClient().get(
        f"{OWM_BASE}/weather",
        params={"lat": coords["lat"], "lon": coords["lon"], "appid": OWM_API_KEY}
    )
    data = resp.json()
    rain_1h = data.get("rain", {}).get("1h", 0)
    temp = data["main"]["temp"] - 273.15  # Kelvin to Celsius
    return {"rain_mm": rain_1h, "temp_celsius": temp, "raw": data}
```

### aqi.py — CPCB AQI Integration

```python
# CPCB doesn't have a clean public API, so use this approach:
# Option A: Scrape from https://app.cpcbccr.com/AQI_India/
# Option B: Use OpenWeatherMap Air Pollution API (free tier)

async def check_aqi(pin_code: str) -> dict:
    coords = MONITORED_ZONES[pin_code]
    resp = await httpx.AsyncClient().get(
        f"http://api.openweathermap.org/data/2.5/air_pollution",
        params={"lat": coords["lat"], "lon": coords["lon"], "appid": OWM_API_KEY}
    )
    data = resp.json()
    aqi = data["list"][0]["main"]["aqi"]  # 1-5 scale
    pm25 = data["list"][0]["components"]["pm2_5"]
    # Convert to Indian AQI scale (approximate)
    indian_aqi = int(pm25 * 2.5)  # rough approximation
    return {"aqi": indian_aqi, "pm25": pm25}
```

### severity.py — Threshold-to-Severity Lookup

```python
SEVERITY_RATES = {
    "moderate": 0.30,
    "severe_l1": 0.45,
    "severe_l2": 0.60,
    "extreme": 0.75,
}

def classify_rainfall(mm_6hr: float) -> tuple:
    """Returns (severity, rate) or (None, None) if below threshold."""
    if mm_6hr >= 115:
        return "severe_l2", 0.60
    elif mm_6hr >= 65:
        return "severe_l1", 0.45
    elif mm_6hr >= 35:
        return "moderate", 0.30
    return None, None

def classify_heat(temp_celsius: float, duration_hours: float) -> tuple:
    if temp_celsius > 42 and duration_hours >= 3:
        return "moderate", 0.30
    return None, None

def classify_aqi(aqi_value: int) -> tuple:
    if aqi_value > 300:
        return "severe_l1", 0.45
    elif aqi_value > 200:
        return "moderate", 0.30
    return None, None
```

### monitor.py — Polling Loop

```python
from fastapi import BackgroundTasks
import asyncio

POLL_INTERVAL = 60  # seconds

async def trigger_polling_loop():
    """Runs continuously, checking all zones every 60 seconds."""
    while True:
        for pin_code in MONITORED_ZONES:
            weather = await check_weather(pin_code)
            aqi = await check_aqi(pin_code)

            # Check rainfall
            rain_severity, rain_rate = classify_rainfall(weather["rain_mm"] * 6)
            if rain_severity:
                await create_disruption_event(pin_code, "rainfall", rain_severity, rain_rate, weather["rain_mm"])

            # Check AQI
            aqi_severity, aqi_rate = classify_aqi(aqi["aqi"])
            if aqi_severity:
                await create_disruption_event(pin_code, "air_quality", aqi_severity, aqi_rate, aqi["aqi"])

            # Check heat
            heat_severity, heat_rate = classify_heat(weather["temp_celsius"], 3)
            if heat_severity:
                await create_disruption_event(pin_code, "extreme_heat", heat_severity, heat_rate, weather["temp_celsius"])

        await asyncio.sleep(POLL_INTERVAL)
```

---

## Claims Engine

### eligibility.py — 4-Gate Validator

```python
def evaluate_eligibility(rider: dict, event: dict) -> dict:
    """
    Runs 4 gates sequentially. Returns gate results + overall pass/fail.
    """
    results = {
        "gate1_zone_match": False,
        "gate2_shift_overlap": False,
        "gate3_platform_inactive": False,
        "gate4_sensor_verified": True,  # simplified for Phase 2
        "all_passed": False,
        "rejection_reason": None,
    }

    # Gate 1: Zone overlap
    rider_zones = [rider["zone1_pincode"], rider["zone2_pincode"], rider["zone3_pincode"]]
    if event["zone_pincode"] in rider_zones:
        results["gate1_zone_match"] = True
    else:
        results["rejection_reason"] = f"Disruption in {event['zone_pincode']} is not in your registered zones: {rider_zones}"
        return results

    # Gate 2: Shift window overlap
    # For demo: assume riders work 10AM-3PM and 6PM-10PM
    # In production: check against baseline profiler's shift data
    event_hour = event["start_time"].hour
    in_shift = (10 <= event_hour <= 15) or (18 <= event_hour <= 22)
    if in_shift:
        results["gate2_shift_overlap"] = True
    else:
        results["rejection_reason"] = f"Disruption at {event_hour}:00 is outside your shift window (10AM-3PM, 6PM-10PM)"
        return results

    # Gate 3: Platform inactivity
    # For demo: always true (mock — assume rider is inactive)
    # In production: check delivery platform API
    results["gate3_platform_inactive"] = True

    # Gate 4: Sensor fusion
    # For Phase 2: simplified — always true
    # Full sensor fusion is Phase 3
    results["gate4_sensor_verified"] = True

    results["all_passed"] = True
    return results
```

### payout_calculator.py

```python
def calculate_payout(
    hourly_rate: float,
    disrupted_hours: float,
    severity_rate: float,
    weekly_payout_cap: float,
    already_paid_this_week: float
) -> dict:
    disrupted_income = hourly_rate * disrupted_hours
    gross_payout = disrupted_income * severity_rate
    remaining_cap = weekly_payout_cap - already_paid_this_week
    final_payout = min(gross_payout, remaining_cap)
    final_payout = max(final_payout, 0)  # can't be negative

    return {
        "disrupted_hours": disrupted_hours,
        "hourly_rate": hourly_rate,
        "disrupted_income": round(disrupted_income, 2),
        "severity_rate": severity_rate,
        "gross_payout": round(gross_payout, 2),
        "weekly_payout_cap": weekly_payout_cap,
        "already_paid_this_week": already_paid_this_week,
        "remaining_cap": round(remaining_cap, 2),
        "final_payout": round(final_payout, 2),
        "capped": gross_payout > remaining_cap,
    }
```

---

## API Endpoints

```
POST /api/admin/simulate-disruption
    Request: {
        "zone_pincode": "600017",
        "event_type": "rainfall",
        "severity": "severe_l1",
        "duration_hours": 3,
        "raw_value": 85
    }
    Response: {
        "event_id": 1,
        "zone": "T. Nagar (600017)",
        "severity": "severe_l1",
        "severity_rate": 0.45,
        "affected_riders": 3,
        "claims_initiated": 2,
        "claims_rejected": 1,
        "total_payout": 220.50,
        "claims": [
            {
                "rider_id": 1,
                "rider_name": "Ravi Kumar",
                "gates": { "zone": true, "shift": true, "inactive": true, "sensor": true },
                "payout": 94.50,
                "status": "approved"
            },
            {
                "rider_id": 2,
                "rider_name": "Night Rider",
                "gates": { "zone": true, "shift": false, "inactive": true, "sensor": true },
                "rejection_reason": "Disruption at 14:00 is outside your shift window",
                "payout": 0,
                "status": "rejected"
            }
        ]
    }

    This is the MOST IMPORTANT endpoint for the demo.
    It creates a disruption event, finds all affected riders,
    runs eligibility, calculates payouts, and returns everything.

GET /api/triggers/active
    Response: {
        "active_events": [
            {
                "event_id": 1,
                "zone": "600017",
                "type": "rainfall",
                "severity": "severe_l1",
                "start_time": "2026-03-28T14:00:00",
                "is_active": true
            }
        ]
    }

GET /api/claims/{claim_id}
    Response: { full claim details with all gate results }

POST /api/payout/{claim_id}/disburse
    Request: { "payment_method": "upi" }
    Response: {
        "payout_id": 1,
        "amount": 94.50,
        "razorpay_payment_id": "pay_test_xyz",
        "status": "completed"
    }
```

---

## Unit Tests

```python
def test_rainfall_classification():
    assert classify_rainfall(80)[0] == "severe_l1"
    assert classify_rainfall(30)[0] is None
    assert classify_rainfall(120)[0] == "severe_l2"

def test_ravi_payout_scenario_a():
    """README Scenario A: 3hrs × ₹70 × 45% = ₹94.50"""
    result = calculate_payout(
        hourly_rate=70, disrupted_hours=3,
        severity_rate=0.45, weekly_payout_cap=1925, already_paid_this_week=0
    )
    assert result["final_payout"] == 94.50

def test_catastrophic_week_cap():
    """README Scenario D: 50hrs × ₹70 × 75% = ₹2625, capped at ₹1925"""
    result = calculate_payout(
        hourly_rate=70, disrupted_hours=50,
        severity_rate=0.75, weekly_payout_cap=1925, already_paid_this_week=0
    )
    assert result["final_payout"] == 1925.0
    assert result["capped"] == True

def test_eligibility_outside_shift():
    """1 AM storm → shift check fails"""
    from datetime import datetime
    rider = {"zone1_pincode": "600017", "zone2_pincode": "600020", "zone3_pincode": "600032"}
    event = {"zone_pincode": "600017", "start_time": datetime(2026, 3, 28, 1, 0)}
    result = evaluate_eligibility(rider, event)
    assert result["gate2_shift_overlap"] == False
    assert result["all_passed"] == False
```

**Checklist:**
- [ ] OpenWeatherMap API returns real weather data for at least 3 zones
- [ ] AQI check returns a value (even if approximate)
- [ ] Severity classification matches the trigger table from README
- [ ] 4-gate eligibility correctly rejects off-shift, off-zone claims
- [ ] Payout calculator matches all 4 README scenarios (A, B, C, D)
- [ ] Weekly cap enforcement works (Scenario D)
- [ ] Cumulative weekly tracking works (Scenario C — already paid deducted)
- [ ] simulate-disruption endpoint processes all affected riders
- [ ] Razorpay test mode creates a mock payment (even if just a log)

---

---

# MODULE 4 — Mobile App (Rider-Facing)

**Owner:** Person 4
**Tech Stack:** React Native, Firebase Auth, Axios
**Install:** `npx react-native init RahatPay` + `npm install axios @react-navigation/native firebase`

---

## What You're Building

The complete rider-facing Android app. Every screen the rider interacts with — from login to seeing their payout arrive. You work against the API contract from Day 1, using mock JSON until the backend is live.

---

## Screens — Build Order

### Screen 1: LoginScreen (Day 1)
Phone number input + OTP. Use Firebase Auth. On success, check if rider_id exists. If not, navigate to registration. If yes, navigate to dashboard.

### Screen 2: RegisterStep1 — Partner ID (Day 1)
Input fields: Partner ID (e.g., SWG-CHN-12345), Platform dropdown (Swiggy/Zomato), Full Name, City dropdown.

### Screen 3: RegisterStep2 — KYC (Day 1)
Input fields: Aadhaar last 4 digits OR PAN number. A "Verify" button that validates format (Aadhaar: 4 digits, PAN: ABCDE1234F pattern). Show a green checkmark on success. This is mock verification — no real DigiLocker needed.

### Screen 4: RegisterStep3 — Tier Selection (Day 1-2)
Show 3 tier cards side by side (Kavach, Suraksha, Raksha). Each card shows: rate, payout cap, coverage types, claim speed. Below the cards: zone selection — 3 dropdowns for pin codes (populated from GET /api/zones/available). A "Calculate Premium" button that calls the premium endpoint and shows the result. A "Confirm & Subscribe" button that calls POST /api/rider/register.

### Screen 5: DashboardScreen — Home (Day 2)
The main screen after login. Shows: rider name, active tier (with colored badge), weekly premium amount, covered zones with area names, remaining weekly payout headroom (cap minus already paid), policy status and renewal date. Pull-to-refresh to reload.

### Screen 6: PremiumBreakdown (Day 2)
Visual formula: Income (₹3,500) × Rate (1.8%) × Zone (1.10) × Season (1.15) = ₹80/week. Show each component with a label explaining what it means. This screen is a key differentiator — it shows the rider exactly why they pay what they pay.

### Screen 7: PayoutHistory (Day 3)
List of past payouts. Each card shows: date, event type, severity, disrupted hours, amount, status (approved/rejected/pending). Tap a card to see ClaimDetail.

### Screen 8: ClaimDetail (Day 3)
Shows the full breakdown: which gates passed/failed, the payout math (hours × rate × severity), and rejection reason if applicable.

---

## API Client Setup

```javascript
// src/api/client.js
import axios from 'axios';

const API_BASE = 'http://YOUR_BACKEND_IP:8000/api';

const api = axios.create({
  baseURL: API_BASE,
  timeout: 10000,
  headers: { 'Content-Type': 'application/json' },
});

// Add auth token to requests
api.interceptors.request.use((config) => {
  const token = getStoredToken(); // from AsyncStorage
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

export default api;

// Example calls:
// api.get('/rider/1/dashboard')
// api.post('/rider/register', { ... })
// api.get('/rider/1/payouts')
// api.get('/tiers')
// api.get('/zones/available?city=chennai')
```

---

## Mock Data (Use Until Backend is Live)

```javascript
// src/api/mockData.js
export const mockDashboard = {
  rider_id: 1,
  name: "Ravi Kumar",
  tier: "suraksha",
  premium_weekly: 79.70,
  premium_breakdown: {
    baseline_income: 3500,
    tier_rate: 0.018,
    zone_risk: 1.10,
    seasonal_factor: 1.15,
  },
  zones: [
    { pin_code: "600017", area: "T. Nagar", risk: 1.10 },
    { pin_code: "600020", area: "Adyar", risk: 1.05 },
    { pin_code: "600032", area: "Velachery", risk: 1.15 },
  ],
  coverage: {
    weekly_payout_cap: 1925,
    already_paid_this_week: 94.50,
    remaining_headroom: 1830.50,
  },
  policy_status: "active",
};
```

---

## Unit Tests

```javascript
// Test that screens render without crashing
// Test that API calls use correct endpoints
// Test that premium formula displays correctly
// Test that tier selection shows correct rates

// Use: npx jest --watchAll
```

**Checklist:**
- [ ] Login with OTP works (Firebase)
- [ ] Registration flow: 3 screens, all fields validated
- [ ] Tier selection shows correct rates (1.0%, 1.8%, 2.5%)
- [ ] Premium calculation shows formula breakdown
- [ ] Dashboard shows all fields from /rider/{id}/dashboard
- [ ] Payout history shows list from /rider/{id}/payouts
- [ ] Claim detail shows gate results
- [ ] App works on Android emulator
- [ ] Push notification fires on payout (even if simulated)
- [ ] Screens work with mock data (for independent testing)
- [ ] Screens work with live API (after integration)

---

---

# MODULE 5 — Seed Data, Integration & Demo

**Owner:** Person 5
**Tech Stack:** Python (scripts), Postman, screen recording
**Install:** `pip install httpx pytest`

---

## What You're Building

The glue. You make sure all four modules work together. You provide the data, the test scripts, the integration verification, and the final demo. Without you, we have four separate apps that don't connect.

---

## Day 1 Deliverable — API Contract Document

Write this BEFORE anyone else starts coding. Share it in the team group. This is the single source of truth.

```markdown
# RahatPay API Contract v1.0

## Base URL: http://localhost:8000/api

## Registration (Module 1)
POST   /rider/register          → creates rider + policy, returns premium
GET    /rider/{id}/dashboard    → full rider state
GET    /rider/{id}/payouts      → payout history
GET    /zones/available?city=X  → zones for a city
GET    /tiers                   → all 3 tiers with details

## Premium (Module 2)
POST   /premium/calculate       → raw premium calculation
GET    /premium/zone-risk/{pin} → zone risk for a pin code
GET    /baseline/{rider_id}     → rider's baseline income/hours

## Triggers & Claims (Module 3)
POST   /admin/simulate-disruption → create fake disruption + process claims
GET    /triggers/active           → currently active disruptions
GET    /claims/{claim_id}         → single claim details
POST   /payout/{claim_id}/disburse → trigger payout

## Auth (Module 1)
POST   /auth/send-otp
POST   /auth/verify-otp
```

---

## Seed Data Files

### riders.json — 10 Pre-Built Riders

```json
[
    {
        "partner_id": "SWG-CHN-10001", "platform": "swiggy", "name": "Ravi Kumar",
        "phone": "9876500001", "city": "chennai", "tier": "suraksha",
        "zones": ["600017", "600020", "600032"],
        "baseline_weekly_income": 3500, "baseline_weekly_hours": 50,
        "is_seasoning": false
    },
    {
        "partner_id": "ZMT-PUN-10002", "platform": "zomato", "name": "Arjun Patil",
        "phone": "9876500002", "city": "pune", "tier": "kavach",
        "zones": ["411038"],
        "baseline_weekly_income": 1400, "baseline_weekly_hours": 20,
        "is_seasoning": false
    },
    {
        "partner_id": "SWG-MUM-10003", "platform": "swiggy", "name": "Kiran Desai",
        "phone": "9876500003", "city": "mumbai", "tier": "raksha",
        "zones": ["400017", "400050", "400069"],
        "baseline_weekly_income": 5000, "baseline_weekly_hours": 60,
        "is_seasoning": false
    },
    {
        "partner_id": "ZMT-CHN-10004", "platform": "zomato", "name": "Priya Nair",
        "phone": "9876500004", "city": "chennai", "tier": "suraksha",
        "zones": ["600017", "600028", "600032"],
        "baseline_weekly_income": 3200, "baseline_weekly_hours": 45,
        "is_seasoning": false
    },
    {
        "partner_id": "SWG-BLR-10005", "platform": "swiggy", "name": "Deepak Gowda",
        "phone": "9876500005", "city": "bangalore", "tier": "kavach",
        "zones": ["560034", "560011"],
        "baseline_weekly_income": 2000, "baseline_weekly_hours": 30,
        "is_seasoning": false
    },
    {
        "partner_id": "SWG-DEL-10006", "platform": "swiggy", "name": "Amit Sharma",
        "phone": "9876500006", "city": "delhi", "tier": "raksha",
        "zones": ["110001", "110019"],
        "baseline_weekly_income": 4500, "baseline_weekly_hours": 55,
        "is_seasoning": false
    },
    {
        "partner_id": "ZMT-MUM-10007", "platform": "zomato", "name": "Suresh Patil",
        "phone": "9876500007", "city": "mumbai", "tier": "suraksha",
        "zones": ["400017", "400069"],
        "baseline_weekly_income": 3800, "baseline_weekly_hours": 50,
        "is_seasoning": false
    },
    {
        "partner_id": "SWG-CHN-10008", "platform": "swiggy", "name": "New Rider (Seasoning)",
        "phone": "9876500008", "city": "chennai", "tier": "suraksha",
        "zones": ["600017", "600020"],
        "baseline_weekly_income": 0, "baseline_weekly_hours": 0,
        "is_seasoning": true
    },
    {
        "partner_id": "ZMT-BLR-10009", "platform": "zomato", "name": "Lakshmi Devi",
        "phone": "9876500009", "city": "bangalore", "tier": "suraksha",
        "zones": ["560034"],
        "baseline_weekly_income": 2800, "baseline_weekly_hours": 40,
        "is_seasoning": false
    },
    {
        "partner_id": "SWG-DEL-10010", "platform": "swiggy", "name": "Night Worker",
        "phone": "9876500010", "city": "delhi", "tier": "kavach",
        "zones": ["110001"],
        "baseline_weekly_income": 1800, "baseline_weekly_hours": 25,
        "is_seasoning": false
    }
]
```

### disruption_scenarios.json — 4 Demo Scenarios

```json
[
    {
        "name": "Demo 1: Severe Rainfall in Chennai",
        "zone_pincode": "600017",
        "event_type": "rainfall",
        "severity": "severe_l1",
        "duration_hours": 3,
        "raw_value": 85,
        "expected_affected_riders": ["Ravi Kumar", "Priya Nair"],
        "description": "IMD Red Alert, 85mm rainfall in T. Nagar"
    },
    {
        "name": "Demo 2: AQI Spike in Delhi",
        "zone_pincode": "110001",
        "event_type": "air_quality",
        "severity": "severe_l1",
        "duration_hours": 6,
        "raw_value": 350,
        "expected_affected_riders": ["Amit Sharma", "Night Worker"],
        "description": "AQI crosses 350 in Connaught Place"
    },
    {
        "name": "Demo 3: Cyclone in Mumbai",
        "zone_pincode": "400017",
        "event_type": "cyclone",
        "severity": "extreme",
        "duration_hours": 9,
        "raw_value": 160,
        "description": "Category 1 cyclone, Dharavi zone"
    },
    {
        "name": "Demo 4: Ineligible — Night Storm",
        "zone_pincode": "600017",
        "event_type": "rainfall",
        "severity": "severe_l1",
        "start_hour": 1,
        "duration_hours": 3,
        "description": "Storm at 1 AM — daytime riders should be rejected"
    }
]
```

---

## Integration Test Scripts

```python
# test_full_e2e.py
import httpx

BASE = "http://localhost:8000/api"

def test_full_flow():
    """
    The golden test: registration → premium → disruption → claim → payout.
    If this passes, the demo will work.
    """

    # Step 1: Register Ravi
    reg = httpx.post(f"{BASE}/rider/register", json={
        "partner_id": "SWG-CHN-TEST",
        "platform": "swiggy",
        "name": "Ravi Test",
        "phone": "9999900000",
        "aadhaar_last4": "4321",
        "city": "chennai",
        "zones": ["600017", "600020", "600032"],
        "tier": "suraksha"
    }).json()
    rider_id = reg["rider_id"]
    assert reg["tier"] == "suraksha"
    assert reg["premium"]["weekly_amount"] > 15
    print(f"✓ Registration: rider_id={rider_id}, premium=₹{reg['premium']['weekly_amount']}")

    # Step 2: Check dashboard
    dash = httpx.get(f"{BASE}/rider/{rider_id}/dashboard").json()
    assert dash["tier"] == "suraksha"
    assert dash["coverage"]["remaining_headroom"] > 0
    print(f"✓ Dashboard: headroom=₹{dash['coverage']['remaining_headroom']}")

    # Step 3: Simulate disruption
    event = httpx.post(f"{BASE}/admin/simulate-disruption", json={
        "zone_pincode": "600017",
        "event_type": "rainfall",
        "severity": "severe_l1",
        "duration_hours": 3,
        "raw_value": 85
    }).json()
    print(f"✓ Disruption: {event['affected_riders']} riders affected")

    # Step 4: Check claim was created
    payouts = httpx.get(f"{BASE}/rider/{rider_id}/payouts").json()
    if payouts["total_payouts"] > 0:
        payout = payouts["payouts"][0]
        print(f"✓ Claim: ₹{payout['amount']} — status: {payout['status']}")
        assert payout["amount"] > 0
    else:
        print("✗ No payout created — check eligibility gates")

    # Step 5: Verify dashboard updated
    dash2 = httpx.get(f"{BASE}/rider/{rider_id}/dashboard").json()
    assert dash2["coverage"]["already_paid_this_week"] > 0
    print(f"✓ Headroom updated: ₹{dash2['coverage']['remaining_headroom']}")

    print("\n=== FULL E2E TEST PASSED ===")

if __name__ == "__main__":
    test_full_flow()
```

---

## Demo Video Script (2 Minutes)

```
[0:00-0:15] Open the app. Show login with OTP.
[0:15-0:35] Walk through registration: Partner ID → KYC → Tier selection.
             Show the premium being calculated live with formula breakdown.
[0:35-0:50] Show the dashboard: tier, premium, zones, headroom.
[0:50-1:10] Switch to terminal/Postman. Hit the simulate-disruption endpoint.
             Show the response: affected riders, gate results, payout amounts.
[1:10-1:30] Switch back to app. Pull-to-refresh dashboard.
             Show the payout appearing in history with amount and gate details.
             Show the updated headroom (cap minus payout).
[1:30-1:50] Show a second scenario: 1 AM storm → rejected claim with reason.
             Show the plain-language rejection in the app.
[1:50-2:00] Close with the premium formula one more time. End.
```

**Checklist:**
- [ ] API contract document written and shared (Day 1)
- [ ] All seed data files created (riders, zones, scenarios)
- [ ] Seed data loaded into database via script
- [ ] Postman collection with all endpoints + working examples
- [ ] Integration test: registration works end-to-end
- [ ] Integration test: premium calculation matches README examples
- [ ] Integration test: disruption → claim → payout flow works
- [ ] Integration test: ineligible claim is correctly rejected with reason
- [ ] Demo video recorded (2 minutes)
- [ ] GitHub repo has requirements.txt, package.json, and setup instructions

---

---

# HOW TO STITCH ALL 5 MODULES TOGETHER

---

## Step 1: Shared FastAPI Server (Day 1 Setup)

All backend modules (1, 2, 3) run as ONE FastAPI server. Not three separate servers.

Create a shared `main.py` at the root:

```python
# rahatpay/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="RahatPay API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # React Native needs this
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import routes from each module
from module1_registration.routes import auth, registration, policy
from module2_risk_engine.routes import premium
from module3_triggers_claims.routes import triggers, claims, admin

# Mount all routes
app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(registration.router, prefix="/api/rider", tags=["Registration"])
app.include_router(policy.router, prefix="/api", tags=["Policy"])
app.include_router(premium.router, prefix="/api/premium", tags=["Premium"])
app.include_router(triggers.router, prefix="/api/triggers", tags=["Triggers"])
app.include_router(claims.router, prefix="/api/claims", tags=["Claims"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])

# Start trigger polling on startup
from module3_triggers_claims.triggers.monitor import trigger_polling_loop
import asyncio

@app.on_event("startup")
async def start_polling():
    asyncio.create_task(trigger_polling_loop())
```

Run with: `uvicorn main:app --reload --host 0.0.0.0 --port 8000`

---

## Step 2: Endpoint-to-Module Ownership Map

| Endpoint | Module | Owner |
|---|---|---|
| POST /api/auth/send-otp | 1 | Person 1 |
| POST /api/auth/verify-otp | 1 | Person 1 |
| POST /api/rider/register | 1 (calls Module 2 for premium) | Person 1 |
| GET /api/rider/{id}/dashboard | 1 (reads claims from Module 3's table) | Person 1 |
| GET /api/rider/{id}/payouts | 1 (reads from claims + payouts tables) | Person 1 |
| GET /api/zones/available | 1 | Person 1 |
| GET /api/tiers | 1 | Person 1 |
| POST /api/premium/calculate | 2 | Person 2 |
| GET /api/premium/zone-risk/{pin} | 2 | Person 2 |
| GET /api/baseline/{rider_id} | 2 | Person 2 |
| POST /api/admin/simulate-disruption | 3 (reads riders from Module 1's table) | Person 3 |
| GET /api/triggers/active | 3 | Person 3 |
| GET /api/claims/{id} | 3 | Person 3 |
| POST /api/payout/{claim_id}/disburse | 3 | Person 3 |
| Mobile app (all screens) | 4 (calls all above endpoints) | Person 4 |
| Integration tests + demo | 5 (tests all above) | Person 5 |

---

## Step 3: Cross-Module Function Calls

Module 1 needs to call Module 2 during registration:

```python
# Inside module1's registration.py
from module2_risk_engine.premium.calculator import calculate_premium
from module2_risk_engine.baseline.profiler import get_baseline

# When creating a new rider:
baseline = get_baseline(rider_id=None, city="chennai", is_seasoning=True)
premium = calculate_premium(
    baseline_weekly_income=baseline["weekly_income"],
    tier="suraksha",
    zone_pincodes=["600017", "600020", "600032"]
)
```

Module 3 needs to call Module 2 during claim processing:

```python
# Inside module3's eligibility.py
from module2_risk_engine.baseline.profiler import get_baseline

# When calculating payout for a rider:
baseline = get_baseline(rider_id=rider["rider_id"], city=rider["city"], is_seasoning=rider["is_seasoning"])
hourly_rate = baseline["hourly_rate"]
```

Module 3 reads rider data from Module 1's tables:

```python
# Inside module3's claims engine
# Query all riders whose zones include the disrupted zone
affected_riders = db.query(
    "SELECT * FROM riders WHERE zone1_pincode = %s OR zone2_pincode = %s OR zone3_pincode = %s",
    (event_zone, event_zone, event_zone)
)
```

---

## Step 4: Integration Day Checklist (Day 4)

```
[ ] All 5 branches merged to main
[ ] pip install -r requirements.txt runs clean
[ ] PostgreSQL schema created, seed data loaded
[ ] uvicorn main:app starts without errors
[ ] All routes appear at http://localhost:8000/docs (FastAPI auto-docs)
[ ] Person 5 runs test_full_e2e.py — all steps pass
[ ] Mobile app connects to live backend (change API_BASE URL)
[ ] Registration flow works end-to-end through the app
[ ] Simulate disruption → payout appears in app
[ ] Ineligible claim shows rejection reason in app
[ ] Demo video recorded
```

---

*This document is the single reference for the entire Phase 2 build. If it's not in here, don't build it. If it is in here, it must ship.*
