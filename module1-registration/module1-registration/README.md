# RahatPay — Module 1: Registration & Policy Management

> **The authoritative source of truth for rider identity, zone data, and policy lifecycle across the entire RahatPay platform.**

---

## Table of Contents

1. [Module Overview](#1-module-overview)
2. [Tech Stack](#2-tech-stack)
3. [Architecture Overview](#3-architecture-overview)
4. [Database Design](#4-database-design)
5. [API Routes](#5-api-routes)
   - [Auth Routes](#auth-routes)
   - [Registration](#registration)
   - [Rider APIs](#rider-apis)
   - [Utility APIs](#utility-apis)
   - [Admin APIs](#admin-apis)
6. [Registration Flow](#6-registration-flow-step-by-step)
7. [Admin System](#7-admin-system)
8. [Polygon Zone Handling](#8-polygon-zone-handling)
9. [Setup Instructions](#9-setup-instructions)
10. [Running the Server](#10-running-the-server)
11. [Demo Walkthrough](#11-demo-walkthrough)
12. [Testing APIs](#12-testing-apis)
13. [Integration Notes](#13-integration-notes)
14. [Design Decisions](#14-design-decisions)
15. [Future Improvements](#15-future-improvements)

---

## 1. Module Overview

### Purpose

Module 1 is the **registration and policy management backbone** of RahatPay — a parametric income-disruption insurance platform for gig economy delivery riders. It handles:

- **Rider onboarding** — identity creation, KYC validation, and zone assignment
- **Policy lifecycle** — from creation through renewal, tier changes, and expiry
- **Premium computation** — by coordinating with Module 2's risk engine
- **Database ownership** — all platform tables live here; other modules read from them
- **Admin governance** — fraud monitoring, worker management, zone control, and financial analytics

### Role in the RahatPay System

```
[Rider App / Partner Platform]
        │
        ▼
[ Module 1 — Registration & Policy ]  ◄── YOU ARE HERE
        │
        ├──► Module 2 (Risk Engine & Premium Calculator)
        │       └── Called during registration and renewal to compute premiums
        │
        └──► Module 3 (Claims & Payouts)
                └── Reads riders, policies, zones, and disruption_events from Module 1's DB
```

Module 1 **owns** all core tables. Module 3 reads from `riders`, `policies`, `zones`, `disruption_events`, and writes back to `claims` and `payouts`.

### Problems It Solves

- Prevents duplicate registrations (by `partner_id` and `phone`)
- Validates riders against geographic zones (polygon-based)
- Enforces KYC and identity constraints at the DB level
- Provides a locked 4-week policy cycle to prevent abuse
- Acts as a trust anchor for other modules via `trust_score` and `kyc_verified`

---

## 2. Tech Stack

| Component | Technology |
|---|---|
| Web Framework | **FastAPI** 0.111.0 |
| ASGI Server | **Uvicorn** 0.30.1 (with standard extras) |
| ORM | **SQLAlchemy** 2.0 (async) |
| Database Driver | **asyncpg** 0.29.0 |
| Database | **PostgreSQL** (14+) |
| Schema Migrations | **Alembic** 1.13.1 |
| Data Validation | **Pydantic v2** 2.7.1 |
| Auth Integration | **Firebase Admin SDK** 6.5.0 (OTP via Firebase Phone Auth) |
| HTTP Client (tests) | **httpx** 0.27.0 |
| Testing | **pytest** + **pytest-asyncio** |
| Configuration | **pydantic-settings** + `.env` file |
| Containerization | **Docker** + **docker-compose** |

### Key Libraries — Why They Were Chosen

- **FastAPI**: Native async support, automatic OpenAPI docs, Pydantic integration
- **asyncpg**: Fastest async PostgreSQL driver; required for SQLAlchemy 2.0 async mode
- **JSONB (PostgreSQL)**: Flexible polygon storage without requiring PostGIS
- **Pydantic v2**: Field-level validators, model validators, serialization — all in one

---

## 3. Architecture Overview

### Folder Structure

```
module1-registration/
├── main.py                    # FastAPI app entry point, lifespan, middleware
├── config.py                  # Settings (pydantic-settings), tier config, seasonal factors
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── alembic.ini
│
├── db/
│   ├── connection.py          # Async SQLAlchemy engine, session factory, Base
│   ├── schema.sql             # Full DB schema (run once to initialize)
│   └── seed.sql               # Sample zones + 3 test riders with policies
│
├── models/
│   ├── rider.py               # Zone + Rider ORM models
│   └── policy.py              # Policy, Claim, Payout, DisruptionEvent ORM models
│
├── routes/
│   ├── auth.py                # /auth/send-otp, /auth/verify-otp
│   ├── registration.py        # POST /register
│   ├── policy.py              # Dashboard, payouts, zones, tiers, tier-change, renewal
│   └── admin.py               # /admin/* — full admin control panel
│
├── integrations/
│   ├── firebase_auth.py       # Firebase OTP send/verify (mock-capable)
│   └── module2_adapter.py     # Module 2 integration (direct import or mock fallback)
│
└── tests/
    └── ...                    # pytest test suite
```

### How Components Interact

```
HTTP Request
    │
    ▼
FastAPI App (main.py)
    │── CORS Middleware
    │── Exception Handlers (Validation, IntegrityError, etc.)
    │
    ▼
Route Handler (routes/*.py)
    │── Pydantic schema validates request body
    │── Dependency injection: get_db() → AsyncSession
    │
    ▼
SQLAlchemy ORM (models/*.py)
    │── Reads/writes PostgreSQL tables
    │── JSONB for polygon + premium_breakdown
    │
    ▼ (during /register and /renew)
Module 2 Adapter (integrations/module2_adapter.py)
    │── get_baseline() → income, hours, hourly_rate
    │── calculate_premium() → weekly_premium + breakdown
```

### Module 2 Integration Mode

Module 2 is called **in-process** (direct Python import), not via HTTP. The adapter in `integrations/module2_adapter.py`:

1. Attempts to import from `../../module2-risk-engine/` at startup
2. Falls back to a **built-in mock** when `MODULE2_MOCK_MODE=True` (default for development)
3. The mock uses city-median income tables and a zone-risk lookup table that mirrors Module 2's XGBoost output

---

## 4. Database Design

All tables use `INTEGER GENERATED ALWAYS AS IDENTITY` primary keys (PostgreSQL-standard, no UUID overhead). All timestamps use `TIMESTAMPTZ` (timezone-aware).

### Entity Relationship Overview

```
zones  ◄────── riders ──────► policies
                │                 │
               claims ◄──────────┘
                │
           disruption_events
                │
             payouts
```

---

### Table: `zones`

**Purpose:** Reference table for geographic delivery zones. Owned by Module 1; read by all modules.

| Column | Type | Description |
|---|---|---|
| `zone_id` | `INTEGER IDENTITY PK` | Auto-generated primary key |
| `city` | `VARCHAR(100)` | City name (e.g., Chennai, Mumbai) |
| `area_name` | `VARCHAR(200)` | Human-readable area name |
| `polygon` | `JSONB` | Array of `{lat, lng}` coordinate objects |
| `risk_multiplier` | `NUMERIC(4,2)` | Zone risk factor; CHECK `0.80 – 1.50` |
| `is_active` | `BOOLEAN` | Whether zone accepts new registrations |
| `registration_cap` | `INTEGER` | Max riders per zone (default 1000) |
| `created_at` | `TIMESTAMPTZ` | Record creation timestamp |

**Key Constraints:**
- `risk_multiplier BETWEEN 0.80 AND 1.50`

**Seeded Zones:** 20 zones across Chennai (8), Mumbai (4), Bangalore (4), Delhi (4).

---

### Table: `riders`

**Purpose:** Core identity table. Single source of truth for all rider data across the platform.

| Column | Type | Description |
|---|---|---|
| `id` | `INTEGER IDENTITY PK` | Internal rider ID |
| `partner_id` | `VARCHAR(100) UNIQUE` | External ID from Swiggy/Zomato/Dunzo |
| `platform` | `VARCHAR(20)` | CHECK: `swiggy\|zomato\|dunzo\|other` |
| `name` | `VARCHAR(200)` | Full name |
| `phone` | `VARCHAR(15) UNIQUE` | Indian mobile number |
| `aadhaar_last4` | `CHAR(4)` | Last 4 digits of Aadhaar (optional) |
| `pan` | `VARCHAR(10)` | PAN card number (optional) |
| `city` | `VARCHAR(100)` | Rider's operating city |
| `zone1_id` | `INTEGER FK → zones` | Primary zone (mandatory) |
| `zone2_id` | `INTEGER FK → zones` | Secondary zone (optional) |
| `zone3_id` | `INTEGER FK → zones` | Tertiary zone (optional) |
| `tier` | `VARCHAR(20)` | CHECK: `kavach\|suraksha\|raksha` |
| `baseline_weekly_income` | `NUMERIC(10,2)` | Weekly income from Module 2 |
| `baseline_weekly_hours` | `NUMERIC(6,2)` | Weekly hours from Module 2 |
| `is_seasoning` | `BOOLEAN` | TRUE for first 4 weeks (no real baseline yet) |
| `trust_score` | `NUMERIC(5,2)` | 0–100 trust score; used by Module 3 gates |
| `is_blocked` | `BOOLEAN` | Admin-set block flag |
| `kyc_verified` | `BOOLEAN` | Admin-verified KYC status |
| `created_at` | `TIMESTAMPTZ` | Registration timestamp |
| `updated_at` | `TIMESTAMPTZ` | Auto-updated via trigger |

**Key Constraints:**
- `kyc_required`: `aadhaar_last4 IS NOT NULL OR pan IS NOT NULL` — at least one KYC doc required
- `trust_score BETWEEN 0 AND 100`
- `platform IN ('swiggy', 'zomato', 'dunzo', 'other')`
- `tier IN ('kavach', 'suraksha', 'raksha')`

---

### Table: `policies`

**Purpose:** Insurance policy covering a 4-week cycle. One active policy per rider at a time.

| Column | Type | Description |
|---|---|---|
| `id` | `INTEGER IDENTITY PK` | Policy ID |
| `rider_id` | `INTEGER FK → riders` | Owning rider |
| `tier` | `VARCHAR(20)` | Policy tier at time of creation |
| `weekly_premium` | `NUMERIC(10,2)` | Premium amount (CHECK ≥ ₹15) |
| `premium_breakdown` | `JSONB` | Full breakdown: `{income, tier_rate, zone_risk, seasonal_factor, raw_premium, floor_applied, cap_applied, final_premium}` |
| `weekly_payout_cap` | `NUMERIC(10,2)` | Max payout per week (CHECK > 0) |
| `coverage_type` | `VARCHAR(100)` | e.g., `income_disruption` |
| `status` | `VARCHAR(20)` | CHECK: `active\|expired\|cancelled\|pending` |
| `cycle_start_date` | `DATE` | Start of 4-week cycle |
| `cycle_end_date` | `DATE` | Must be exactly 28 days after start |
| `created_at` | `TIMESTAMPTZ` | |
| `updated_at` | `TIMESTAMPTZ` | Auto-updated via trigger |

**Key Constraints:**
- `weekly_premium >= 15` — ₹15 minimum floor
- `policy_4week_cycle`: `cycle_end_date = cycle_start_date + INTERVAL '28 days'` — DB-enforced cycle length

---

### Table: `disruption_events`

**Purpose:** Weather/civic disruption events that trigger claims. Created by Module 1; processed by Module 3.

| Column | Type | Description |
|---|---|---|
| `id` | `INTEGER IDENTITY PK` | Event ID |
| `event_type` | `VARCHAR(50)` | CHECK: `heavy_rain\|cyclone\|flood\|extreme_heat\|poor_aqi\|civic_disruption\|storm\|other` |
| `severity` | `VARCHAR(20)` | CHECK: `moderate\|severe_l1\|severe_l2\|extreme` |
| `payout_rate` | `NUMERIC(5,4)` | Fraction of income to pay out (0–1) |
| `affected_zone` | `INTEGER FK → zones` | Which zone is affected |
| `trigger_data` | `JSONB` | Raw data from weather APIs |
| `event_start` | `TIMESTAMPTZ` | Event start time |
| `event_end` | `TIMESTAMPTZ` | Optional event end time |
| `processing_status` | `VARCHAR(20)` | `pending\|processing\|processed\|failed` |
| `created_at` | `TIMESTAMPTZ` | |
| `updated_at` | `TIMESTAMPTZ` | Auto-updated via trigger |

---

### Table: `claims`

**Purpose:** Claims generated by Module 3 when a rider is eligible for a disruption event payout.

| Column | Type | Description |
|---|---|---|
| `id` | `INTEGER IDENTITY PK` | Claim ID |
| `rider_id` | `INTEGER FK → riders` | |
| `policy_id` | `INTEGER FK → policies` | Active policy at time of claim |
| `disruption_event_id` | `INTEGER FK → disruption_events` | Triggering event |
| `gate_results` | `JSONB` | `{zone_overlap, shift_window, platform_inactivity, location_verified}` |
| `is_eligible` | `BOOLEAN` | Whether rider passed all gates |
| `ineligibility_reason` | `TEXT` | Human-readable reason if rejected |
| `lost_hours` | `NUMERIC(6,2)` | Hours lost during event |
| `hourly_rate` | `NUMERIC(10,2)` | Rider's computed hourly rate |
| `severity_rate` | `NUMERIC(5,4)` | Payout fraction for this severity |
| `calculated_payout` | `NUMERIC(10,2)` | Raw computed payout |
| `final_payout` | `NUMERIC(10,2)` | Final capped payout (CHECK ≤ ₹5,000) |
| `status` | `VARCHAR(20)` | `pending\|approved\|rejected\|paid\|failed` |
| `created_at` | `TIMESTAMPTZ` | |
| `updated_at` | `TIMESTAMPTZ` | |

**Key Constraints:**
- `final_payout >= 0 AND final_payout <= 5000` — hard cap at ₹5,000 per claim
- `UNIQUE(rider_id, disruption_event_id)` — one claim per rider per event (no duplicate claims)

---

### Table: `payouts`

**Purpose:** Actual payment disbursement records linked to approved claims.

| Column | Type | Description |
|---|---|---|
| `id` | `INTEGER IDENTITY PK` | Payout ID |
| `claim_id` | `INTEGER FK → claims` | Claim being paid |
| `rider_id` | `INTEGER FK → riders` | Rider receiving payment |
| `amount` | `NUMERIC(10,2)` | CHECK: `> 0 AND <= 5000` |
| `gateway` | `VARCHAR(50)` | CHECK: `razorpay\|manual\|test` |
| `gateway_reference` | `VARCHAR(200)` | Transaction reference |
| `gateway_response` | `JSONB` | Full gateway response payload |
| `upi_id` | `VARCHAR(200)` | Rider's UPI ID (hashed in production) |
| `status` | `VARCHAR(20)` | `initiated\|processing\|success\|failed\|reversed` |
| `initiated_at` | `TIMESTAMPTZ` | When payout was triggered |
| `completed_at` | `TIMESTAMPTZ` | When payment completed |
| `created_at` | `TIMESTAMPTZ` | |
| `updated_at` | `TIMESTAMPTZ` | |

**Key Constraint:** `amount > 0 AND amount <= 5000` — same cap enforced at payment level

---

## 5. API Routes

All routes are documented at **`/docs`** (Swagger UI) and **`/redoc`** when the server is running.

---

### Auth Routes

#### `POST /auth/send-otp`

Triggers Firebase Phone Auth to send a 6-digit OTP via SMS.

**Request Body:**
```json
{
  "phone": "+919876543210"
}
```

**Response:**
```json
{
  "session_info": "session_abc123",
  "mock": true,
  "message": "OTP sent successfully."
}
```

> In mock mode (`FIREBASE_MOCK_MODE=True`), the OTP is always `000000`. No real SMS is sent.

**Validations:**
- Phone must match Indian format: `+91XXXXXXXXXX`, `91XXXXXXXXXX`, or `0XXXXXXXXXX`

---

#### `POST /auth/verify-otp`

Verifies the OTP. Returns rider context if the phone is already registered.

**Request Body:**
```json
{
  "phone": "+919876543210",
  "otp": "000000",
  "session_info": "session_abc123"
}
```

**Response (registered rider):**
```json
{
  "verified": true,
  "firebase_uid": "firebase_uid_xyz",
  "phone": "+919876543210",
  "is_registered": true,
  "rider_id": "1",
  "rider_name": "Arjun Kumar",
  "message": "Welcome back! You are already registered."
}
```

**Response (new user):**
```json
{
  "verified": true,
  "firebase_uid": "firebase_uid_xyz",
  "phone": "+919876543210",
  "is_registered": false,
  "rider_id": null,
  "rider_name": null,
  "message": "Phone verified. Please complete registration."
}
```

**Validations:**
- OTP must be exactly 6 digits
- OTP expiry and invalidity handled with distinct HTTP 401 responses

---

### Registration

#### `POST /register`

**The most critical endpoint in Module 1.** Creates rider identity and first active policy in a single atomic transaction.

**Request Body:**
```json
{
  "partner_id": "SWG-CHN-001",
  "platform": "swiggy",
  "name": "Arjun Kumar",
  "phone": "+919876543210",
  "kyc": {
    "type": "aadhaar",
    "value": "XXXX XXXX 4521"
  },
  "city": "Chennai",
  "zone1_id": 1,
  "zone2_id": 2,
  "zone3_id": 3,
  "tier": "kavach",
  "zones": [
    {
      "zone_id": 1,
      "polygon": [
        { "lat": 13.0827, "lng": 80.2707 },
        { "lat": 13.0850, "lng": 80.2750 },
        { "lat": 13.0800, "lng": 80.2780 }
      ]
    }
  ],
  "demo_income_override": 800
}
```

**Optional: `demo_income_override` (demo / QA only)**

| | |
|---|---|
| **Purpose** | For presentations and tests: treat this value as the rider’s **weekly baseline income** for premium calculation on this request only (after `get_baseline()`, before `calculate_premium()`). Does not change Module 2’s formulas. |
| **When allowed** | Only when `ENVIRONMENT` is **not** `production` **and** `ALLOW_DEMO_INCOME_OVERRIDE=true` (default). Otherwise the API returns **400** with a clear message. |
| **Production** | Set `ENVIRONMENT=production` (and optionally `ALLOW_DEMO_INCOME_OVERRIDE=false`) to disable this field entirely. |

Omit the field for normal registrations (city median / Module 2 baseline is used as usual).

**Response (`201 Created`):**
```json
{
  "rider_id": 4,
  "partner_id": "SWG-CHN-001",
  "name": "Arjun Kumar",
  "tier": "kavach",
  "policy_id": 5,
  "weekly_premium": 15.00,
  "weekly_payout_cap": 1500.00,
  "premium_breakdown": {
    "income": 3500.00,
    "tier_rate": 0.015,
    "zone_risk": 1.15,
    "seasonal_factor": 0.92,
    "raw_premium": 55.65,
    "floor_applied": false,
    "cap_applied": false,
    "final_premium": 15.00
  },
  "cycle_start_date": "2026-04-02",
  "cycle_end_date": "2026-04-30",
  "is_seasoning": true,
  "message": "Registration successful. Your 'kavach' policy is active for 4 weeks. Weekly premium: ₹15.0."
}
```

**Validations:**
- `partner_id`: alphanumeric + `-_`, 3–100 chars; must be unique
- `phone`: Indian mobile format; must be unique
- `platform`: one of `swiggy | zomato | dunzo | other`
- `tier`: one of `kavach | suraksha | raksha`
- `kyc.type`: `aadhaar` (stores last 4 digits) or `pan` (validates `ABCDE1234F` format)
- All `zone_id` values must exist in the database
- All zones must belong to the given `city`
- Zone IDs must be distinct
- If `zones[]` polygon data is provided:
  - Each `zone_id` must match one of `zone1_id / zone2_id / zone3_id`
  - Each polygon must have **at least 3** lat/lng points
  - `lat` within `[-90, 90]`, `lng` within `[-180, 180]`

### Premium calculation (floor & cap)

Premium is computed in **Module 2** (or the built-in mock in `integrations/module2_adapter.py`). The weekly raw amount is:

`income × tier_rate × zone_risk × seasonal_factor`

Then:

1. **₹15 floor** — If the computed raw amount is below **₹15/week**, the premium is raised to **₹15** (`floor_applied: true` in the breakdown). The DB also enforces `weekly_premium >= 15` on policies.
2. **3.5% income cap** — The premium is capped at **3.5% of the same baseline weekly income** used in the formula (`premium_breakdown.cap_applied` when the cap binds). The floor still wins if it would otherwise be higher than the cap.

**Demonstrating floor and cap:** With normal city-median income, mock baselines often stay in a range where both aren’t dramatic. Use **`demo_income_override`** (e.g. `800` for floor demos, `50000` with tier `raksha` for high-income / cap demos) in non-production environments.

---

### Rider APIs

#### `GET /rider/{rider_id}/dashboard`

Returns the rider's full coverage summary — active policy, premium breakdown, zone details, and weekly payout headroom.

**Response:**
```json
{
  "rider_id": 1,
  "name": "Arjun Kumar",
  "tier": "kavach",
  "platform": "swiggy",
  "city": "Chennai",
  "policy_id": 1,
  "policy_status": "active",
  "weekly_premium": 15.00,
  "weekly_payout_cap": 1500.00,
  "premium_breakdown": {
    "income": 3500.0,
    "tier_rate": 0.015,
    "zone_risk": 1.20,
    "seasonal_factor": 1.0,
    "raw_premium": 63.0,
    "floor_applied": true,
    "cap_applied": false,
    "final_premium": 15.00
  },
  "zones": [
    {
      "zone_id": 1,
      "area_name": "George Town",
      "city": "Chennai",
      "polygon": [{ "lat": 13.0827, "lng": 80.2707 }, "..."],
      "risk_multiplier": 1.20,
      "is_active": true,
      "registration_cap": 1000
    }
  ],
  "baseline_weekly_income": 3500.00,
  "baseline_weekly_hours": 40.0,
  "baseline_hourly_rate": 87.5,
  "is_seasoning": true,
  "already_paid_this_week": 0.0,
  "remaining_headroom": 1500.0,
  "cycle_start_date": "2026-04-02",
  "cycle_end_date": "2026-04-30",
  "days_remaining": 28,
  "trust_score": 50.0
}
```

---

#### `GET /rider/{rider_id}/payouts`

Returns full claim and payout history with gate evaluation results.

**Query Params:** `limit` (default 50, max 200), `offset` (default 0)

**Response:**
```json
{
  "rider_id": 1,
  "total_paid": 450.00,
  "total_claims": 3,
  "approved_claims": 2,
  "rejected_claims": 1,
  "claims": [
    {
      "claim_id": 10,
      "disruption_event_id": 5,
      "event_type": "heavy_rain",
      "severity": "severe_l1",
      "gate_results": {
        "zone_overlap": true,
        "shift_window": true,
        "platform_inactivity": true,
        "location_verified": true
      },
      "is_eligible": true,
      "ineligibility_reason": null,
      "lost_hours": 4.5,
      "hourly_rate": 87.5,
      "severity_rate": 0.6,
      "calculated_payout": 236.25,
      "final_payout": 236.25,
      "status": "paid",
      "created_at": "2026-03-28T10:00:00+05:30"
    }
  ]
}
```

---

#### `POST /rider/{rider_id}/renew`

Creates a new 4-week policy after the current cycle ends. Re-computes premium with updated baseline data.

- Blocks renewal if an active policy is still mid-cycle
- Automatically graduates rider from seasoning if ≥ 4 weeks have passed
- Expires any stale `active` policies whose `cycle_end_date` is in the past

**Response (`201 Created`):**
```json
{
  "rider_id": 1,
  "policy_id": 8,
  "tier": "kavach",
  "weekly_premium": 15.00,
  "weekly_payout_cap": 1500.00,
  "premium_breakdown": { "..." },
  "cycle_start_date": "2026-04-30",
  "cycle_end_date": "2026-05-28",
  "message": "Policy renewed successfully. New cycle: 2026-04-30 → 2026-05-28. Weekly premium: ₹15.0."
}
```

---

#### `POST /rider/{rider_id}/change-tier`

Changes the rider's insurance tier. Only allowed at cycle boundary (after current policy expires).

**Request Body:**
```json
{
  "new_tier": "suraksha"
}
```

**Response:**
```json
{
  "rider_id": 1,
  "old_tier": "kavach",
  "new_tier": "suraksha",
  "effective_from": "2026-04-30",
  "message": "Tier changed from 'kavach' to 'suraksha'. Your new premium will apply from the next policy cycle."
}
```

**Validations:** Returns `409 Conflict` if an active mid-cycle policy exists.

---

### Utility APIs

#### `GET /zones`

Returns all delivery zones. Optionally filter by city.

**Query Params:** `city` (optional, case-insensitive partial match)

**Example:** `GET /zones?city=Chennai`

**Response:**
```json
[
  {
    "zone_id": 1,
    "city": "Chennai",
    "area_name": "George Town",
    "polygon": [
      { "lat": 13.0827, "lng": 80.2707 },
      { "lat": 13.0850, "lng": 80.2750 },
      { "lat": 13.0800, "lng": 80.2780 }
    ],
    "risk_multiplier": 1.20,
    "is_active": true,
    "registration_cap": 1000
  }
]
```

---

#### `GET /tiers`

Returns all static tier definitions with rates, caps, and coverage triggers.

**Response:**
```json
[
  {
    "name": "Kavach",
    "display_name": "Kavach — Basic Protection",
    "tier_rate": 0.015,
    "tier_rate_percent": "1.5%",
    "weekly_payout_cap": 1500.00,
    "coverage_type": "income_disruption",
    "coverage_triggers": ["heavy_rain", "cyclone", "flood"],
    "description": "Entry-level coverage for basic income disruption events",
    "premium_floor": 15.0,
    "premium_cap_percent": "3.5%"
  },
  {
    "name": "Suraksha",
    "display_name": "Suraksha — Standard Protection",
    "tier_rate": 0.018,
    "tier_rate_percent": "1.8%",
    "weekly_payout_cap": 3000.00,
    "coverage_triggers": ["heavy_rain", "cyclone", "flood", "poor_aqi", "extreme_heat"],
    "..."
  },
  {
    "name": "Raksha",
    "display_name": "Raksha — Premium Protection",
    "tier_rate": 0.022,
    "tier_rate_percent": "2.2%",
    "weekly_payout_cap": 5000.00,
    "coverage_triggers": ["heavy_rain", "cyclone", "flood", "poor_aqi", "extreme_heat", "civic_disruption", "storm"],
    "..."
  }
]
```

---

### Admin APIs

> **All admin endpoints require:**
> ```
> Authorization: Bearer admin_token
> ```
> Returns `403 Forbidden` if header is missing or incorrect.

---

#### `GET /admin/workers`

Lists all riders. Supports filtering and pagination.

**Query Params:** `platform`, `zone_id`, `tier`, `limit` (max 200), `offset`

**Response:** Array of rider objects (same shape as `riders.to_dict()`)

---

#### `GET /admin/workers/{rider_id}`

Fetches a single rider with their active policy attached.

**Response:**
```json
{
  "id": 1,
  "partner_id": "SWG-CHN-001",
  "name": "Arjun Kumar",
  "tier": "kavach",
  "trust_score": 50.0,
  "is_blocked": false,
  "kyc_verified": true,
  "active_policy": {
    "id": 1,
    "status": "active",
    "weekly_premium": 15.00,
    "cycle_end_date": "2026-04-30"
  }
}
```

---

#### `PATCH /admin/workers/{rider_id}/block`

Blocks or unblocks a rider.

**Request Body:**
```json
{ "is_blocked": true }
```

**Response:**
```json
{ "message": "Worker blocked status set to true", "rider_id": 1 }
```

---

#### `PATCH /admin/workers/{rider_id}/verify-kyc`

Marks a rider's KYC as verified.

**Response:**
```json
{ "message": "Worker KYC verified", "rider_id": 1 }
```

---

#### `GET /admin/claims/live`

Returns up to 100 most recent pending claims across all riders.

**Response:** Array of claim objects ordered by `created_at DESC`

---

#### `GET /admin/claims/{rider_id}`

Returns all claims for a specific rider.

---

#### `POST /admin/mock/create-claim`

Creates a **demo** pending claim against the first available **active** policy (if no pending claim already exists for that rider/policy). Intended for **claim override** walkthroughs when the database has no claims yet.

| | |
|---|---|
| **Auth** | `Authorization: Bearer admin_token` |
| **Production** | Returns **404 Not found** when `ENVIRONMENT=production`. |
| **Idempotent** | If a pending claim already exists for that rider, returns the existing `claim_id` and a short message. |

**Response (example):**
```json
{
  "message": "Demo claim created",
  "claim_id": 1,
  "rider_id": 1,
  "policy_id": 1
}
```

> After a fresh `db/seed.sql`, a sample pending claim may already exist for seed rider `SWG-CHN-001`; use `GET /admin/claims/live` to see it, or this endpoint to create one on empty DBs.

---

#### `PATCH /admin/claims/{claim_id}/override`

Admin override for a claim's status and/or payout amount.

**Request Body (example):**
```json
{
  "status": "approved",
  "final_payout": 750
}
```

**Valid statuses:** `approved | rejected | paid | failed`

---

#### `GET /admin/payouts`

Returns paginated payout records across all riders.

**Query Params:** `limit` (default 50), `offset` (default 0)

---

#### `GET /admin/fraud/flagged`

Returns users flagged for high-frequency claims or suspicious behavior.

**Response:**
```json
{
  "flagged_users": [
    {
      "rider_id": 12,
      "reason": "High claim frequency across multiple adjacent bins",
      "risk_score": 0.92,
      "flagged_at": "2026-03-31T10:00:00Z"
    }
  ]
}
```

---

#### `GET /admin/fraud/zone-anomalies`

Returns zones with disproportionately high claim volumes.

**Response:**
```json
{
  "anomalous_zones": [
    {
      "zone_id": 3,
      "anomaly_type": "disproportionate_claims",
      "description": "Claim volume is 3x higher than average",
      "severity": "high"
    }
  ]
}
```

---

#### `GET /admin/fraud/referrals`

Returns suspicious referral clusters (simultaneous onboardings with identical activity windows).

---

#### `GET /admin/fraud/collusion`

Returns suspected collusion rings (multiple riders sharing zone + activity fingerprints).

---

#### `GET /admin/zones`

Returns all zones (admin view, no city filter required).

---

#### `PATCH /admin/zones/{zone_id}/toggle`

Activates or deactivates a zone for new registrations.

**Request Body:**
```json
{ "is_active": false }
```

---

#### `GET /admin/zones/{zone_id}/events`

Returns all disruption events for a specific zone, ordered by `event_start DESC`.

---

#### `GET /admin/analytics/financial`

Computes live financial analytics from real database data.

**Response:**
```json
{
  "total_premiums": 8420.50,
  "total_payouts": 3180.75,
  "loss_ratio": 0.3777,
  "total_liability": 25500.00,
  "payout_cap_utilization": 0.1247,
  "churn_rate": 0.1200
}
```

| Metric | Calculation |
|---|---|
| `loss_ratio` | `total_payouts / total_premiums` |
| `payout_cap_utilization` | `total_payouts / sum(active weekly_payout_cap)` |
| `churn_rate` | `1 - (active_policies / total_riders)` |

---

#### `GET /admin/config`

Returns current system configuration: tier parameters, fraud thresholds, and batch job status. Values are **defaults merged with** any overrides stored in **`.admin_runtime_config.json`** (see `PATCH /admin/config` below).

**Response:**
```json
{
  "tier_parameters": { "kavach": { "..." }, "suraksha": { "..." }, "raksha": { "..." } },
  "fraud_thresholds": {
    "high_claim_frequency": 3,
    "collusion_proximity_meters": 50
  },
  "batch_job_status": {
    "last_premium_run": "2026-03-31T01:00:00Z",
    "last_gate_eval": "2026-03-31T03:00:00Z"
  }
}
```

---

#### `PATCH /admin/config`

Updates system configuration (fraud thresholds, optional `batch_job_status` keys, etc.). Changes are **merged** with defaults and **persisted** for the next process start.

**Persistence & safety**

| | |
|---|---|
| **Storage** | JSON file: **`.admin_runtime_config.json`** at the project root (same directory level as `main.py`). |
| **First write** | The file is created on the first successful **PATCH**. If the file is missing, **GET** still returns full defaults (no crash). |
| **Concurrency** | Reads and writes use a **thread lock** so concurrent PATCH/GET calls do not corrupt the file. |
| **Corrupt file** | If the file cannot be parsed, overrides are ignored and a warning is logged; **GET** still returns defaults. |

**Request Body:**
```json
{
  "fraud_thresholds": { "high_claim_frequency": 5 },
  "update_message": "Relaxing frequency threshold for Diwali period"
}
```

---

## 6. Registration Flow (Step-by-Step)

```
POST /register
     │
     ▼
Step 1: Check partner_id uniqueness
     │  → 409 Conflict if already registered
     │
     ▼
Step 2: Check phone uniqueness
     │  → 409 Conflict if phone already exists
     │
     ▼
Step 3: Validate zone IDs exist in DB
     │  → 400 Bad Request if any zone_id is unknown
     │  → Check all zones belong to the requested city
     │    (prevents cross-city zone assignments)
     │
     ▼
Step 3b: Persist polygon data (if zones[] provided)
     │  → Serialize each LatLngPoint → {lat, lng}
     │  → Write polygon JSONB back to zone record
     │  → Uses db.add() — persisted in the same transaction
     │
     ▼
Step 4: Call Module 2 → get_baseline()
     │  → Input: partner_id, city, is_seasoning=True
     │  → Output: income, hours, hourly_rate, is_provisional
     │  → New riders always start with is_seasoning=True
     │    (city-median income used as provisional baseline)
     │
     ▼
Step 4b: (Optional) demo_income_override
     │  → If provided and allowed in this environment: replace income
     │    (keep hours from baseline); then continue to PRICING
     │
     ▼
Step 5: Call Module 2 → calculate_premium()
     │  → Input: income, tier, zone_ids
     │  → Formula: income × tier_rate × zone_risk × seasonal_factor
     │  → Applies ₹15 floor and 3.5% income cap
     │  → Returns breakdown + final_premium
     │
     ▼
Step 6: Create Rider record
     │  → Uses db.flush() to get rider.id without committing
     │  → trust_score defaults to 50.00
     │  → is_seasoning = True (always for new riders)
     │
     ▼
Step 7: Create Policy record (4-week cycle)
     │  → cycle_end = today + 28 days (DB-enforced)
     │  → Stores premium_breakdown as JSONB snapshot
     │  → status = 'active'
     │
     ▼
Step 8: Atomic commit
     │  → Both rider and policy committed atomically
     │  → IntegrityError → rollback + 409 response
     │
     ▼
Step 9: Return RegisterRiderResponse
        → rider_id, policy_id, premium details, cycle dates
```

---

## 7. Admin System

The admin layer provides operational control over the platform without requiring direct database access.

### Use Cases

| Feature | Endpoint | Use Case |
|---|---|---|
| **Worker Management** | `GET /admin/workers` | Audit registered riders by platform/zone/tier |
| **KYC Verification** | `PATCH /admin/workers/{id}/verify-kyc` | Manually approve a rider's identity documents |
| **Block/Unblock** | `PATCH /admin/workers/{id}/block` | Suspend a rider suspected of fraud |
| **Live Claims** | `GET /admin/claims/live` | Monitor incoming pending claims in real-time |
| **Mock Claim (demo)** | `POST /admin/mock/create-claim` | Create a pending claim for override demos (disabled in production) |
| **Claim Override** | `PATCH /admin/claims/{id}/override` | Manually approve/reject edge-case claims |
| **Fraud: Flagged** | `GET /admin/fraud/flagged` | Review high-risk riders flagged by risk engine |
| **Fraud: Zone Anomalies** | `GET /admin/fraud/zone-anomalies` | Detect zones with disproportionate claim activity |
| **Fraud: Referrals** | `GET /admin/fraud/referrals` | Identify suspicious onboarding clusters |
| **Fraud: Collusion** | `GET /admin/fraud/collusion` | Detect coordinated claim rings |
| **Zone Deactivation** | `PATCH /admin/zones/{id}/toggle` | Close a zone to new registrations |
| **Financial Analytics** | `GET /admin/analytics/financial` | Monitor loss ratio, premiums, and payout utilization |
| **System Config** | `GET/PATCH /admin/config` | View/update fraud thresholds and batch job status |

### Authentication

The current implementation uses a **static Bearer token** (`admin_token`) for simplicity. In production, this should be replaced with a proper JWT-based role system verified against Firebase Admin or an internal IAM service.

---

## 8. Polygon Zone Handling

### Why Polygon Instead of Pincode?

Traditional pincode-based zone systems have several problems:
1. **Pincodes are too broad** — a single pincode can span 10–15 km², making precise risk assessment impossible
2. **Pincodes don't align with delivery density** — high-activity micro-zones exist within a single pincode
3. **No boundary precision** — a rider 50m outside a flood-affected pincode is incorrectly included/excluded

Polygon-based zones allow:
- **Precise geographic boundaries** defined by actual delivery micro-markets
- **Accurate zone overlap checks** during claim eligibility (Module 3 gates)
- **Risk differentiation within a city** (e.g., low-lying vs. elevated areas in Chennai)

### Data Format

Polygons are stored as **JSONB arrays** of coordinate objects:

```json
[
  { "lat": 13.0827, "lng": 80.2707 },
  { "lat": 13.0850, "lng": 80.2750 },
  { "lat": 13.0800, "lng": 80.2780 },
  { "lat": 13.0790, "lng": 80.2720 }
]
```

### Validation Rules

| Rule | Where Enforced |
|---|---|
| Minimum 3 coordinate points | Pydantic `field_validator` on `polygon` field |
| `lat` within `[-90, 90]` | Pydantic `Field(ge=-90.0, le=90.0)` |
| `lng` within `[-180, 180]` | Pydantic `Field(ge=-180.0, le=180.0)` |
| `zone_id` must match declared zones | `model_validator(mode="after")` on `RegisterRiderRequest` |
| No duplicate zone_ids in polygon list | Same model validator |
| Zone risk multiplier `0.80 – 1.50` | PostgreSQL `CHECK` constraint on `zones` table |

### Seeded Zone Example

All 20 zones in `seed.sql` come pre-populated with real lat/lng polygon coordinates for:

| City | Zones |
|---|---|
| Chennai | George Town, Sowcarpet, Egmore, Nungambakkam, Adyar, Anna Nagar, Ambattur Industrial, Perungudi |
| Mumbai | Fort, Bandra West, Goregaon, Kurla |
| Bangalore | MG Road, Koramangala, Whitefield, Electronic City |
| Delhi | Connaught Place, Saket, Badarpur, Shahdara |

---

## 9. Setup Instructions

### Prerequisites

- Python 3.11+
- PostgreSQL 14+ (running locally or via Docker)
- `pip` or `pip3`

### Step 1: Clone the Repository

```bash
git clone <repo-url>
cd module1-registration
```

### Step 2: Create and Activate Virtual Environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Configure Environment Variables

```bash
cp .env.example .env
```

Edit `.env`:

```env
# Application
APP_NAME=RahatPay Module 1
APP_VERSION=1.0.0
DEBUG=True
ENVIRONMENT=development

# Database
DATABASE_URL=postgresql+asyncpg://rahatpay:rahatpay@localhost:5432/rahatpay
DB_ECHO=False

# Firebase (set to True for local dev — uses OTP 000000)
FIREBASE_MOCK_MODE=True

# Module 2 (set to True for standalone dev, False if Module 2 is available)
MODULE2_MOCK_MODE=True

# Production: use production + disable demo-only registration field (recommended)
# ENVIRONMENT=production
# ALLOW_DEMO_INCOME_OVERRIDE=false
```

| Variable | Purpose |
|----------|---------|
| `ENVIRONMENT` | When set to **`production`**, `demo_income_override` on `POST /register` is **rejected** (400), and **`POST /admin/mock/create-claim`** returns **404**. Use `development` (or any non-`production` value) for local demos. |
| `ALLOW_DEMO_INCOME_OVERRIDE` | Default **`true`**. Set to **`false`** to reject `demo_income_override` even outside production (e.g. staging policy). |

### Step 5: Create the PostgreSQL Database

```bash
psql -U postgres

CREATE USER rahatpay WITH PASSWORD 'rahatpay';
CREATE DATABASE rahatpay OWNER rahatpay;
\q
```

### Step 6: Run Schema

```bash
psql -U rahatpay -d rahatpay -f db/schema.sql
```

This creates all 6 tables, indexes, triggers, and constraints.

### Step 7: Run Seed Data

```bash
psql -U rahatpay -d rahatpay -f db/seed.sql
```

This inserts:
- 20 zones across 4 cities with polygon data
- 3 sample riders (Arjun/Chennai/Kavach, Priya/Mumbai/Suraksha, Ravi/Bangalore/Raksha)
- 3 active policies (one per rider)
- A **demo pending claim** for seed rider `SWG-CHN-001` (idempotent — skipped if one already exists), for admin override demos

> **Alternatively**, seed data runs automatically on first startup when `ENVIRONMENT=development` and the zones table is empty.

### Step 8: (Optional) Docker Setup

```bash
docker-compose up --build
```

The `docker-compose.yml` starts both PostgreSQL and the FastAPI app. The app is available at `http://localhost:8001`.

---

## 10. Running the Server

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8001
```

Or run directly:

```bash
python main.py
```

The server starts on **port 8001** by default.

| URL | Description |
|---|---|
| `http://localhost:8001/` | Module metadata and endpoint index |
| `http://localhost:8001/health` | Liveness probe (includes DB health check) |
| `http://localhost:8001/health/details` | DB status + table counts (riders, policies, zones) |
| `http://localhost:8001/docs` | Swagger UI — interactive API explorer |
| `http://localhost:8001/redoc` | ReDoc — clean API documentation |

---

## 11. Demo Walkthrough

Short path to validate the stack end-to-end (use Swagger at `/docs` or `curl`; admin calls need `Authorization: Bearer admin_token`).

### Step 1: Normal registration

`POST /register` with valid `zone1_id` / `city` from `GET /zones?city=Chennai`. Omit `demo_income_override`. Confirm `201` and `weekly_premium` / `premium_breakdown` in the response.

### Step 2: Low income demo (₹15 floor)

Register another rider (unique `partner_id` / `phone`) with tier **`kavach`** and e.g. **`"demo_income_override": 800`**. Expect `premium_breakdown.floor_applied: true` and `weekly_premium` ≥ **15**.

### Step 3: High income demo (3.5% cap)

Register with tier **`raksha`** and e.g. **`"demo_income_override": 50000`**. Expect `premium_breakdown.income: 50000` and `final_premium` ≤ **3.5% × income** (plus float tolerance), and still ≥ **15** after floor logic.

### Step 4: Create / override claim

1. `GET /admin/claims/live` — note a pending `claim_id`, or run `POST /admin/mock/create-claim` (non-production) to create one.
2. `PATCH /admin/claims/{claim_id}/override` with body:

```json
{
  "status": "approved",
  "final_payout": 750
}
```

### Step 5: View analytics

`GET /admin/analytics/financial` — totals, `loss_ratio`, and related KPIs from live DB data.

### Step 6: Check health

- `GET /health` — liveness and DB connectivity.
- `GET /health/details` — `db_status` plus `total_riders`, `total_policies`, `total_zones`.

---

## 12. Testing APIs

### Swagger UI (Recommended)

Navigate to `http://localhost:8001/docs`. All endpoints are interactive — you can send requests directly from the browser.

### Admin Authentication

For all `/admin/*` endpoints, add this header:

```
Authorization: Bearer admin_token
```

In Swagger UI: click **Authorize** (top right) and enter `Bearer admin_token`.

### Quick Smoke Tests

```bash
# Health check
curl http://localhost:8001/health

# List zones in Chennai
curl "http://localhost:8001/zones?city=Chennai"

# List available tiers
curl http://localhost:8001/tiers

# Register a new rider
curl -X POST http://localhost:8001/register \
  -H "Content-Type: application/json" \
  -d '{
    "partner_id": "TEST-001",
    "platform": "swiggy",
    "name": "Test Rider",
    "phone": "9000000001",
    "kyc": { "type": "aadhaar", "value": "1234" },
    "city": "Chennai",
    "zone1_id": 1,
    "tier": "kavach"
  }'

# Admin: list all workers
curl http://localhost:8001/admin/workers \
  -H "Authorization: Bearer admin_token"

# Admin: financial analytics
curl http://localhost:8001/admin/analytics/financial \
  -H "Authorization: Bearer admin_token"
```

### Running Tests

```bash
pytest tests/ -v
```

The suite includes **127** passing tests (registration, rider/policy routes, admin APIs, validation, fraud stubs, financial analytics, DB integrity, and premium edge cases). Run against a dedicated database (e.g. `rahatpay_test`) as configured in the test modules.

---

## 13. Integration Notes

### How Module 2 Connects

Module 2 (Risk Engine & Premium Calculator) is integrated via **direct Python import**, not HTTP:

```python
# integrations/module2_adapter.py
from baseline.profiler import get_baseline as _m2_get_baseline
from premium.calculator import calculate_premium as _m2_calculate_premium
```

Module 1 calls Module 2 at two points:
1. **Registration (`POST /register`)** — to get seasoning baseline and compute first premium
2. **Renewal (`POST /rider/{id}/renew`)** — to refresh baseline (rider may have graduated from seasoning) and recompute premium

If Module 2 is not available, the adapter falls back to a mock that:
- Uses city-level median income tables (Chennai: ₹3,500/week, Mumbai: ₹4,200/week, etc.)
- Applies a zone-risk lookup table that mirrors Module 2's XGBoost output
- Applies seasonal factors (June–August peak monsoon: 1.25×)

**To connect real Module 2:** Set `MODULE2_MOCK_MODE=False` in `.env`. The module must be importable from `../../module2-risk-engine/`.

### How Module 3 Uses Module 1

Module 3 (Claims & Payouts) **reads** from Module 1's database tables:

| Table | What Module 3 Reads |
|---|---|
| `riders` | `id`, `trust_score`, `zone1_id`, `zone2_id`, `zone3_id`, `is_blocked`, `baseline_weekly_income`, `baseline_weekly_hours` |
| `policies` | Active policy for a rider (to check coverage and payout cap) |
| `zones` | Polygon data for zone overlap gate evaluation |
| `disruption_events` | Events in `pending` status that need to generate claims |

Module 3 **writes** to:
- `claims` — one claim per eligible rider per disruption event
- `payouts` — payment records for approved claims

Module 3 sets `disruption_events.processing_status = 'processed'` once claims are generated for an event.

---

## 14. Design Decisions

### Why JSONB for Polygons?

1. **No PostGIS dependency** — PostGIS requires an extension and adds operational complexity. JSONB works out-of-the-box with standard PostgreSQL.
2. **Flexibility** — The polygon schema can evolve (e.g., add altitude, metadata) without schema migrations.
3. **Validation at application layer** — Pydantic validators enforce coordinate bounds and minimum point counts before data reaches the DB.
4. **PostGIS migration path** — The column is explicitly commented as a candidate for PostGIS `GEOMETRY(POLYGON)` in production when spatial queries become a bottleneck.

### Why Integer Identity Keys?

1. **Performance** — Integer PKs are faster for joins, indexing, and range scans than UUIDs.
2. **`GENERATED ALWAYS AS IDENTITY`** — PostgreSQL standard (SQL:2003); prevents accidental manual insertion, guaranteeing the sequence controls the key.
3. **Readability** — Easier to reference in logs, support tickets, and API paths (`/rider/42`) than UUIDs.
4. **No application-level UUID generation** — Removes a class of bugs where UUIDs could be duplicated or misformatted.

### Why an Admin Layer?

1. **Operability without DB access** — Ops teams can monitor fraud, block users, and run analytics without needing raw SQL access to production.
2. **Audit trail** — All admin actions go through the API, which can be logged and audited centrally.
3. **Separation of concerns** — Admin logic is isolated in `routes/admin.py` with its own auth dependency and is never exposed in the public API.
4. **Fraud governance** — The fraud endpoints provide a structured interface that can be backed by an ML model in production without changing the API contract.

### Why 4-Week Policy Cycles?

1. **Fraud prevention** — A fixed lock-in period prevents riders from gaming the system (e.g., registering during a storm, collecting, then cancelling).
2. **Actuarial soundness** — Premiums are computed on 4-week income baselines; the cycle aligns the premium collection window with the baseline measurement window.
3. **DB-enforced** — The `policy_4week_cycle` CHECK constraint ensures no policy can be created with a non-28-day window, even if application logic has a bug.

---

## 15. Future Improvements

### PostGIS Integration
Replace the JSONB polygon storage with PostgreSQL's native `GEOMETRY(POLYGON, 4326)` type using PostGIS. This enables true spatial queries for zone overlap checks (`ST_Intersects`, `ST_Contains`) that are currently computed in Python by Module 3.

### Rider-Zone Normalization
Replace the `zone1_id / zone2_id / zone3_id` flat columns with a proper `rider_zones` junction table, allowing dynamic zone assignment (more than 3 zones) and easier querying.

```sql
-- Future schema
CREATE TABLE rider_zones (
    rider_id INTEGER REFERENCES riders(id),
    zone_id  INTEGER REFERENCES zones(zone_id),
    priority INTEGER NOT NULL,
    PRIMARY KEY (rider_id, zone_id)
);
```

### Real Fraud ML Integration
The current fraud endpoints return static mock data. Future integration should:
- Connect to an anomaly detection model (e.g., Isolation Forest or DBSCAN) that runs on claim patterns
- Provide a feedback loop where admin decisions (block/unblock) are used as training labels

### JWT-Based Admin Auth
Replace the static `admin_token` with proper JWT validation:
- Issue short-lived tokens via Firebase Admin or an internal IAM service
- Encode `role=admin` in the JWT claims
- Support role hierarchy (e.g., `viewer`, `ops`, `superadmin`)

### Alembic Migration Pipeline
Move from raw `schema.sql` execution to Alembic-managed migrations for production deployments, enabling zero-downtime schema changes with rollback support.

### Registration Cap Enforcement
The `zones.registration_cap` column is stored but not yet enforced in the registration flow. A future improvement would count active riders per zone and reject registrations that exceed the cap.

---

## Health Check

### `GET /health`

```bash
GET /health
```

```json
{
  "status": "healthy",
  "module": "module1-registration",
  "version": "1.0.0",
  "database": "connected"
}
```

Returns `degraded` if the database connection fails, enabling load balancer health probes to route traffic away from unhealthy instances.

### `GET /health/details`

Returns **`db_status`** plus row counts for a quick operational snapshot (demos and debugging).

**Example:**

```json
{
  "db_status": "connected",
  "total_riders": 4,
  "total_policies": 4,
  "total_zones": 20
}
```

If the database is unreachable, `db_status` is `disconnected` and count fields are `null`. If the DB is up but a count query fails, `db_status` may be `degraded` with `null` counts.

---

*Module 1 — RahatPay Registration & Policy Management*
*FastAPI + PostgreSQL | Async SQLAlchemy | JSONB Polygons | Firebase Auth*
