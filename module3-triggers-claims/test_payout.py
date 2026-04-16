from claims.payout_calculator import calculate_disrupted_hours, calculate_payout


def test_payout_readme_scenario_a():
    result = calculate_payout(hourly_rate=70.0, disrupted_hours=3.0, severity_rate=0.45)
    assert result["gross_payout"] == 94.5


def test_disrupted_hours_respects_custom_windows():
    hours = calculate_disrupted_hours(
        event_start="2026-04-16T10:00:00+00:00",
        event_end="2026-04-16T14:00:00+00:00",
        shift_windows=[(11, 13)],
    )
    assert hours == 2.0
