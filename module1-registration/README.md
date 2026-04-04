# RahatPay — Module 1: Registration & Policy Management

**Owner:** Module 1 Team  
**Stack:** FastAPI · PostgreSQL · SQLAlchemy (async) · Firebase Admin SDK · Pydantic v2

---

## What This Module Owns

Module 1 is the **single source of truth** for:

- Rider identity (`riders` table)
- Policy lifecycle (`policies` table)
- The full database schema — every other module reads from tables created here
- Zone reference data (`zones` table)
- Schema definitions for `claims`, `payouts`, `disruption_events` (Module 3 writes to these)

---

## Quick Start

### 1. Prerequisites

- Python 3.12+
- PostgreSQL 15+ (or use Docker)
- `asyncpg` requires `libpq-dev` on Debian/Ubuntu

### 2. Environment

```bash
cp .env.example .env
# Edit .env — defaults work for local Docker setup
```

### 3. Run with Docker (recommended)

```bash
docker-compose up --build
```

API available at: `http://localhost:8001`  
Swagger UI: `http://localhost:8001/docs`

### 4. Run locally (without Docker)

```bash
# Create virtualenv
python -m venv .venv && source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Ensure PostgreSQL is running, then:
python main.py
# or
uvicorn main:app --reload --port 8001
```

### 5. Run tests

```bash
# Requires a running PostgreSQL with a rahatpay_test database
createdb rahatpay_test   # one-time setup

pytest tests/ -v
```

---

## API Reference

### Auth

| Method | Path | Description |
|--------|------|-------------|
| POST | `/auth/send-otp` | Trigger Firebase OTP SMS |
| POST | `/auth/verify-otp` | Verify OTP; returns rider_id if registered |

### Registration

| Method | Path | Description |
|--------|------|-------------|
| POST | `/register` | **Core endpoint.** Creates rider + active policy |

### Rider Dashboard

| Method | Path | Description |
|--------|------|-------------|
| GET | `/rider/{id}/dashboard` | Full policy, premium breakdown, headroom |
| GET | `/rider/{id}/payouts` | Claim history with gate results |
| POST | `/rider/{id}/change-tier` | Tier change (cycle boundary only) |
| POST | `/rider/{id}/renew` | Renew policy after cycle ends |

### Reference Data

| Method | Path | Description |
|--------|------|-------------|
| GET | `/zones?city=Chennai` | List delivery zones |
| GET | `/tiers` | Tier definitions, rates, payout caps |

### Health

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Liveness probe |

---

## Module 2 Integration

Module 1 calls Module 2 **directly** (function import, not HTTP).  
Integration point: `integrations/module2_adapter.py`

```python
# Module 2 functions used by Module 1:
baseline = await get_baseline(rider_id, city, is_seasoning)
# → BaselineResult(income, hours, hourly_rate, is_provisional)

premium = await calculate_premium(income, tier, zones, month)
# → PremiumResult(weekly_premium, breakdown)
```

**To connect real Module 2:**
1. Set `MODULE2_MOCK_MODE=false` in `.env`
2. The adapter will auto-import from `../../module2-risk-engine/`
3. If the import fails, it gracefully falls back to mock

**Mock mode** (default): Uses city-level medians for income and a hardcoded zone risk table matching Module 5's seed values.

---

## Premium Formula

```
raw_premium = income × tier_rate × zone_risk × seasonal_factor
final_premium = clamp(raw_premium, floor=₹15, cap=3.5% of income)
```

| Tier | Rate | Weekly Payout Cap |
|------|------|-------------------|
| Kavach | 1.5% | ₹1,500 |
| Suraksha | 1.8% | ₹3,000 |
| Raksha | 2.2% | ₹5,000 |

---

## Database Schema Notes

All tables are in `db/schema.sql`. Critical constraints:

- `claims.final_payout ≤ 5000` — enforced at DB level (CHECK constraint)
- `payouts.amount ≤ 5000` — enforced at DB level (CHECK constraint)  
- `policies.weekly_premium ≥ 15` — minimum premium floor
- `policies.cycle_end_date = cycle_start_date + 28 days` — 4-week lock-in
- `riders.aadhaar_last4 IS NOT NULL OR pan IS NOT NULL` — at least one KYC required

---

## Firebase Auth

**Mock mode** (default for dev):
- Any call to `/auth/send-otp` records a mock session
- OTP is always `000000`
- Set `FIREBASE_MOCK_MODE=true` in `.env`

**Real mode:**
- Set `FIREBASE_MOCK_MODE=false`
- Set `FIREBASE_CREDENTIALS_PATH=/path/to/serviceAccount.json`
- Client SDK handles phone auth; server verifies ID tokens

---

## Project Structure

```
module1-registration/
├── db/
│   ├── connection.py       # Async SQLAlchemy engine + get_db() dependency
│   ├── schema.sql          # Full DB schema with all CHECK constraints
│   └── seed.sql            # 20 zones + 3 sample riders
├── integrations/
│   ├── firebase_auth.py    # OTP send/verify (real + mock)
│   └── module2_adapter.py  # Direct function bridge to Module 2
├── migrations/
│   └── env.py              # Alembic async migration environment
├── models/
│   ├── rider.py            # Rider + Zone ORM models
│   └── policy.py           # Policy + Claim + Payout + DisruptionEvent models
├── routes/
│   ├── auth.py             # /auth/send-otp, /auth/verify-otp
│   ├── registration.py     # POST /register
│   └── policy.py           # Dashboard, payouts, zones, tiers, tier-change, renew
├── tests/
│   ├── test_registration.py  # 14 registration test cases
│   └── test_policy.py        # 16 policy/dashboard test cases
├── config.py               # All settings via pydantic-settings + TIER_CONFIG
├── main.py                 # App entry point, lifespan, exception handlers
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── alembic.ini
└── .env.example
```

---

## Inter-Module Contracts

### What Module 1 exposes to other modules

**Tables (read-only for other modules):**
- `riders` — identity, tier, baseline, zones
- `policies` — active coverage, premium, cycle dates
- `zones` — pincode → city + risk multiplier
- `disruption_events` — schema owned here, written by Module 3
- `claims` — schema owned here, written by Module 3
- `payouts` — schema owned here, written by Module 3

**Module 3 needs from Module 1:**
- `rider.zone1/2/3_pincode` — for zone overlap gate
- `rider.baseline_weekly_income`, `baseline_weekly_hours` — for hourly rate
- `policy.weekly_payout_cap` — for cap enforcement
- `policy.status` + `cycle_end_date` — for eligibility

**Module 4 (Mobile App) needs from Module 1:**
- All endpoints in this module are the API contract for Module 4
- Module 4 should mock these responses on Day 1 then swap to real calls
