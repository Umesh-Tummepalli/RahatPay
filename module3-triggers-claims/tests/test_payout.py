from claims.payout_calculator import calculate_disrupted_hours, calculate_payout


def test_calculate_disrupted_hours_uses_shift_overlap():
    disrupted_hours = calculate_disrupted_hours(
        event_start="2026-04-16T11:00:00+00:00",
        event_end="2026-04-16T13:00:00+00:00",
        shift_windows=[(10, 15)],
    )

    assert disrupted_hours == 2.0


def test_calculate_payout_returns_expected_breakdown():
    result = calculate_payout(hourly_rate=80.0, disrupted_hours=2.0, severity_rate=0.45)

    assert result["disrupted_income"] == 160.0
    assert result["gross_payout"] == 72.0
