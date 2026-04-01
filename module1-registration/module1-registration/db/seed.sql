-- ============================================================
-- RahatPay — Module 1: Seed Data
-- ============================================================

-- ============================================================
-- ZONES (Chennai, Mumbai, Bangalore, Delhi)
-- risk_multiplier from Module 2 XGBoost model output
-- ============================================================
INSERT INTO zones (zone_id, city, area_name, risk_multiplier, polygon) 
OVERRIDING SYSTEM VALUE
VALUES
-- Chennai
(1, 'Chennai',   'George Town',          1.20, '[{"lat": 13.0827, "lng": 80.2707}, {"lat": 13.0850, "lng": 80.2750}, {"lat": 13.0800, "lng": 80.2780}]'::jsonb),
(2, 'Chennai',   'Sowcarpet',            1.15, '[{"lat": 13.0897, "lng": 80.2787}, {"lat": 13.0950, "lng": 80.2850}, {"lat": 13.0850, "lng": 80.2880}]'::jsonb),
(3, 'Chennai',   'Egmore',               1.10, '[{"lat": 13.0783, "lng": 80.2603}, {"lat": 13.0820, "lng": 80.2650}, {"lat": 13.0730, "lng": 80.2680}]'::jsonb),
(4, 'Chennai',   'Nungambakkam',         1.05, '[{"lat": 13.0595, "lng": 80.2425}, {"lat": 13.0650, "lng": 80.2480}, {"lat": 13.0550, "lng": 80.2500}]'::jsonb),
(5, 'Chennai',   'Adyar',                1.00, '[{"lat": 13.0012, "lng": 80.2565}, {"lat": 13.0100, "lng": 80.2650}, {"lat": 12.9900, "lng": 80.2680}]'::jsonb),
(6, 'Chennai',   'Anna Nagar',           0.95, '[{"lat": 13.0850, "lng": 80.2100}, {"lat": 13.0900, "lng": 80.2200}, {"lat": 13.0800, "lng": 80.2250}]'::jsonb),
(7, 'Chennai',   'Ambattur Industrial',  1.25, '[{"lat": 13.1143, "lng": 80.1548}, {"lat": 13.1200, "lng": 80.1600}, {"lat": 13.1100, "lng": 80.1650}]'::jsonb),
(8, 'Chennai',   'Perungudi',            1.10, '[{"lat": 12.9654, "lng": 80.2461}, {"lat": 12.9700, "lng": 80.2500}, {"lat": 12.9600, "lng": 80.2550}]'::jsonb),
-- Mumbai
(9, 'Mumbai',    'Fort',                 1.30, '[{"lat": 18.9322, "lng": 72.8315}, {"lat": 18.9400, "lng": 72.8350}, {"lat": 18.9250, "lng": 72.8400}]'::jsonb),
(10, 'Mumbai',   'Bandra West',          1.20, '[{"lat": 19.0596, "lng": 72.8295}, {"lat": 19.0650, "lng": 72.8350}, {"lat": 19.0500, "lng": 72.8400}]'::jsonb),
(11, 'Mumbai',   'Goregaon',             1.15, '[{"lat": 19.1646, "lng": 72.8493}, {"lat": 19.1700, "lng": 72.8550}, {"lat": 19.1600, "lng": 72.8600}]'::jsonb),
(12, 'Mumbai',   'Kurla',                1.35, '[{"lat": 19.0728, "lng": 72.8826}, {"lat": 19.0800, "lng": 72.8900}, {"lat": 19.0650, "lng": 72.8950}]'::jsonb),
-- Bangalore
(13, 'Bangalore', 'MG Road',             1.00, '[{"lat": 12.9716, "lng": 77.5946}, {"lat": 12.9800, "lng": 77.6000}, {"lat": 12.9650, "lng": 77.6050}]'::jsonb),
(14, 'Bangalore', 'Koramangala',         1.05, '[{"lat": 12.9279, "lng": 77.6271}, {"lat": 12.9350, "lng": 77.6350}, {"lat": 12.9200, "lng": 77.6400}]'::jsonb),
(15, 'Bangalore', 'Whitefield',          1.10, '[{"lat": 12.9698, "lng": 77.7499}, {"lat": 12.9800, "lng": 77.7600}, {"lat": 12.9600, "lng": 77.7650}]'::jsonb),
(16, 'Bangalore', 'Electronic City',     1.08, '[{"lat": 12.8452, "lng": 77.6602}, {"lat": 12.8550, "lng": 77.6700}, {"lat": 12.8350, "lng": 77.6750}]'::jsonb),
-- Delhi
(17, 'Delhi',     'Connaught Place',     1.25, '[{"lat": 28.6304, "lng": 77.2177}, {"lat": 28.6400, "lng": 77.2250}, {"lat": 28.6200, "lng": 77.2300}]'::jsonb),
(18, 'Delhi',     'Saket',               1.15, '[{"lat": 28.5246, "lng": 77.2066}, {"lat": 28.5350, "lng": 77.2150}, {"lat": 28.5150, "lng": 77.2200}]'::jsonb),
(19, 'Delhi',     'Badarpur',            1.40, '[{"lat": 28.4907, "lng": 77.3060}, {"lat": 28.5000, "lng": 77.3150}, {"lat": 28.4800, "lng": 77.3200}]'::jsonb),
(20, 'Delhi',     'Shahdara',            1.35, '[{"lat": 28.6946, "lng": 77.2917}, {"lat": 28.7050, "lng": 77.3000}, {"lat": 28.6850, "lng": 77.3050}]'::jsonb)
ON CONFLICT (zone_id) DO UPDATE SET
    risk_multiplier = EXCLUDED.risk_multiplier,
    area_name       = EXCLUDED.area_name,
    polygon         = EXCLUDED.polygon;

-- Restart sequence to zone 21
SELECT setval(pg_get_serial_sequence('zones', 'zone_id'), 21, false);

-- ============================================================
-- SAMPLE RIDERS (for testing; passwords/OTPs mocked)
-- ============================================================
-- These are inserted only if they don't exist
DO $$
DECLARE
    r1_id INTEGER;
    r2_id INTEGER;
    r3_id INTEGER;
BEGIN
    -- Rider 1: Kavach tier, Chennai, seasoning
    INSERT INTO riders (
        partner_id, platform, name, phone,
        aadhaar_last4, city,
        zone1_id, zone2_id, zone3_id,
        tier, baseline_weekly_income, baseline_weekly_hours,
        is_seasoning, trust_score, is_blocked, kyc_verified
    ) VALUES (
        'SWG-CHN-001', 'swiggy', 'Arjun Kumar', '+919876543210',
        '4521', 'Chennai',
        1, 2, 3,
        'kavach', NULL, NULL,
        TRUE, 50.00, FALSE, TRUE
    )
    ON CONFLICT (partner_id) DO NOTHING
    RETURNING id INTO r1_id;

    -- Rider 2: Suraksha tier, Mumbai, active baseline
    INSERT INTO riders (
        partner_id, platform, name, phone,
        pan, city,
        zone1_id, zone2_id, zone3_id,
        tier, baseline_weekly_income, baseline_weekly_hours,
        is_seasoning, trust_score, is_blocked, kyc_verified
    ) VALUES (
        'ZOM-MUM-042', 'zomato', 'Priya Sharma', '+919123456789',
        'ABCDE1234F', 'Mumbai',
        9, 10, NULL,
        'suraksha', 4200.00, 42.00,
        FALSE, 72.50, FALSE, TRUE
    )
    ON CONFLICT (partner_id) DO NOTHING
    RETURNING id INTO r2_id;

    -- Rider 3: Raksha tier, Bangalore
    INSERT INTO riders (
        partner_id, platform, name, phone,
        aadhaar_last4, city,
        zone1_id, zone2_id, zone3_id,
        tier, baseline_weekly_income, baseline_weekly_hours,
        is_seasoning, trust_score, is_blocked, kyc_verified
    ) VALUES (
        'ZOM-BLR-099', 'zomato', 'Ravi Naidu', '+918765432109',
        '9988', 'Bangalore',
        13, 14, 15,
        'raksha', 5500.00, 50.00,
        FALSE, 85.00, FALSE, TRUE
    )
    ON CONFLICT (partner_id) DO NOTHING
    RETURNING id INTO r3_id;

    -- Create active policies for riders that were just inserted
    IF r1_id IS NOT NULL THEN
        INSERT INTO policies (
            rider_id, tier, weekly_premium,
            premium_breakdown, weekly_payout_cap,
            coverage_type, status,
            cycle_start_date, cycle_end_date
        ) VALUES (
            r1_id, 'kavach', 15.00,
            '{"income": 0, "tier_rate": 0.015, "zone_risk": 1.20, "seasonal_factor": 1.0, "floor_applied": true, "cap_applied": false}'::jsonb,
            1500.00,
            'income_disruption', 'active',
            CURRENT_DATE, CURRENT_DATE + INTERVAL '28 days'
        );
    END IF;

    IF r2_id IS NOT NULL THEN
        INSERT INTO policies (
            rider_id, tier, weekly_premium,
            premium_breakdown, weekly_payout_cap,
            coverage_type, status,
            cycle_start_date, cycle_end_date
        ) VALUES (
            r2_id, 'suraksha', 88.20,
            '{"income": 4200, "tier_rate": 0.018, "zone_risk": 1.30, "seasonal_factor": 0.9, "floor_applied": false, "cap_applied": false}'::jsonb,
            3000.00,
            'income_disruption', 'active',
            CURRENT_DATE, CURRENT_DATE + INTERVAL '28 days'
        );
    END IF;

    IF r3_id IS NOT NULL THEN
        INSERT INTO policies (
            rider_id, tier, weekly_premium,
            premium_breakdown, weekly_payout_cap,
            coverage_type, status,
            cycle_start_date, cycle_end_date
        ) VALUES (
            r3_id, 'raksha', 192.50,
            '{"income": 5500, "tier_rate": 0.022, "zone_risk": 1.05, "seasonal_factor": 1.0, "floor_applied": false, "cap_applied": false}'::jsonb,
            5000.00,
            'income_disruption', 'active',
            CURRENT_DATE, CURRENT_DATE + INTERVAL '28 days'
        );
    END IF;
END $$;

-- ============================================================
-- DEMO: one pending claim for admin override (idempotent)
-- ============================================================
DO $$
DECLARE
  v_rider INTEGER;
  v_policy INTEGER;
  v_event INTEGER;
BEGIN
  SELECT id INTO v_rider FROM riders WHERE partner_id = 'SWG-CHN-001' LIMIT 1;
  IF v_rider IS NULL THEN
    RETURN;
  END IF;

  SELECT id INTO v_policy FROM policies
  WHERE rider_id = v_rider AND status = 'active'
  ORDER BY id DESC LIMIT 1;
  IF v_policy IS NULL THEN
    RETURN;
  END IF;

  IF EXISTS (
    SELECT 1 FROM claims
    WHERE rider_id = v_rider AND policy_id = v_policy AND status = 'pending'
  ) THEN
    RETURN;
  END IF;

  INSERT INTO disruption_events (
    event_type, severity, payout_rate, affected_zone, trigger_data, event_start, processing_status
  ) VALUES (
    'heavy_rain', 'moderate', 0.5000, 1, '{}'::jsonb, NOW(), 'processed'
  )
  RETURNING id INTO v_event;

  INSERT INTO claims (
    rider_id, policy_id, disruption_event_id,
    gate_results, is_eligible, status, calculated_payout, final_payout
  ) VALUES (
    v_rider, v_policy, v_event,
    '{}'::jsonb, TRUE, 'pending', 500.00, 500.00
  );
END $$;
