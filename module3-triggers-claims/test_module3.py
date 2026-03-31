import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'module3-triggers-claims')))

import shared_db as module3_db
from routes import trigger_routes as module3_routes

Base, Rider, Policy, Claim, Payout, DisruptionEvent, engine, SessionLocal = (
    module3_db.Base, module3_db.Rider, module3_db.Policy, module3_db.Claim, 
    module3_db.Payout, module3_db.DisruptionEvent, module3_db.engine, module3_db.SessionLocal
)
simulate_disruption, DisruptionSimulationRequest = (
    module3_routes.simulate_disruption, module3_routes.DisruptionSimulationRequest
)

# Ravi profile
db = SessionLocal()

# Cleanup table
db.query(Rider).delete()
db.query(Policy).delete()
db.commit()

ravi = Rider(
    id=1,
    name="Ravi",
    baseline_income=3500.0,
    baseline_hours=50.0, # Hourly = 70.0
    zone1_pincode="600017",
    zone2_pincode="600020",
    zone3_pincode="600032"
)
db.add(ravi)
db.commit()

# Cap: Suraksha is 55% of 3500 = 1925
policy = Policy(
    rider_id=1,
    tier="Suraksha",
    weekly_payout_cap=1925.0
)
db.add(policy)
db.commit()


# Scenario A
# simulate severe rainfall in zone 600017, 3 hours. 85mm is Severe L1 (0.45 rate)
req = DisruptionSimulationRequest(
    zone_pincode="600017",
    event_type="rainfall",
    severity="Severe L1", 
    duration_hours=3.0,
    raw_measurement=85.0
)

res = simulate_disruption(req, db)
print("Scenario A Result:")
print("Affected:", res["riders_affected"])
print("Claims Initiated:", res["claims_initiated"])
if res["claims_initiated"] > 0:
    payout = res["results"][0]["payout_math"]["final_payout"]
    print("Final Payout:", payout)
    print("Expected: ~94.50")
    if payout == 94.5:
        print("PASS")
    else:
        print("FAIL")

