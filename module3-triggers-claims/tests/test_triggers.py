from triggers.severity import classify_severity


def test_rainfall_thresholds_match_phase3_contract():
    assert classify_severity("rainfall_mm_6hr", 20) == (None, None)
    assert classify_severity("rainfall_mm_6hr", 35) == ("moderate", 0.30)
    assert classify_severity("rainfall_mm_6hr", 70) == ("severe_l1", 0.45)
    assert classify_severity("rainfall_mm_6hr", 120) == ("severe_l2", 0.60)
    assert classify_severity("rainfall_mm_6hr", 180) == ("extreme", 0.75)


def test_temperature_and_aqi_thresholds_match_phase3_contract():
    assert classify_severity("temperature_c", 41.9) == (None, None)
    assert classify_severity("temperature_c", 43) == ("moderate", 0.30)
    assert classify_severity("aqi", 250) == ("moderate", 0.30)
    assert classify_severity("aqi", 350) == ("severe_l1", 0.45)
