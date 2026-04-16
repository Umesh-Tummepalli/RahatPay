# RahatPay Phase 3 — E2E Demo Flow

> **Module 5 Integration** | Person 5 — Person 4 integration checkpoint
> Run `python health_check.py --retries 2` before starting any E2E flow.

---

## Port Reference (Authoritative)

| Module | Port | Role |
|--------|------|------|
| Module 1 — Registration & Admin | **:8000** | Core API, admin routes |
| Module 2 — Risk Engine & ML     | **:8002** | Premiums, seasonal, ML model |
| Module 3 — Triggers & Claims   | **:8003** | Triggers, claims, fraud |
| Admin Dashboard (Vite dev)      | **:5000** | React SPA |

> [!NOTE]
> The `/m3/` prefix in frontend API calls is a **Vite proxy convention only**.
> Vite strips `/m3` and forwards to `:8003`. Direct curl/health_check.py calls hit `:8003` without the `/m3` prefix.

---

## Prerequisites

Ensure all three backend modules are running:

```powershell
# Terminal 1 — Module 1 (port 8000)
cd module1-registration
uvicorn main:app --port 8000 --reload

# Terminal 2 — Module 2 (port 8002)
cd module2-risk-engine
uvicorn main:app --port 8002 --reload

# Terminal 3 — Module 3 (port 8003)
cd module3-triggers-claims
uvicorn main:app --port 8003 --reload

# Terminal 4 — Admin Dashboard (port 5000)
cd "Admin Dashboard Ui"
npm run dev
```

---

## Step D1 — Health Check

```powershell
python module5-integration/health_check.py --retries 2
```

Expected output: all 3 modules `ONLINE`, all critical endpoints `OK`.

---

## Step D2 — Seed Demo Data

Via Admin Dashboard UI or curl:

```bash
curl -X POST http://localhost:8000/admin/seed-demo \
  -H "Authorization: Bearer admin_token" \
  -H "Content-Type: application/json"
```

Expected: 8 riders created, policies assigned, baselines seeded.

---

## Step D3 — Verify Polling Feed

Open Admin Dashboard → Dashboard page.
The **Live Autonomous Trigger Feed** card should:
- Show auto-scrolling entries every 10 seconds
- Display GREEN (no breach) and RED (breach) entries
- Show `Live feed — polling every 10s` banner if Module 3 is online
- Fall back to mock entries with `Live trigger API unavailable` banner if Module 3 is offline

```bash
# Verify directly
curl http://localhost:8003/api/triggers/polling-log \
  -H "Authorization: Bearer admin_token"
```

---

## Step D4 — Trigger a Disruption Event

Via Dashboard → Simulate Seasonal/Disaster Event panel:

```bash
curl -X POST http://localhost:8003/admin/simulate-disaster \
  -H "Authorization: Bearer admin_token" \
  -H "Content-Type: application/json" \
  -d '{"event_type": "heavy_rain", "severity": "severe_l1", "affected_zone": 9, "lost_hours": 5, "severity_rate": 0.60}'
```

Expected: event created, claims generated for riders in Zone 9.

---

## Step D5 — Check Claims

```bash
curl http://localhost:8003/admin/claims/live \
  -H "Authorization: Bearer admin_token"
```

Expected: claims in `pending` or `in_review` status.

---

## Step D6 — Check Fraud Panel

Navigate to **Fraud** page:
- ML banner shows: `Isolation Forest | Trained on N samples | Accuracy X%`
- Claims table shows in-review claims with spoof scores and density ratios

---

## Step D7 — Approve a Claim

> **Note on routing**: Frontend calls `/m3/admin/claims/{id}/override` (Vite proxy strips `/m3`, hits `:8003`.
> Direct curl calls target `:8003` directly:

```bash
curl -X PATCH http://localhost:8003/admin/claims/1/override \
  -H "Authorization: Bearer admin_token" \
  -H "Content-Type: application/json" \
  -d '{"action": "approve"}'
```

Expected: claim removed from fraud review table (optimistic update).

---

## Step D8 — Run BCR Stress Test

Navigate to **BCR Stress Test** page → click **Run Stress Test**

Or via curl:

```bash
curl -X POST http://localhost:8000/admin/stress-test \
  -H "Authorization: Bearer admin_token" \
  -H "Content-Type: application/json" \
  -d '{"sim_days": 14, "severity": 0.75}'
```

Expected response shape:
```json
{
  "summary": {
    "total_bcr": 0.6532,
    "status": "SUSTAINABLE",
    "sim_days": 14,
    "severity": 0.75,
    "zones_simulated": 20
  },
  "zones": [...]
}
```

**Target: BCR < 0.70 (SUSTAINABLE)**

---

## Step D9 — Verify Dashboard Metrics

Check the **Actuarial Overview** page:
- Weekly Loss Ratio LineChart shows trend
- Stacked BarChart shows premiums vs payouts per tier
- BCR status banner shows green `SUSTAINABLE`

---

## Step D10 — Predictive Analytics

Navigate to **Predictive Analytics** page:
- Zones sorted by risk probability (highest first)
- Zones with recent events show amber `[Recent event]` tag
- Seasonal factor shown for current month

---

## Failure Handling Matrix

| Scenario | Expected Behaviour |
|----------|-------------------|
| Module 1 offline | All `/admin/*` calls fail → dashboard shows `…` with no crash |
| Module 2 offline | Seasonal factor falls back to local lookup; ML banner shows mock data |
| Module 3 offline | Trigger feed shows simulated entries + amber banner |
| Module 3 offline | Claims table shows mock claims + warning badge |
| Stress test API offline | Mock result with 8 zones generated client-side |
| All modules offline | Dashboard renders, all cards show graceful fallback state |

---

## Compliance Verification

| Regulation | Evidence |
|------------|---------|
| **DPDP 2023** | `Rider.aadhaar_last4` (last 4 only), analytics aggregated, 7-day sensor purge documented in `main.py` |
| **IRDAI Parametric** | Pricing = zone × seasonal × tier rate (see admin.py module comment block) |
| **IRDAI Zero-touch** | Claims auto-processed by `process_disruption_claims()` in Module 3 |
| **IRDAI Fraud** | GPS + density detection only — no behavioral profiling (see fraud route comments) |
| **SSC 2020 §38** | Demo: 14-day window; Production: 90-day engagement target (see stress_test endpoint) |
