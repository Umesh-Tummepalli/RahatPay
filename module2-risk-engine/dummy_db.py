"""
dummy_db.py

Stands in for Module 1's PostgreSQL database until integration day.
On integration day, profiler.py swaps this import for real DB queries.
The structure here MUST match what Module 1 will actually store —
agree field names with Module 1 owner before finalising.

Riders:
  101 — Ravi       Chennai    Suraksha  established (6 weeks history)
  102 — Arjun      Pune       Kavach    seasoning   (1 week history)
  103 — Kiran      Mumbai     Raksha    established (5 weeks history)
  104 — Priya      Bangalore  Suraksha  established (4 weeks history)
  105 — Dev        Delhi      Kavach    established (4 weeks history)
"""

# ── Rider master records ─────────────────────────────────────────────────────
RIDERS = {
    101: {
        "rider_id": 101,
        "name": "Ravi",
        "city": "chennai",
        "tier": "suraksha",
        "partner_platform": "swiggy",
        "enrolled_weeks": 6,          # how many weeks since enrollment
        "seasoning_complete": True,   # True once >= 2 weeks of real data
    },
    102: {
        "rider_id": 102,
        "name": "Arjun",
        "city": "pune",
        "tier": "kavach",
        "partner_platform": "zomato",
        "enrolled_weeks": 1,
        "seasoning_complete": False,  # still in seasoning
    },
    103: {
        "rider_id": 103,
        "name": "Kiran",
        "city": "mumbai",
        "tier": "raksha",
        "partner_platform": "zomato",
        "enrolled_weeks": 5,
        "seasoning_complete": True,
    },
    104: {
        "rider_id": 104,
        "name": "Priya",
        "city": "bangalore",
        "tier": "suraksha",
        "partner_platform": "swiggy",
        "enrolled_weeks": 4,
        "seasoning_complete": True,
    },
    105: {
        "rider_id": 105,
        "name": "Dev",
        "city": "delhi",
        "tier": "kavach",
        "partner_platform": "zomato",
        "enrolled_weeks": 4,
        "seasoning_complete": True,
    },
}


# ── Weekly activity history ───────────────────────────────────────────────────
# Each record = one week of a rider's activity.
# week_number: 1 = most recent, 2 = one week ago, etc.
# zones_visited: list of pincodes, ordered by hours spent (most → least)
# earnings: ₹ earned that week
# hours_worked: active delivery hours

ACTIVITY_HISTORY = {
    # Ravi — Chennai, consistent full-time
    101: [
        {"week_number": 1, "earnings": 3600, "hours_worked": 51, "zones_visited": ["600017", "600020", "600032"]},
        {"week_number": 2, "earnings": 3400, "hours_worked": 48, "zones_visited": ["600017", "600032", "600020"]},
        {"week_number": 3, "earnings": 3550, "hours_worked": 50, "zones_visited": ["600020", "600017", "600028"]},
        {"week_number": 4, "earnings": 3450, "hours_worked": 49, "zones_visited": ["600017", "600020", "600032"]},
        {"week_number": 5, "earnings": 3500, "hours_worked": 50, "zones_visited": ["600032", "600017", "600020"]},
        {"week_number": 6, "earnings": 3300, "hours_worked": 47, "zones_visited": ["600017", "600028", "600020"]},
    ],
    # Arjun — Pune, only 1 week of data (seasoning)
    102: [
        {"week_number": 1, "earnings": 1350, "hours_worked": 19, "zones_visited": ["411038"]},
    ],
    # Kiran — Mumbai, high earner high-risk zone
    103: [
        {"week_number": 1, "earnings": 5200, "hours_worked": 60, "zones_visited": ["400017", "400069", "400050"]},
        {"week_number": 2, "earnings": 4900, "hours_worked": 57, "zones_visited": ["400017", "400050", "400069"]},
        {"week_number": 3, "earnings": 5100, "hours_worked": 59, "zones_visited": ["400069", "400017", "400050"]},
        {"week_number": 4, "earnings": 5000, "hours_worked": 58, "zones_visited": ["400017", "400069", "400050"]},
        {"week_number": 5, "earnings": 4800, "hours_worked": 56, "zones_visited": ["400050", "400017", "400069"]},
    ],
    # Priya — Bangalore, stable zone
    104: [
        {"week_number": 1, "earnings": 3200, "hours_worked": 47, "zones_visited": ["560034", "560011", "560095"]},
        {"week_number": 2, "earnings": 3100, "hours_worked": 46, "zones_visited": ["560034", "560095", "560011"]},
        {"week_number": 3, "earnings": 3300, "hours_worked": 48, "zones_visited": ["560011", "560034", "560095"]},
        {"week_number": 4, "earnings": 3050, "hours_worked": 45, "zones_visited": ["560034", "560011", "560095"]},
    ],
    # Dev — Delhi, moderate earner
    105: [
        {"week_number": 1, "earnings": 2900, "hours_worked": 46, "zones_visited": ["110001", "110019", "110045"]},
        {"week_number": 2, "earnings": 2750, "hours_worked": 44, "zones_visited": ["110001", "110045", "110019"]},
        {"week_number": 3, "earnings": 2850, "hours_worked": 45, "zones_visited": ["110019", "110001", "110045"]},
        {"week_number": 4, "earnings": 2800, "hours_worked": 44, "zones_visited": ["110001", "110019", "110045"]},
    ],
}


# ── Helper functions (mirrors what DB queries will do) ────────────────────────

def get_rider(rider_id: int) -> dict | None:
    return RIDERS.get(rider_id)


def get_activity_history(rider_id: int, last_n_weeks: int = 4) -> list:
    history = ACTIVITY_HISTORY.get(rider_id, [])
    return [w for w in history if w["week_number"] <= last_n_weeks]