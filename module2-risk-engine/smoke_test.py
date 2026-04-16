import os
import sys

# Ensure we can import from main
sys.path.append(os.path.dirname(__file__))

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

print("--- Testing /evaluate/baseline (Module 1 bridge) ---")
resp = client.post("/evaluate/baseline", json={"rider_id": "1001", "city": "chennai"})
print(f"Status: {resp.status_code}")
if resp.status_code == 200:
    print(resp.json())
else:
    print(resp.text)

print("\n--- Testing /evaluate/premium (Module 1 bridge) ---")
resp = client.post("/evaluate/premium", json={
    "income": 3500,
    "tier": "suraksha",
    "zones": ["400017"],  # Dharavi - should be expensive
    "city": "mumbai",
    "month": 7            # Monsoon
})
print(f"Status: {resp.status_code}")
if resp.status_code == 200:
    print(resp.json())
else:
    print(resp.text)

print("\n--- Testing /api/fraud/score-spoof ---")
resp = client.post("/api/fraud/score-spoof", json={
    "rider_id": 1001,
    "gps_accuracy_m": 0.5, # Impossible accuracy -> anomaly
    "device_id": "test_dev_1",
    "concurrent_device_ids": ["test_dev_1", "test_dev_2"], # Clash -> anomaly
    "recent_coordinates": [
        [19.0760, 72.8777, 1690000000.0],
        [19.0760, 72.8777, 1690000010.0], # Static coordinates
        [19.0760, 72.8777, 1690000020.0]
    ]
})
print(f"Status: {resp.status_code}")
if resp.status_code == 200:
    print(resp.json())
else:
    print(resp.text)
