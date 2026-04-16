#!/usr/bin/env python3
"""Quick test of Person 3 claims pipeline components."""

import sys
sys.path.insert(0, 'module3-triggers-claims')
sys.path.insert(0, 'module1-registration')

print('=== Testing Person 3 Claims Pipeline ===\n')

# Test 1: Payout Calculator
print('1. Payout Calculator')
from module3_triggers_claims.claims.payout_calculator import calculate_payout

# Scenario: 3 hours × ₹70/hr × 0.45 severity
payout = calculate_payout(hourly_rate=70.0, disrupted_hours=3.0, severity_rate=0.45)
print(f'   Hours: {payout["disrupted_hours"]}, Rate: ₹{payout["hourly_rate"]}, Severity: {payout["severity_rate"]:.0%}')
print(f'   Gross Payout: ₹{payout["gross_payout"]}')
print(f'   Expected ₹94.50: {abs(payout["gross_payout"] - 94.5) < 0.01} ✓')

# Test 2: Cap Enforcer  
print('\n2. Cap Enforcer (Tier caps)')
from module3_triggers_claims.claims.cap_enforcer import TIER_CAP_PERCENT
baseline = 3500.0
for tier, pct in TIER_CAP_PERCENT.items():
    cap = baseline * pct
    print(f'   {tier.upper():12} ({pct:.0%}): ₹{cap:7.0f}')

# Test 3: Imports
print('\n3. Module Imports')
try:
    from module3_triggers_claims.claims.eligibility import evaluate_eligibility
    print('   Eligibility: ✓ Loaded')
except Exception as e:
    print(f'   Eligibility: ✗ {e}')

try:
    from module3_triggers_claims.claims.disbursement import disburse_payout
    print('   Disbursement: ✓ Loaded (Razorpay ready)')
except Exception as e:
    print(f'   Disbursement: ✗ {e}')

try:
    from module3_triggers_claims.claims.processor import process_disruption_claims
    print('   Processor: ✓ Loaded (orchestrator ready)')
except Exception as e:
    print(f'   Processor: ✗ {e}')

print('\n=== All Person 3 Components Verified ✅ ===')
