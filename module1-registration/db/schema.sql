-- ============================================================
-- RahatPay — Module 1: Full Database Schema
-- Owner: Module 1 (Registration & Policy Management)
-- All other modules READ from these tables.
-- ============================================================

-- ============================================================
-- 1. ZONES (read-only reference table)
-- ============================================================
CREATE TABLE IF NOT EXISTS zones (
    zone_id         INTEGER         GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    city            VARCHAR(100)    NOT NULL,
    area_name       VARCHAR(200)    NOT NULL,
    -- Polygon stored as JSONB; can be migrated to PostGIS in production.
    polygon         JSONB           NOT NULL DEFAULT '[]',
    risk_multiplier NUMERIC(4, 2)   NOT NULL
        CHECK (risk_multiplier BETWEEN 0.80 AND 1.50),
    is_active       BOOLEAN         NOT NULL DEFAULT TRUE,
    registration_cap INTEGER        NOT NULL DEFAULT 1000,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_zones_city ON zones(city);

-- ============================================================
-- 2. RIDERS
-- ============================================================
CREATE TABLE IF NOT EXISTS riders (
    id                      INTEGER         GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    partner_id              VARCHAR(100)    NOT NULL UNIQUE,
    platform                VARCHAR(20)     NOT NULL
        CHECK (platform IN ('swiggy', 'zomato', 'dunzo', 'other')),
    name                    VARCHAR(200)    NOT NULL,
    phone                   VARCHAR(15)     NOT NULL UNIQUE,
    -- KYC: one of these must be non-null (enforced via CHECK)
    aadhaar_last4           CHAR(4)         CHECK (aadhaar_last4 ~ '^\d{4}$'),
    pan                     VARCHAR(10)     CHECK (pan ~ '^[A-Z]{5}[0-9]{4}[A-Z]$'),
    -- At least one KYC identifier must be provided
    CONSTRAINT kyc_required CHECK (
        aadhaar_last4 IS NOT NULL OR pan IS NOT NULL
    ),
    city                    VARCHAR(100)    NOT NULL,
    -- Future improvement: normalize into rider_zones table.
    -- Zone FKs (rider covers up to 3 zones; zone1 is mandatory)
    zone1_id                INTEGER         NOT NULL REFERENCES zones(zone_id),
    zone2_id                INTEGER         REFERENCES zones(zone_id),
    zone3_id                INTEGER         REFERENCES zones(zone_id),
    -- Tier
    tier                    VARCHAR(20)     NOT NULL
        CHECK (tier IN ('kavach', 'suraksha', 'raksha')),
    -- Baseline financials (populated from Module 2)
    baseline_weekly_income  NUMERIC(10, 2)  CHECK (baseline_weekly_income >= 0),
    baseline_weekly_hours   NUMERIC(6, 2)   CHECK (baseline_weekly_hours >= 0),
    daily_income_history    JSONB           DEFAULT '[]'::jsonb,
    -- Seasoning: TRUE for riders < 4 weeks old (no real baseline yet)
    is_seasoning            BOOLEAN         NOT NULL DEFAULT TRUE,
    -- Trust score (0-100), used by Module 3 gate checks
    trust_score             NUMERIC(5, 2)   NOT NULL DEFAULT 50.00
        CHECK (trust_score BETWEEN 0 AND 100),
    -- Admin features
    is_blocked              BOOLEAN         NOT NULL DEFAULT FALSE,
    kyc_verified            BOOLEAN         NOT NULL DEFAULT FALSE,
    -- Audit
    created_at              TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_riders_phone        ON riders(phone);
CREATE INDEX IF NOT EXISTS idx_riders_partner_id   ON riders(partner_id);
CREATE INDEX IF NOT EXISTS idx_riders_city         ON riders(city);
CREATE INDEX IF NOT EXISTS idx_riders_zone1        ON riders(zone1_id);

-- Auto-update updated_at
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_riders_updated_at
    BEFORE UPDATE ON riders
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ============================================================
-- 3. POLICIES
-- ============================================================
CREATE TABLE IF NOT EXISTS policies (
    id                  INTEGER         GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    rider_id            INTEGER         NOT NULL REFERENCES riders(id) ON DELETE RESTRICT,
    tier                VARCHAR(20)     NOT NULL
        CHECK (tier IN ('kavach', 'suraksha', 'raksha')),
    -- Premium (minimum ₹15 enforced by CHECK)
    weekly_premium      NUMERIC(10, 2)  NOT NULL
        CHECK (weekly_premium >= 15),
    -- Premium breakdown (JSONB for flexibility)
    -- Shape: { income, tier_rate, zone_risk, seasonal_factor, floor_applied, cap_applied }
    premium_breakdown   JSONB           NOT NULL DEFAULT '{}',
    -- Payout cap per week (from tier config)
    weekly_payout_cap   NUMERIC(10, 2)  NOT NULL
        CHECK (weekly_payout_cap > 0),
    -- Coverage details
    coverage_type       VARCHAR(100)    NOT NULL,
    -- Status
    status              VARCHAR(20)     NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'expired', 'cancelled', 'pending')),
    -- 4-week cycle
    cycle_start_date    DATE            NOT NULL,
    cycle_end_date      DATE            NOT NULL
        CHECK (cycle_end_date > cycle_start_date),
    -- Ensure 4-week (28-day) cycle
    CONSTRAINT policy_4week_cycle CHECK (
        cycle_end_date = cycle_start_date + INTERVAL '28 days'
    ),
    -- Audit
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_policies_rider_id    ON policies(rider_id);
CREATE INDEX IF NOT EXISTS idx_policies_status      ON policies(status);
CREATE INDEX IF NOT EXISTS idx_policies_cycle_end   ON policies(cycle_end_date);

CREATE TRIGGER trg_policies_updated_at
    BEFORE UPDATE ON policies
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ============================================================
-- 4. DISRUPTION EVENTS (created here, consumed by Module 3)
-- ============================================================
CREATE TABLE IF NOT EXISTS disruption_events (
    id              INTEGER         GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    event_type      VARCHAR(50)     NOT NULL
        CHECK (event_type IN (
            'heavy_rain', 'cyclone', 'flood', 'extreme_heat',
            'poor_aqi', 'civic_disruption', 'storm', 'other'
        )),
    severity        VARCHAR(20)     NOT NULL
        CHECK (severity IN ('moderate', 'severe_l1', 'severe_l2', 'extreme')),
    -- Severity → payout rate mapping (stored for audit trail)
    payout_rate     NUMERIC(5, 4)   NOT NULL
        CHECK (payout_rate BETWEEN 0 AND 1),
    affected_zone   INTEGER         NOT NULL REFERENCES zones(zone_id),
    -- Raw trigger data (from weather APIs)
    trigger_data    JSONB           NOT NULL DEFAULT '{}',
    -- Event window
    event_start     TIMESTAMPTZ     NOT NULL,
    event_end       TIMESTAMPTZ,
    CHECK (event_end IS NULL OR event_end > event_start),
    -- Module 3 sets this to 'processed' once claims are generated
    processing_status VARCHAR(20)   NOT NULL DEFAULT 'pending'
        CHECK (processing_status IN ('pending', 'processing', 'processed', 'failed')),
    -- Audit
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_disruption_zone      ON disruption_events(affected_zone);
CREATE INDEX IF NOT EXISTS idx_disruption_status    ON disruption_events(processing_status);
CREATE INDEX IF NOT EXISTS idx_disruption_start     ON disruption_events(event_start);

CREATE TRIGGER trg_disruption_updated_at
    BEFORE UPDATE ON disruption_events
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ============================================================
-- 5. CLAIMS
-- ============================================================
CREATE TABLE IF NOT EXISTS claims (
    id                      INTEGER         GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    rider_id                INTEGER         NOT NULL REFERENCES riders(id) ON DELETE RESTRICT,
    policy_id               INTEGER         NOT NULL REFERENCES policies(id) ON DELETE RESTRICT,
    disruption_event_id     INTEGER         NOT NULL REFERENCES disruption_events(id),
    -- Gate results (Module 3 populates this)
    gate_results            JSONB           NOT NULL DEFAULT '{}'
        -- Shape: { zone_overlap, shift_window, platform_inactivity, location_verified }
        CHECK (jsonb_typeof(gate_results) = 'object'),
    -- Eligibility
    is_eligible             BOOLEAN         NOT NULL DEFAULT FALSE,
    ineligibility_reason    TEXT,
    -- Calculation inputs (snapshot at time of claim)
    lost_hours              NUMERIC(6, 2)   CHECK (lost_hours >= 0),
    hourly_rate             NUMERIC(10, 2)  CHECK (hourly_rate >= 0),
    severity_rate           NUMERIC(5, 4)   CHECK (severity_rate BETWEEN 0 AND 1),
    calculated_payout       NUMERIC(10, 2)  CHECK (calculated_payout >= 0),
    -- CRITICAL CHECK CONSTRAINT: final_payout ≤ 5000
    final_payout            NUMERIC(10, 2)
        CHECK (final_payout >= 0 AND final_payout <= 5000),
    -- Status
    status                  VARCHAR(20)     NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'approved', 'rejected', 'paid', 'failed')),
    -- Audit
    created_at              TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_claims_rider_id      ON claims(rider_id);
CREATE INDEX IF NOT EXISTS idx_claims_policy_id     ON claims(policy_id);
CREATE INDEX IF NOT EXISTS idx_claims_event_id      ON claims(disruption_event_id);
CREATE INDEX IF NOT EXISTS idx_claims_status        ON claims(status);

-- Prevent duplicate claim for same rider + same disruption event
CREATE UNIQUE INDEX IF NOT EXISTS idx_claims_rider_event_unique
    ON claims(rider_id, disruption_event_id);

CREATE TRIGGER trg_claims_updated_at
    BEFORE UPDATE ON claims
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ============================================================
-- 6. PAYOUTS
-- ============================================================
CREATE TABLE IF NOT EXISTS payouts (
    id                  INTEGER         GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    claim_id            INTEGER         NOT NULL REFERENCES claims(id) ON DELETE RESTRICT,
    rider_id            INTEGER         NOT NULL REFERENCES riders(id) ON DELETE RESTRICT,
    -- CRITICAL CHECK CONSTRAINT: amount must be positive and ≤ 5000
    amount              NUMERIC(10, 2)  NOT NULL
        CHECK (amount > 0 AND amount <= 5000),
    -- Payment gateway details
    gateway             VARCHAR(50)     NOT NULL DEFAULT 'razorpay'
        CHECK (gateway IN ('razorpay', 'manual', 'test')),
    gateway_reference   VARCHAR(200),
    gateway_response    JSONB           NOT NULL DEFAULT '{}',
    -- UPI / bank details (hashed in production)
    upi_id              VARCHAR(200),
    -- Status
    status              VARCHAR(20)     NOT NULL DEFAULT 'initiated'
        CHECK (status IN ('initiated', 'processing', 'success', 'failed', 'reversed')),
    -- Timestamps
    initiated_at        TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    completed_at        TIMESTAMPTZ,
    CHECK (completed_at IS NULL OR completed_at >= initiated_at),
    -- Audit
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_payouts_claim_id     ON payouts(claim_id);
CREATE INDEX IF NOT EXISTS idx_payouts_rider_id     ON payouts(rider_id);
CREATE INDEX IF NOT EXISTS idx_payouts_status       ON payouts(status);

CREATE TRIGGER trg_payouts_updated_at
    BEFORE UPDATE ON payouts
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
