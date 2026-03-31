import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import or_

from shared_db import get_db, DisruptionEvent, Rider, Policy, Claim, Payout
from claims.eligibility import EligibilityGates
from claims.baseline_mock import get_rider_hourly_rate
from claims.calculator import calculate_payout
from claims.disbursement import initiate_payout

router = APIRouter()

class DisruptionSimulationRequest(BaseModel):
    zone_pincode: str
    event_type: str
    severity: str    # "Moderate", "Severe L1", "Severe L2"
    duration_hours: float
    raw_measurement: float

# Quick mapping for manual simulator
SEVERITY_RATES = {
    "Moderate": 0.30,
    "Severe L1": 0.45,
    "Severe L2": 0.60
}

@router.post("/simulate-disruption")
def simulate_disruption(req: DisruptionSimulationRequest, db: Session = Depends(get_db)):
    """
    Demo Button: Simulates a disruption, checks eligibility for affected riders, 
    calculates payouts, processes mock payments, and returns the entire orchestration result.
    """
    
    severity_rate = SEVERITY_RATES.get(req.severity)
    if severity_rate is None:
        raise HTTPException(status_code=400, detail="Invalid severity. Must be Moderate, Severe L1, or Severe L2.")
        
    start_time = datetime.datetime.utcnow()
    
    # 1. Store the disruption event
    event = DisruptionEvent(
        zone=req.zone_pincode,
        type=req.event_type,
        severity_level=req.severity,
        severity_payout_rate=severity_rate,
        api_source="manual_simulation",
        raw_measurement=req.raw_measurement,
        start_time=start_time,
        duration_hours=req.duration_hours,
        is_active=True
    )
    db.add(event)
    db.commit()
    db.refresh(event)

    # 2. Find affected riders who have this zone mapped
    affected_riders = db.query(Rider).filter(
        or_(
            Rider.zone1_pincode == req.zone_pincode,
            Rider.zone2_pincode == req.zone_pincode,
            Rider.zone3_pincode == req.zone_pincode
        )
    ).all()

    summary = {
        "event_id": event.id,
        "riders_affected": len(affected_riders),
        "claims_initiated": 0,
        "claims_rejected": 0,
        "total_payout_amount": 0.0,
        "results": []
    }

    # 3. For each affected rider process eligibility and claims
    for rider in affected_riders:
        rider_zones = [z for z in [rider.zone1_pincode, rider.zone2_pincode, rider.zone3_pincode] if z]
        
        # 4-Gate Validation
        is_eligible, gates, reason = EligibilityGates.run_all_gates(
            disruption_zone=req.zone_pincode,
            event_time=start_time,
            rider_zones=rider_zones
        )
        
        # Prepare DB Claim Record
        claim = Claim(
            rider_id=rider.id,
            disruption_event_id=event.id,
            gate1_zone_match=gates["gate1_zone_match"],
            gate2_shift_overlap=gates["gate2_shift_overlap"],
            gate3_platform_inactivity=gates["gate3_platform_inactivity"],
            gate4_sensor_fusion=gates["gate4_sensor_fusion"],
            rejection_reason=reason if not is_eligible else None,
            status="approved" if is_eligible else "rejected",
            disrupted_hours=req.duration_hours,
            severity_rate=severity_rate
        )
        
        individual_result = {
            "rider_id": rider.id,
            "rider_name": rider.name,
            "status": claim.status,
            "gates": gates,
            "rejection_reason": reason,
            "payout_math": None
        }

        if is_eligible:
            # Payout compute
            hourly_rate = get_rider_hourly_rate(rider)
            policy = db.query(Policy).filter(Policy.rider_id == rider.id).first()
            weekly_cap = policy.weekly_payout_cap if policy else 0.0
            
            # Sum up already paid this week. 
            # Production: Should filter by start of the week.
            past_claims = db.query(Claim).filter(
                Claim.rider_id == rider.id, Claim.status == "approved"
            ).all()
            already_paid = sum(c.final_payout for c in past_claims if c.final_payout)
            
            math = calculate_payout(
                hourly_rate=hourly_rate,
                disrupted_hours=req.duration_hours,
                severity_rate=severity_rate,
                weekly_cap=weekly_cap,
                already_paid=already_paid
            )
            
            # Save metrics to claim
            claim.hourly_rate = math["hourly_rate"]
            claim.disrupted_income = math["disrupted_income"]
            claim.gross_payout = math["gross_payout"]
            claim.weekly_cap = math["weekly_cap"]
            claim.already_paid = math["already_paid"]
            claim.final_payout = math["final_payout"]
            
            individual_result["payout_math"] = math
            summary["claims_initiated"] += 1
            summary["total_payout_amount"] += math["final_payout"]
            
        else:
            summary["claims_rejected"] += 1
            
        db.add(claim)
        db.commit()
        db.refresh(claim)
        
        # If eligible and payout > 0, do mock disbursement
        if is_eligible and claim.final_payout > 0:
            mock_res = initiate_payout(rider.id, claim.final_payout)
            pout = Payout(
                claim_id=claim.id,
                rider_id=rider.id,
                amount=claim.final_payout,
                payment_method="upi",
                razorpay_ref_id=mock_res.get("provider_ref"),
                status=mock_res.get("status")
            )
            db.add(pout)
            db.commit()
            
        summary["results"].append(individual_result)

    return summary

@router.post("/simulate-civic")
def simulate_civic(req: DisruptionSimulationRequest, db: Session = Depends(get_db)):
    """Admin wrapper for simulating civic disruption"""
    req.event_type = "civic"
    return simulate_disruption(req, db)

@router.post("/simulate-heat")
def simulate_heat(req: DisruptionSimulationRequest, db: Session = Depends(get_db)):
    """Admin wrapper for simulating heat disruption"""
    req.event_type = "heat"
    return simulate_disruption(req, db)
