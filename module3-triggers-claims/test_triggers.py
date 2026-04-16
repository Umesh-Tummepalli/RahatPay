from weather import classify_severity


def test_classify_severity_rainfall_thresholds():
    assert classify_severity("rainfall_mm_6hr", 80) == ("severe_l1", 0.45)
    assert classify_severity("rainfall_mm_6hr", 10) == (None, None)


def test_classify_severity_aqi_thresholds():
    assert classify_severity("aqi", 310) == ("severe_l1", 0.45)
    assert classify_severity("aqi", 250) == ("moderate", 0.30)
