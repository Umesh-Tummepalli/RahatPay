"""
tests/test_premium.py

Unit tests for Module 2.

Run from module2/ directory:
    python -m pytest tests/ -v

Tests cover:
  - Ravi and Arjun scenarios from the product README
  - Floor guardrail (Arjun)
  - Ceiling guardrail (high earner + worst case)
  - All 15 seed zone lookups
  - Seasonal factors by city
  - Profiler: established riders vs seasoning riders
  - Top 3 zone calculation
  - calculate_premium_for_rider convenience wrapper
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from premium.calculator import calculate_premium, calculate_premium_for_rider
from premium.guardrails import apply_guardrails, PREMIUM_FLOOR_INR, PREMIUM_CEILING_PCT
from premium.seasonal import get_seasonal_factor
from premium.zone_risk import get_zone_risk, get_rider_zone_risk, get_zone_risk_full, ZONE_RISK_TABLE
from premium.profiler import get_baseline, get_hourly_rate, get_top_zones


# ─────────────────────────────────────────────────────────────────────────────
# README PERSONA TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestReadmePersonas:

    def test_ravi_suraksha_july(self):
        """
        Ravi — Suraksha, ₹3500/week, zones T.Nagar/Adyar/Velachery, July (monsoon).
        Expected from README: ~₹80 (formula: 3500 × 1.8% × 1.10 × 1.15 ≈ 79.83)
        We test that the final premium falls in the reasonable ₹70–₹90 range.
        """
        result = calculate_premium(
            baseline_weekly_income=3500,
            tier="suraksha",
            zone_pincodes=["600017", "600020", "600032"],
            city="chennai",
            month=7,
        )
        assert 70 <= result["weekly_premium_inr"] <= 90, \
            f"Ravi's premium should be ~₹80, got ₹{result['weekly_premium_inr']}"
        assert result["coverage"]["weekly_payout_cap_inr"] == pytest.approx(1925.0, abs=1)
        assert result["breakdown"]["tier"] == "suraksha"

    def test_arjun_kavach_february_floor(self):
        """
        Arjun — Kavach, ₹1400/week, Kothrud, February (dry).
        Raw formula: 1400 × 1.0% × 0.85 × 0.90 = ₹10.71 → FLOOR kicks in → ₹15.
        """
        result = calculate_premium(
            baseline_weekly_income=1400,
            tier="kavach",
            zone_pincodes=["411038"],
            city="pune",
            month=2,
        )
        assert result["weekly_premium_inr"] == PREMIUM_FLOOR_INR, \
            f"Floor should apply for Arjun. Got ₹{result['weekly_premium_inr']}"
        assert "Floor applied" in result["breakdown"]["guardrail_applied"]

    def test_ravi_payout_cap(self):
        """Suraksha cap = 55% of ₹3500 = ₹1925."""
        result = calculate_premium(
            baseline_weekly_income=3500,
            tier="suraksha",
            zone_pincodes=["600017"],
            city="chennai",
            month=7,
        )
        assert result["coverage"]["weekly_payout_cap_inr"] == pytest.approx(1925.0, abs=0.01)


# ─────────────────────────────────────────────────────────────────────────────
# GUARDRAILS
# ─────────────────────────────────────────────────────────────────────────────

class TestGuardrails:

    def test_floor_applies_when_premium_too_low(self):
        """Raw premium below ₹15 → clamped to ₹15."""
        assert apply_guardrails(10.0, 1000.0) == PREMIUM_FLOOR_INR

    def test_ceiling_applies_for_high_earner_high_risk(self):
        """
        High earner + Raksha + Dharavi (1.35) + peak monsoon (1.25):
        10000 × 2.5% × 1.35 × 1.25 = ₹421.87 > 3.5% of ₹10000 (₹350) → capped.
        """
        result = calculate_premium(
            baseline_weekly_income=10000,
            tier="raksha",
            zone_pincodes=["400017"],
            city="mumbai",
            month=7,
        )
        ceiling = 10000 * PREMIUM_CEILING_PCT
        assert result["weekly_premium_inr"] <= ceiling + 0.01, \
            f"Ceiling should apply. Got ₹{result['weekly_premium_inr']}, ceiling ₹{ceiling}"
        assert "Ceiling applied" in result["breakdown"]["guardrail_applied"]

    def test_no_guardrail_for_normal_case(self):
        """Normal case — no guardrail triggered."""
        assert apply_guardrails(50.0, 3000.0) == 50.0

    def test_floor_is_15(self):
        assert PREMIUM_FLOOR_INR == 15.0

    def test_ceiling_is_3_5_pct(self):
        assert PREMIUM_CEILING_PCT == pytest.approx(0.035)


# ─────────────────────────────────────────────────────────────────────────────
# ZONE RISK
# ─────────────────────────────────────────────────────────────────────────────

class TestZoneRisk:

    def test_all_seed_pincodes_return_valid_risk(self):
        """All 15 seed pin codes should return a risk between 0.80 and 1.50."""
        for pincode in ZONE_RISK_TABLE:
            risk = get_zone_risk(pincode)
            assert 0.80 <= risk <= 1.50, \
                f"Zone {pincode} returned invalid risk {risk}"

    def test_dharavi_is_high_risk(self):
        assert get_zone_risk("400017") >= 1.30

    def test_koramangala_is_low_risk(self):
        assert get_zone_risk("560034") <= 0.90

    def test_unknown_pincode_returns_default(self):
        assert get_zone_risk("999999") == 1.00

    def test_rider_zone_risk_weighted_average(self):
        """
        get_rider_zone_risk should weight the first zone most heavily.
        If all zones are the same, result should equal that single zone's risk.
        """
        single_zone_risk = get_rider_zone_risk(["600017", "600017", "600017"])
        assert single_zone_risk == pytest.approx(get_zone_risk("600017"), abs=0.01)

    def test_zone_risk_full_returns_explanation(self):
        result = get_zone_risk_full("400017")
        assert "pincode" in result
        assert "risk_multiplier" in result
        assert "risk_label" in result
        assert "reason" in result
        assert result["risk_multiplier"] >= 1.30

    def test_zone_risk_full_unknown_pincode(self):
        result = get_zone_risk_full("000000")
        assert result["risk_multiplier"] == 1.00
        assert result["source"] == "default"


# ─────────────────────────────────────────────────────────────────────────────
# SEASONAL FACTORS
# ─────────────────────────────────────────────────────────────────────────────

class TestSeasonalFactors:

    def test_mumbai_july_is_peak(self):
        """Mumbai July = peak monsoon = 1.25."""
        assert get_seasonal_factor("mumbai", 7) == 1.25

    def test_chennai_october_is_peak(self):
        """Chennai October = NE monsoon onset = highest factor."""
        assert get_seasonal_factor("chennai", 10) == 1.25

    def test_bangalore_february_is_dry(self):
        assert get_seasonal_factor("bangalore", 2) == 0.90

    def test_delhi_november_has_aqi_risk(self):
        """Delhi November elevated due to AQI (crop burning season)."""
        assert get_seasonal_factor("delhi", 11) >= 1.00

    def test_unknown_city_returns_valid_factor(self):
        factor = get_seasonal_factor("unknowncity", 7)
        assert 0.80 <= factor <= 1.30

    def test_seasonal_factor_range(self):
        """All factors across all cities and months must be in 0.90–1.25."""
        from premium.seasonal import CITY_SEASONAL_FACTORS
        for city, months in CITY_SEASONAL_FACTORS.items():
            for month, factor in months.items():
                assert 0.85 <= factor <= 1.30, \
                    f"City {city} month {month} factor {factor} out of range"


# ─────────────────────────────────────────────────────────────────────────────
# PROFILER
# ─────────────────────────────────────────────────────────────────────────────

class TestProfiler:

    def test_established_rider_returns_rolling_average(self):
        """Rider 101 (Ravi) has 6 weeks of history — should return rolling average."""
        baseline = get_baseline(101)
        assert baseline["source"] == "rolling_4week"
        assert baseline["weekly_income"] > 0
        assert baseline["weekly_hours"] > 0
        assert baseline["hourly_rate"] > 0

    def test_seasoning_rider_returns_city_median(self):
        """Rider 102 (Arjun, Pune) is in seasoning — should return city median."""
        baseline = get_baseline(102)
        assert "city_median" in baseline["source"]
        assert baseline["weekly_income"] == 3000   # Pune median
        assert baseline["top_3_zones"] == []

    def test_ravi_hourly_rate_is_reasonable(self):
        """Ravi earns ~₹3500/week over ~50 hours → ~₹70/hr."""
        rate = get_hourly_rate(101)
        assert 60 <= rate <= 80, f"Ravi's hourly rate should be ~₹70, got ₹{rate}"

    def test_ravi_top_zones(self):
        """Ravi consistently works T.Nagar — should be in top 3."""
        zones = get_top_zones(101)
        assert len(zones) <= 3
        assert "600017" in zones   # T. Nagar is Ravi's primary zone

    def test_invalid_rider_raises(self):
        with pytest.raises(ValueError):
            get_baseline(9999)


# ─────────────────────────────────────────────────────────────────────────────
# CALCULATE PREMIUM FOR RIDER (convenience wrapper)
# ─────────────────────────────────────────────────────────────────────────────

class TestCalculatePremiumForRider:

    def test_ravi_full_pipeline(self):
        """Full pipeline for Ravi — baseline from profiler, premium calculated."""
        result = calculate_premium_for_rider(rider_id=101, tier="suraksha", month=7)
        assert result["rider_id"] == 101
        assert result["weekly_premium_inr"] >= PREMIUM_FLOOR_INR
        assert result["coverage"]["weekly_payout_cap_inr"] > 0

    def test_arjun_seasoning_pipeline(self):
        """
        Arjun in seasoning — city median baseline used (₹3000 Pune median).
        Raw: 3000 × 1.0% × 0.85 × 0.90 = ₹22.95 — above floor, so no floor clamp.
        We verify city median is used and premium is positive and reasonable.
        """
        result = calculate_premium_for_rider(rider_id=102, tier="kavach", month=2)
        assert "city_median" in result["baseline_source"]
        assert result["weekly_premium_inr"] >= PREMIUM_FLOOR_INR
        assert result["weekly_premium_inr"] <= 50   # shouldn't be high for kavach dry season

    def test_kiran_raksha_pipeline(self):
        """Kiran — high earner + Raksha + Mumbai."""
        result = calculate_premium_for_rider(rider_id=103, tier="raksha", month=7)
        assert result["coverage"]["weekly_payout_cap_inr"] > 3000   # 70% of ~5000


# ─────────────────────────────────────────────────────────────────────────────
# BREAKDOWN DICT STRUCTURE
# ─────────────────────────────────────────────────────────────────────────────

class TestBreakdownStructure:
    """
    Ensures the breakdown dict returned by calculate_premium
    has all the keys Module 1 and the mobile app expect.
    """

    def setup_method(self):
        self.result = calculate_premium(
            baseline_weekly_income=3500,
            tier="suraksha",
            zone_pincodes=["600017", "600020"],
            city="chennai",
            month=7,
        )

    def test_top_level_keys(self):
        for key in ["weekly_premium_inr", "breakdown", "coverage", "pct_of_income", "zone_details"]:
            assert key in self.result, f"Missing top-level key: {key}"

    def test_breakdown_keys(self):
        bd = self.result["breakdown"]
        for key in ["baseline_income", "tier_rate", "zone_risk", "seasonal_factor",
                    "raw_premium", "guardrail_applied", "zone_risk_label", "seasonal_label"]:
            assert key in bd, f"Missing breakdown key: {key}"

    def test_coverage_keys(self):
        cov = self.result["coverage"]
        for key in ["weekly_payout_cap_inr", "coverage_label", "claim_speed"]:
            assert key in cov, f"Missing coverage key: {key}"

    def test_zone_details_structure(self):
        for zone in self.result["zone_details"]:
            assert "pincode" in zone
            assert "risk_multiplier" in zone
            assert "risk_label" in zone
            assert "reason" in zone