-- ============================================================
-- RahatPay — Module 1: Seed Disruption Events
-- Use this to populate sample disaster events for testing
-- ============================================================

-- Insert sample disruption events for testing
-- These events will trigger automatic claims for riders in affected zones

INSERT INTO disruption_events (
    event_type, 
    severity, 
    payout_rate, 
    affected_zone, 
    trigger_data, 
    event_start, 
    event_end,
    processing_status
) VALUES 
-- Recent flood event in Mumbai Fort (Zone 9)
(
    'flood',
    'severe_l1',
    0.85,
    9,
    '{"source": "IMD", "alert_id": "IMD-FL-2026-001", "rainfall_mm": 150}',
    NOW() - INTERVAL '2 hours',
    NOW() + INTERVAL '6 hours',
    'processed'
),
-- Heavy rain in Mumbai Bandra (Zone 10)
(
    'heavy_rain',
    'moderate',
    0.60,
    10,
    '{"source": "IMD", "alert_id": "IMD-RN-2026-042", "rainfall_mm": 80}',
    NOW() - INTERVAL '1 hour',
    NOW() + INTERVAL '4 hours',
    'processed'
),
-- Cyclone alert for Chennai (Zones 1-3)
(
    'cyclone',
    'severe_l2',
    0.90,
    1,
    '{"source": "IMD", "alert_id": "IMD-CY-2026-003", "wind_speed_kmh": 85}',
    NOW() - INTERVAL '30 minutes',
    NOW() + INTERVAL '12 hours',
    'processed'
),
-- Extreme heat in Delhi Badarpur (Zone 19)
(
    'extreme_heat',
    'severe_l1',
    0.70,
    19,
    '{"source": "IMD", "alert_id": "IMD-HT-2026-015", "max_temp_celsius": 46}',
    NOW() - INTERVAL '3 hours',
    NOW() + INTERVAL '5 hours',
    'processed'
),
-- Civic disruption in Bangalore (Zone 13)
(
    'civic_disruption',
    'moderate',
    0.50,
    13,
    '{"source": "City Corp", "alert_id": "BLR-STRIKE-001", "reason": "Transport strike"}',
    NOW() - INTERVAL '4 hours',
    NOW() + INTERVAL '8 hours',
    'processed'
)
ON CONFLICT DO NOTHING;

-- Show inserted events
SELECT 
    id,
    event_type,
    severity,
    payout_rate,
    affected_zone,
    event_start,
    event_end,
    processing_status
FROM disruption_events
ORDER BY event_start DESC
LIMIT 10;
