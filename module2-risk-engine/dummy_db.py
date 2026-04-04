"""
dummy_db.py

Stands in for Module 1's PostgreSQL database until integration 
day.
On integration day, profiler.py swaps this import for real DB queries.

Daily activity covers last 15 days per rider.
Used by:
  - Module 2 profiler: aggregates daily data for baseline calculation
  - Module 3 claims engine: checks shift windows for eligibility gate 2
"""

from datetime import date, timedelta

_TODAY = date(2026, 3, 31)

def _day(days_ago: int) -> str:
    return (_TODAY - timedelta(days=days_ago - 1)).isoformat()


# ── Rider master records ──────────────────────────────────────────────────────
RIDERS = {
    101: {"rider_id": 101, "name": "Ravi",  "city": "chennai",   "tier": "suraksha", "partner_platform": "swiggy", "enrolled_weeks": 6, "seasoning_complete": True},
    102: {"rider_id": 102, "name": "Arjun", "city": "pune",      "tier": "kavach",   "partner_platform": "zomato", "enrolled_weeks": 1, "seasoning_complete": False},
    103: {"rider_id": 103, "name": "Kiran", "city": "mumbai",    "tier": "raksha",   "partner_platform": "zomato", "enrolled_weeks": 5, "seasoning_complete": True},
    104: {"rider_id": 104, "name": "Priya", "city": "bangalore", "tier": "suraksha", "partner_platform": "swiggy", "enrolled_weeks": 4, "seasoning_complete": True},
    105: {"rider_id": 105, "name": "Dev",   "city": "delhi",     "tier": "kavach",   "partner_platform": "zomato", "enrolled_weeks": 4, "seasoning_complete": True},
}


# ── Weekly activity history (used by profiler for rolling baseline) ───────────
ACTIVITY_HISTORY = {
    101: [
        {"week_number": 1, "earnings": 3600, "hours_worked": 51, "zones_visited": ["600017", "600020", "600032"]},
        {"week_number": 2, "earnings": 3400, "hours_worked": 48, "zones_visited": ["600017", "600032", "600020"]},
        {"week_number": 3, "earnings": 3550, "hours_worked": 50, "zones_visited": ["600020", "600017", "600028"]},
        {"week_number": 4, "earnings": 3450, "hours_worked": 49, "zones_visited": ["600017", "600020", "600032"]},
        {"week_number": 5, "earnings": 3500, "hours_worked": 50, "zones_visited": ["600032", "600017", "600020"]},
        {"week_number": 6, "earnings": 3300, "hours_worked": 47, "zones_visited": ["600017", "600028", "600020"]},
    ],
    102: [
        {"week_number": 1, "earnings": 1350, "hours_worked": 19, "zones_visited": ["411038"]},
    ],
    103: [
        {"week_number": 1, "earnings": 5200, "hours_worked": 60, "zones_visited": ["400017", "400069", "400050"]},
        {"week_number": 2, "earnings": 4900, "hours_worked": 57, "zones_visited": ["400017", "400050", "400069"]},
        {"week_number": 3, "earnings": 5100, "hours_worked": 59, "zones_visited": ["400069", "400017", "400050"]},
        {"week_number": 4, "earnings": 5000, "hours_worked": 58, "zones_visited": ["400017", "400069", "400050"]},
        {"week_number": 5, "earnings": 4800, "hours_worked": 56, "zones_visited": ["400050", "400017", "400069"]},
    ],
    104: [
        {"week_number": 1, "earnings": 3200, "hours_worked": 47, "zones_visited": ["560034", "560011", "560095"]},
        {"week_number": 2, "earnings": 3100, "hours_worked": 46, "zones_visited": ["560034", "560095", "560011"]},
        {"week_number": 3, "earnings": 3300, "hours_worked": 48, "zones_visited": ["560011", "560034", "560095"]},
        {"week_number": 4, "earnings": 3050, "hours_worked": 45, "zones_visited": ["560034", "560011", "560095"]},
    ],
    105: [
        {"week_number": 1, "earnings": 2900, "hours_worked": 46, "zones_visited": ["110001", "110019", "110045"]},
        {"week_number": 2, "earnings": 2750, "hours_worked": 44, "zones_visited": ["110001", "110045", "110019"]},
        {"week_number": 3, "earnings": 2850, "hours_worked": 45, "zones_visited": ["110019", "110001", "110045"]},
        {"week_number": 4, "earnings": 2800, "hours_worked": 44, "zones_visited": ["110001", "110019", "110045"]},
    ],
}


# ── Daily activity history (15 days per rider) ────────────────────────────────
# shift_start/shift_end: hour in 24hr format (10 = 10 AM, 22 = 10 PM)
# Module 3 uses this to check if a disruption fell within a rider's shift

DAILY_ACTIVITY = {
    # Ravi — Chennai, works 10AM-3PM and 6PM-10PM daily
    101: [
        {"date": _day(1),  "shift_start": 10, "shift_end": 22, "hours_worked": 7.5, "earnings": 530, "zones_visited": ["600017", "600020"], "was_active": True},
        {"date": _day(2),  "shift_start": 10, "shift_end": 22, "hours_worked": 7.0, "earnings": 490, "zones_visited": ["600017", "600032"], "was_active": True},
        {"date": _day(3),  "shift_start": 10, "shift_end": 22, "hours_worked": 7.5, "earnings": 525, "zones_visited": ["600020", "600017"], "was_active": True},
        {"date": _day(4),  "shift_start": 10, "shift_end": 22, "hours_worked": 7.0, "earnings": 490, "zones_visited": ["600017", "600020"], "was_active": True},
        {"date": _day(5),  "shift_start": 10, "shift_end": 22, "hours_worked": 7.5, "earnings": 510, "zones_visited": ["600032", "600017"], "was_active": True},
        {"date": _day(6),  "shift_start": 10, "shift_end": 22, "hours_worked": 7.0, "earnings": 480, "zones_visited": ["600017", "600028"], "was_active": True},
        {"date": _day(7),  "shift_start": 0,  "shift_end": 0,  "hours_worked": 0,   "earnings": 0,   "zones_visited": [],                   "was_active": False},
        {"date": _day(8),  "shift_start": 10, "shift_end": 22, "hours_worked": 7.5, "earnings": 520, "zones_visited": ["600017", "600020"], "was_active": True},
        {"date": _day(9),  "shift_start": 10, "shift_end": 22, "hours_worked": 7.0, "earnings": 495, "zones_visited": ["600020", "600032"], "was_active": True},
        {"date": _day(10), "shift_start": 10, "shift_end": 22, "hours_worked": 7.5, "earnings": 525, "zones_visited": ["600017", "600020"], "was_active": True},
        {"date": _day(11), "shift_start": 10, "shift_end": 22, "hours_worked": 7.0, "earnings": 490, "zones_visited": ["600032", "600017"], "was_active": True},
        {"date": _day(12), "shift_start": 10, "shift_end": 22, "hours_worked": 7.5, "earnings": 515, "zones_visited": ["600017", "600028"], "was_active": True},
        {"date": _day(13), "shift_start": 10, "shift_end": 22, "hours_worked": 7.0, "earnings": 480, "zones_visited": ["600017", "600020"], "was_active": True},
        {"date": _day(14), "shift_start": 0,  "shift_end": 0,  "hours_worked": 0,   "earnings": 0,   "zones_visited": [],                   "was_active": False},
        {"date": _day(15), "shift_start": 10, "shift_end": 22, "hours_worked": 7.5, "earnings": 525, "zones_visited": ["600017", "600020"], "was_active": True},
    ],
    # Arjun — Pune, part-time evenings only 6PM-10PM
    102: [
        {"date": _day(1),  "shift_start": 18, "shift_end": 22, "hours_worked": 3.0, "earnings": 200, "zones_visited": ["411038"], "was_active": True},
        {"date": _day(2),  "shift_start": 18, "shift_end": 22, "hours_worked": 2.5, "earnings": 170, "zones_visited": ["411038"], "was_active": True},
        {"date": _day(3),  "shift_start": 0,  "shift_end": 0,  "hours_worked": 0,   "earnings": 0,   "zones_visited": [],          "was_active": False},
        {"date": _day(4),  "shift_start": 18, "shift_end": 22, "hours_worked": 3.0, "earnings": 195, "zones_visited": ["411038"], "was_active": True},
        {"date": _day(5),  "shift_start": 18, "shift_end": 22, "hours_worked": 3.0, "earnings": 210, "zones_visited": ["411038"], "was_active": True},
        {"date": _day(6),  "shift_start": 0,  "shift_end": 0,  "hours_worked": 0,   "earnings": 0,   "zones_visited": [],          "was_active": False},
        {"date": _day(7),  "shift_start": 0,  "shift_end": 0,  "hours_worked": 0,   "earnings": 0,   "zones_visited": [],          "was_active": False},
        {"date": _day(8),  "shift_start": 18, "shift_end": 22, "hours_worked": 2.5, "earnings": 165, "zones_visited": ["411038"], "was_active": True},
        {"date": _day(9),  "shift_start": 18, "shift_end": 22, "hours_worked": 3.0, "earnings": 200, "zones_visited": ["411038"], "was_active": True},
        {"date": _day(10), "shift_start": 0,  "shift_end": 0,  "hours_worked": 0,   "earnings": 0,   "zones_visited": [],          "was_active": False},
        {"date": _day(11), "shift_start": 18, "shift_end": 22, "hours_worked": 3.0, "earnings": 205, "zones_visited": ["411038"], "was_active": True},
        {"date": _day(12), "shift_start": 18, "shift_end": 22, "hours_worked": 2.5, "earnings": 175, "zones_visited": ["411038"], "was_active": True},
        {"date": _day(13), "shift_start": 0,  "shift_end": 0,  "hours_worked": 0,   "earnings": 0,   "zones_visited": [],          "was_active": False},
        {"date": _day(14), "shift_start": 18, "shift_end": 22, "hours_worked": 3.0, "earnings": 195, "zones_visited": ["411038"], "was_active": True},
        {"date": _day(15), "shift_start": 18, "shift_end": 22, "hours_worked": 2.5, "earnings": 180, "zones_visited": ["411038"], "was_active": True},
    ],
    # Kiran — Mumbai, full-time 9AM-10PM
    103: [
        {"date": _day(1),  "shift_start": 9, "shift_end": 22, "hours_worked": 9.0, "earnings": 750, "zones_visited": ["400017", "400069"], "was_active": True},
        {"date": _day(2),  "shift_start": 9, "shift_end": 22, "hours_worked": 8.5, "earnings": 710, "zones_visited": ["400017", "400050"], "was_active": True},
        {"date": _day(3),  "shift_start": 9, "shift_end": 22, "hours_worked": 9.0, "earnings": 740, "zones_visited": ["400069", "400017"], "was_active": True},
        {"date": _day(4),  "shift_start": 9, "shift_end": 22, "hours_worked": 8.5, "earnings": 700, "zones_visited": ["400017", "400069"], "was_active": True},
        {"date": _day(5),  "shift_start": 9, "shift_end": 22, "hours_worked": 9.0, "earnings": 755, "zones_visited": ["400050", "400017"], "was_active": True},
        {"date": _day(6),  "shift_start": 0, "shift_end": 0,  "hours_worked": 0,   "earnings": 0,   "zones_visited": [],                   "was_active": False},
        {"date": _day(7),  "shift_start": 0, "shift_end": 0,  "hours_worked": 0,   "earnings": 0,   "zones_visited": [],                   "was_active": False},
        {"date": _day(8),  "shift_start": 9, "shift_end": 22, "hours_worked": 9.0, "earnings": 745, "zones_visited": ["400017", "400069"], "was_active": True},
        {"date": _day(9),  "shift_start": 9, "shift_end": 22, "hours_worked": 8.5, "earnings": 705, "zones_visited": ["400069", "400050"], "was_active": True},
        {"date": _day(10), "shift_start": 9, "shift_end": 22, "hours_worked": 9.0, "earnings": 750, "zones_visited": ["400017", "400069"], "was_active": True},
        {"date": _day(11), "shift_start": 9, "shift_end": 22, "hours_worked": 8.5, "earnings": 715, "zones_visited": ["400050", "400017"], "was_active": True},
        {"date": _day(12), "shift_start": 9, "shift_end": 22, "hours_worked": 9.0, "earnings": 740, "zones_visited": ["400017", "400069"], "was_active": True},
        {"date": _day(13), "shift_start": 0, "shift_end": 0,  "hours_worked": 0,   "earnings": 0,   "zones_visited": [],                   "was_active": False},
        {"date": _day(14), "shift_start": 9, "shift_end": 22, "hours_worked": 9.0, "earnings": 750, "zones_visited": ["400017", "400069"], "was_active": True},
        {"date": _day(15), "shift_start": 9, "shift_end": 22, "hours_worked": 8.5, "earnings": 710, "zones_visited": ["400069", "400017"], "was_active": True},
    ],
    # Priya — Bangalore, full-time 10AM-9PM
    104: [
        {"date": _day(1),  "shift_start": 10, "shift_end": 21, "hours_worked": 7.0, "earnings": 455, "zones_visited": ["560034", "560011"], "was_active": True},
        {"date": _day(2),  "shift_start": 10, "shift_end": 21, "hours_worked": 6.5, "earnings": 420, "zones_visited": ["560034", "560095"], "was_active": True},
        {"date": _day(3),  "shift_start": 10, "shift_end": 21, "hours_worked": 7.0, "earnings": 450, "zones_visited": ["560011", "560034"], "was_active": True},
        {"date": _day(4),  "shift_start": 10, "shift_end": 21, "hours_worked": 6.5, "earnings": 415, "zones_visited": ["560034", "560011"], "was_active": True},
        {"date": _day(5),  "shift_start": 10, "shift_end": 21, "hours_worked": 7.0, "earnings": 455, "zones_visited": ["560095", "560034"], "was_active": True},
        {"date": _day(6),  "shift_start": 0,  "shift_end": 0,  "hours_worked": 0,   "earnings": 0,   "zones_visited": [],                   "was_active": False},
        {"date": _day(7),  "shift_start": 0,  "shift_end": 0,  "hours_worked": 0,   "earnings": 0,   "zones_visited": [],                   "was_active": False},
        {"date": _day(8),  "shift_start": 10, "shift_end": 21, "hours_worked": 7.0, "earnings": 445, "zones_visited": ["560034", "560011"], "was_active": True},
        {"date": _day(9),  "shift_start": 10, "shift_end": 21, "hours_worked": 6.5, "earnings": 425, "zones_visited": ["560011", "560095"], "was_active": True},
        {"date": _day(10), "shift_start": 10, "shift_end": 21, "hours_worked": 7.0, "earnings": 460, "zones_visited": ["560034", "560011"], "was_active": True},
        {"date": _day(11), "shift_start": 10, "shift_end": 21, "hours_worked": 6.5, "earnings": 420, "zones_visited": ["560095", "560034"], "was_active": True},
        {"date": _day(12), "shift_start": 10, "shift_end": 21, "hours_worked": 7.0, "earnings": 450, "zones_visited": ["560034", "560011"], "was_active": True},
        {"date": _day(13), "shift_start": 0,  "shift_end": 0,  "hours_worked": 0,   "earnings": 0,   "zones_visited": [],                   "was_active": False},
        {"date": _day(14), "shift_start": 10, "shift_end": 21, "hours_worked": 7.0, "earnings": 455, "zones_visited": ["560034", "560095"], "was_active": True},
        {"date": _day(15), "shift_start": 10, "shift_end": 21, "hours_worked": 6.5, "earnings": 415, "zones_visited": ["560011", "560034"], "was_active": True},
    ],
    # Dev — Delhi, full-time 11AM-9PM
    105: [
        {"date": _day(1),  "shift_start": 11, "shift_end": 21, "hours_worked": 6.5, "earnings": 415, "zones_visited": ["110001", "110019"], "was_active": True},
        {"date": _day(2),  "shift_start": 11, "shift_end": 21, "hours_worked": 6.0, "earnings": 390, "zones_visited": ["110001", "110045"], "was_active": True},
        {"date": _day(3),  "shift_start": 11, "shift_end": 21, "hours_worked": 6.5, "earnings": 410, "zones_visited": ["110019", "110001"], "was_active": True},
        {"date": _day(4),  "shift_start": 11, "shift_end": 21, "hours_worked": 6.0, "earnings": 385, "zones_visited": ["110001", "110019"], "was_active": True},
        {"date": _day(5),  "shift_start": 11, "shift_end": 21, "hours_worked": 6.5, "earnings": 420, "zones_visited": ["110045", "110001"], "was_active": True},
        {"date": _day(6),  "shift_start": 0,  "shift_end": 0,  "hours_worked": 0,   "earnings": 0,   "zones_visited": [],                   "was_active": False},
        {"date": _day(7),  "shift_start": 0,  "shift_end": 0,  "hours_worked": 0,   "earnings": 0,   "zones_visited": [],                   "was_active": False},
        {"date": _day(8),  "shift_start": 11, "shift_end": 21, "hours_worked": 6.5, "earnings": 415, "zones_visited": ["110001", "110019"], "was_active": True},
        {"date": _day(9),  "shift_start": 11, "shift_end": 21, "hours_worked": 6.0, "earnings": 390, "zones_visited": ["110019", "110045"], "was_active": True},
        {"date": _day(10), "shift_start": 11, "shift_end": 21, "hours_worked": 6.5, "earnings": 405, "zones_visited": ["110001", "110019"], "was_active": True},
        {"date": _day(11), "shift_start": 11, "shift_end": 21, "hours_worked": 6.0, "earnings": 395, "zones_visited": ["110045", "110001"], "was_active": True},
        {"date": _day(12), "shift_start": 11, "shift_end": 21, "hours_worked": 6.5, "earnings": 415, "zones_visited": ["110001", "110019"], "was_active": True},
        {"date": _day(13), "shift_start": 0,  "shift_end": 0,  "hours_worked": 0,   "earnings": 0,   "zones_visited": [],                   "was_active": False},
        {"date": _day(14), "shift_start": 11, "shift_end": 21, "hours_worked": 6.5, "earnings": 410, "zones_visited": ["110001", "110045"], "was_active": True},
        {"date": _day(15), "shift_start": 11, "shift_end": 21, "hours_worked": 6.0, "earnings": 385, "zones_visited": ["110019", "110001"], "was_active": True},
    ],
}


# ── Helper functions ──────────────────────────────────────────────────────────

def get_rider(rider_id: int) -> dict | None:
    return RIDERS.get(rider_id)


def get_activity_history(rider_id: int, last_n_weeks: int = 4) -> list:
    """Weekly history — used by profiler for rolling baseline calculation."""
    history = ACTIVITY_HISTORY.get(rider_id, [])
    return [w for w in history if w["week_number"] <= last_n_weeks]


def get_daily_activity(rider_id: int, last_n_days: int = 15) -> list:
    """
    Daily history — used by Module 3 for shift window checking (gate 2).
    Returns last N days of activity, most recent first.
    """
    history = DAILY_ACTIVITY.get(rider_id, [])
    return history[:last_n_days]


def get_rider_shift_window(rider_id: int) -> dict:
    """
    Derives a rider's typical shift window from their last 15 days.
    Module 3 calls this for eligibility gate 2 (shift overlap check).

    Returns:
        {
            "shift_start": 10,
            "shift_end":   22,
            "active_days": 13,
            "source":      "daily_history_15days"
        }
    """
    daily = get_daily_activity(rider_id, last_n_days=15)
    active_days = [d for d in daily if d["was_active"]]

    if not active_days:
        return {"shift_start": 10, "shift_end": 22, "active_days": 0, "source": "default_fallback"}

    return {
        "shift_start": min(d["shift_start"] for d in active_days),
        "shift_end":   max(d["shift_end"]   for d in active_days),
        "active_days": len(active_days),
        "source":      "daily_history_15days",
    }