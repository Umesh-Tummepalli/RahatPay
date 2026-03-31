import uuid
import logging

logger = logging.getLogger(__name__)

def initiate_payout(rider_id: int, amount: float, method: str = "upi") -> dict:
    """
    Mocks a Razorpay test-mode API call to disburse funds to the rider.
    For the Phase 2 demo fallback, it generates a UUID and assumes a successful "completed" state.
    
    If you add the Razorpay SDK later, this takes the form of:
    razorpay_client.payout.create({
        "account_number": "...",
        "fund_account_id": "fa_...",
        "amount": int(amount * 100),
        "currency": "INR",
        "mode": "UPI",
        "purpose": "payout"
    })
    """
    if amount <= 0:
        return {
            "status": "failed",
            "provider_ref": None,
            "error": "Payout amount must be greater than 0"
        }
        
    mock_ref = f"pout_{uuid.uuid4().hex[:14]}"
    
    # In a real environment, you'd log this properly.
    print(f"[RAZORPAY MOCK] Payout of ₹{amount} initiated for Rider ID: {rider_id}")
    print(f"[RAZORPAY MOCK] Reference ID: {mock_ref}")
    
    return {
        "status": "completed",
        "provider_ref": mock_ref,
        "error": None
    }
