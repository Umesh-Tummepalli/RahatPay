import sys
import os
import datetime
from unittest.mock import patch
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'module3-triggers-claims')))
import shared_db as module3_db
from routes import trigger_routes as module3_routes

Base, Rider, Policy, Claim, Payout, DisruptionEvent, engine, SessionLocal = (
    module3_db.Base, module3_db.Rider, module3_db.Policy, module3_db.Claim, 
    module3_db.Payout, module3_db.DisruptionEvent, module3_db.engine, module3_db.SessionLocal
)
simulate_disruption = module3_routes.simulate_disruption
DisruptionSimulationRequest = module3_routes.DisruptionSimulationRequest

def setup_db():
    db = SessionLocal()
    db.query(Rider).delete()
    db.query(Policy).delete()
    db.query(Claim).delete()
    db.query(Payout).delete()
    db.commit()

    # Create Ravi
    ravi = Rider(
        id=1, name="Ravi",
        baseline_income=3500.0, baseline_hours=50.0, # Hourly = 70.0
        zone1_pincode="600017", zone2_pincode="600020", zone3_pincode="600032"
    )
    db.add(ravi)
    db.commit()

    # Create Policy
    policy = Policy(rider_id=1, tier="Suraksha", weekly_payout_cap=1925.0)
    db.add(policy)
    db.commit()
    return db

db = setup_db()

print("\n--- SCENARIO 1: IDEAL PAYOUT DURING SHIFT ---")
# Manually mock time to 1:00 PM (13:00) so it falls in 10-15 shift window
mock_time_1 = datetime.datetime.strptime("2023-08-01 13:00:00", "%Y-%m-%d %H:%M:%S")

with patch.object(module3_routes, 'datetime') as mock_dt:
    mock_dt.datetime.utcnow.return_value = mock_time_1
    req1 = DisruptionSimulationRequest(
        zone_pincode="600017", event_type="rainfall", severity="Severe L1", 
        duration_hours=3.0, raw_measurement=85.0
    )
    res1 = simulate_disruption(req1, db)
    print("Outcome:", res1["results"][0]["status"].upper())
    print("Gross Payout: ₹", res1["results"][0]["payout_math"]["gross_payout"])
    print("Final Payout: ₹", res1["results"][0]["payout_math"]["final_payout"])


print("\n--- SCENARIO 2: CLAIM REJECTED OUTSIDE HOURS ---")
# Mock time to 4:00 PM (16:00) -> falls exactly in the break between shifts!
mock_time_2 = datetime.datetime.strptime("2023-08-01 16:00:00", "%Y-%m-%d %H:%M:%S")

with patch.object(module3_routes, 'datetime') as mock_dt:
    mock_dt.datetime.utcnow.return_value = mock_time_2
    req2 = DisruptionSimulationRequest(
        zone_pincode="600017", event_type="rainfall", severity="Severe L1", 
        duration_hours=3.0, raw_measurement=85.0
    )
    res2 = simulate_disruption(req2, db)
    print("Outcome:", res2["results"][0]["status"].upper())
    print("Rejection Reason:", res2["results"][0]["rejection_reason"])


print("\n--- SCENARIO 3: HEADROOM CAP ACTIVATED ---")
# A massive flood hits causing an unprecedented 50-hour localized shutdown, 
# resulting in ₹2,100 gross payout. He should get capped at ₹1,925 minus ₹94.50 already paid!
mock_time_3 = datetime.datetime.strptime("2023-08-02 11:00:00", "%Y-%m-%d %H:%M:%S")

with patch.object(module3_routes, 'datetime') as mock_dt:
    mock_dt.datetime.utcnow.return_value = mock_time_3
    req3 = DisruptionSimulationRequest(
        zone_pincode="600017", event_type="rainfall", severity="Severe L2", 
        duration_hours=50.0, raw_measurement=150.0
    )
    res3 = simulate_disruption(req3, db)
    
    math_details = res3["results"][0]["payout_math"]
    print("Outcome:", res3["results"][0]["status"].upper())
    print("Total Gross Value: ₹", math_details["gross_payout"])
    print("Already Paid from Prior Events: ₹", math_details["already_paid"])
    print("Weekly Maximum Cap: ₹", math_details["weekly_cap"])
    print("CAPPED FINAL PAYOUT: ₹", math_details["final_payout"])
    
    # Prove the DB got the transaction ID!
    payout = db.query(Payout).filter(Payout.amount == math_details["final_payout"]).first()
    print("Mock Razorpay Ref Attached to DB:", payout.razorpay_ref_id)
