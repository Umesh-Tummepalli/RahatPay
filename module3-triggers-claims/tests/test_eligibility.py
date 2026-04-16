from datetime import datetime, timezone

import pytest

from claims.eligibility import evaluate_eligibility


def _rider_payload():
    return {
        "id": 101,
        "zone1_id": 9,
        "zone2_id": None,
        "zone3_id": None,
        "daily_income_history": [
            {
                "date": "2026-04-13",
                "income": 1200,
                "hours": 4,
                "orders": 8,
                "shift_intervals": [{"start_hour": 10, "end_hour": 14}],
            },
            {
                "date": "2026-04-14",
                "income": 1100,
                "hours": 4,
                "orders": 7,
                "shift_intervals": [{"start_hour": 10, "end_hour": 14}],
            },
            {
                "date": "2026-04-15",
                "income": 1150,
                "hours": 4,
                "orders": 7,
                "shift_intervals": [{"start_hour": 10, "end_hour": 14}],
            },
        ],
    }


@pytest.mark.asyncio
async def test_eligibility_uses_inferred_shift_windows():
    event = {
        "affected_zone": 9,
        "event_start": datetime(2026, 4, 16, 11, 0, tzinfo=timezone.utc),
        "event_end": datetime(2026, 4, 16, 12, 0, tzinfo=timezone.utc),
    }

    result = await evaluate_eligibility(_rider_payload(), event)

    assert result["gate2_shift_overlap"] is True
    assert result["all_gates_passed"] is True
    assert result["gate_details"]["shift_window"]["source"] == "daily_income_history"


@pytest.mark.asyncio
async def test_eligibility_rejects_events_outside_inferred_shift_windows():
    event = {
        "affected_zone": 9,
        "event_start": datetime(2026, 4, 16, 20, 0, tzinfo=timezone.utc),
        "event_end": datetime(2026, 4, 16, 21, 0, tzinfo=timezone.utc),
    }

    result = await evaluate_eligibility(_rider_payload(), event)

    assert result["gate2_shift_overlap"] is False
    assert result["all_gates_passed"] is False
