from datetime import datetime, timezone

import pytest

from claims.eligibility import evaluate_eligibility


@pytest.mark.asyncio
async def test_gate2_uses_history_shift_windows():
    rider = {
        "id": 101,
        "zone1_id": 9,
        "zone2_id": None,
        "zone3_id": None,
        "daily_income_history": [
            {"date": "2026-04-15", "income": 0, "hours": 0, "shift_intervals": [{"start_hour": 9, "end_hour": 13}]},
            {"date": "2026-04-14", "income": 0, "hours": 0, "shift_intervals": [{"start_hour": 9, "end_hour": 13}]},
            {"date": "2026-04-13", "income": 0, "hours": 0, "shift_intervals": [{"start_hour": 9, "end_hour": 13}]},
        ],
    }
    event = {
        "affected_zone": 9,
        "event_start": datetime(2026, 4, 16, 10, 0, tzinfo=timezone.utc),
        "event_end": datetime(2026, 4, 16, 11, 0, tzinfo=timezone.utc),
    }

    result = await evaluate_eligibility(rider, event)
    assert result["gate2_shift_overlap"] is True
    assert result["gate_details"]["shift_window"]["source"] == "daily_income_history"
