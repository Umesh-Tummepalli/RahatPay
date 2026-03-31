# RahatPay Phase 2 — Implementation Requirements
# Smart-Work Edition: Demo-first, depth-second. Ship by Saturday.

---

## Ground Rules Before You Start

1. Every module must produce something demo-able by Day 3. No module should be "still building core logic" on Day 4.
2. Hardcode what you can, calculate what you must. A hardcoded zone risk table that returns the right numbers is indistinguishable from a trained ML model in a 2-minute demo.
3. If it's not visible in the demo video, it's not a priority. CHECK constraints on the database? Yes, judges can see that in code review. Bayesian recalibration? No, push to Phase 3.
4. The API contract is agreed on Day 1 before anyone writes application code. Person 5 owns this.

---

## Project Structure

```
rahatpay/
├── README.md                        # Setup instructions (judges specifically called this out)
├── requirements.txt                 # All Python dependencies in one file
├── main.py                          # Single FastAPI entry point that imports all module routes
├── module1-registration/            # Person 1
├── module2-risk-engine/             # Person 2
├── module3-triggers-claims/         # Person 3
├── module4-mobile-app/              # Person 4
├── module5-integration/             # Person 5
```

All three backend modules (1, 2, 3) run as one single FastAPI server. Person 1 creates the main.py file that imports routes from each module. Person 4 builds a separate React Native app that talks to this server. Person 5 provides seed data and runs integration tests.

Git branching: each person works on their own branch (module1/registration, module2/risk-engine, etc). Nobody pushes to main directly. On integration day, Person 5 merges all branches into main and runs the end-to-end test.

---

---

## MODULE 1 — Registration & Policy Management

**Owner:** Person 1
**Tech:** FastAPI, PostgreSQL, Firebase Admin SDK

---

### What You're Building

You own the database and the identity layer. Every other module reads from your tables. You build the schema, the registration flow, the policy lifecycle, and the dashboard endpoints. You also set up the shared FastAPI app structure that Modules 2 and 3 plug into.

---

### Your Database (Build This First — Day 1 Morning)

You need six tables. Here's what each one stores and why it exists:

**zones** — Pre-populated reference table. Each row is a pin code with its city name, area name, and risk multiplier. Person 2 provides the risk values, Person 5 provides the seed data. This table is read-only during normal operation — nobody writes to it at runtime.

**riders** — One row per registered rider. Stores their Partner ID, platform (swiggy/zomato), name, phone, city, tier choice, three zone pin codes (foreign keys to the zones table), baseline income and hours, a boolean flag for whether they're in the seasoning period, and their trust score. The Partner ID must be unique — reject duplicates.

**policies** — One row per active policy. Links to a rider. Stores the tier, the calculated weekly premium, all four premium components (income, tier rate, zone risk, seasonal factor) so the breakdown can be displayed, the weekly payout cap, the coverage types (environmental only, or environmental + social, etc), the policy status, and the cycle start/end dates. The premium must have a CHECK constraint ensuring it's at least ₹15 (the floor).

**disruption_events** — You create this table but Module 3 writes to it. Each row is a detected disruption: which zone, what type (rainfall, aqi, heat, civic), what severity level, the severity payout rate, which API detected it, the raw measurement value, start time, duration, and whether it's still active.

**claims** — Module 3 writes to this. Each row is one rider's claim against one disruption event. Stores the disrupted hours, hourly rate, disrupted income, severity rate, gross payout, weekly cap, already-paid-this-week amount, and final payout. Also stores the four gate results (booleans) and a rejection reason if applicable. The final_payout column must have a CHECK constraint — this is one of our key USPs (database-level financial governance). Set it to reject anything above ₹5,000 as a safety ceiling.

**payouts** — One row per disbursement. Links to a claim and a rider. Stores the amount, payment method, a Razorpay reference ID (will be a test-mode ID), and status. Amount must have a CHECK constraint matching the claims table ceiling.

The CHECK constraints are important — they're explicitly mentioned in our README as a differentiator, and judges will look at the schema during code review.

---

### Endpoints You Must Build

**Auth endpoints** — Two simple endpoints for OTP login. The first takes a phone number and sends an OTP via Firebase. The second takes the phone + OTP, verifies it, and returns a JWT token. If the phone number is already registered, include the rider_id in the response so the app knows to skip registration and go straight to the dashboard.

**Registration endpoint** — Takes the rider's Partner ID, platform, name, phone, KYC details (Aadhaar last 4 or PAN), city, three zone pin codes, and tier choice. You need to: validate that the Partner ID isn't already taken, validate that all three pin codes exist in the zones table, fetch the rider's baseline from Module 2 (if the rider is new, Module 2 returns the city median), calculate the premium by calling Module 2's premium calculator, create the rider record, create the policy record with a 4-week cycle, and return the full response including the premium breakdown. This is the most important endpoint in the system because it touches Modules 1 and 2 together.

**Dashboard endpoint** — Takes a rider_id and returns everything the app needs for the home screen: name, tier, premium amount and breakdown, list of zones with area names and risk values, baseline income/hours/hourly rate, coverage details (weekly payout cap, how much has been paid this week, remaining headroom), policy status, and cycle end date. The "already paid this week" calculation requires summing approved payouts from the claims table for the current week — this is how Modules 1 and 3 connect.

**Payout history endpoint** — Returns all claims for a rider, sorted newest first. Each entry should include the date, event type, severity, disrupted hours, payout amount, status, and the four gate results. This is what the app's payout history screen displays.

**Zones endpoint** — Takes a city name and returns all available zones for that city from the zones table. Used by the app during registration to populate the zone selection dropdowns.

**Tiers endpoint** — Returns all three tiers with their rates, payout cap percentages, coverage types, claim speed, and trust score requirements. Used by the app during registration to show the tier comparison cards. This is static data but serves it from the API so the app doesn't hardcode it.

---

### How Module 2 Plugs Into You

When a rider registers, you need to calculate their premium. You do this by importing Module 2's calculate_premium function directly — it's a Python function in the same codebase, not a separate HTTP call. You pass it the baseline income, tier, zone pin codes, and optionally the current month. It returns the premium amount and full breakdown. You store the breakdown components in the policies table.

Similarly, you import Module 2's get_baseline function to get the rider's income/hours. For new riders (seasoning = true), this returns the city median. For established riders, it returns the rolling average from seeded data.

---

### How to Verify This Module Works

Register a rider through the endpoint using Ravi's profile from the README (Swiggy, Chennai, Suraksha, zones 600017/600020/600032). The premium should come back around ₹72-80 depending on the seasonal factor. Register the same Partner ID again — should get a 409 conflict. Hit the dashboard endpoint — all fields should be populated. Hit the payout history — should return an empty list for a new rider. Register Arjun (Kavach, Pune, low income) — premium should be ₹15 (floor activated). These four checks confirm your module works.

---

---

## MODULE 2 — AI Risk Engine & Premium Calculator

**Owner:** Person 2
**Tech:** Python (pure functions), optionally FastAPI for standalone testing

---

### What You're Building

The pricing brain. You deliver two capabilities: given a pin code, return a zone risk multiplier; given a rider's details, return their calculated weekly premium with full breakdown. Module 1 calls you during registration. Module 3 calls you during claim processing to get the rider's hourly rate.

---

### Smart Approach — Layer It

**Layer 1 (Day 1, 2-3 hours, must ship):** A hardcoded dictionary of zone risk values for 10-12 pin codes across four cities, a seasonal factor lookup by month, the premium formula as a pure function, and the affordability guardrails (₹15 floor, 3.5% ceiling). This immediately unblocks Module 1.

**Layer 2 (Day 2, if time):** The baseline profiler — a function that takes a rider_id and returns their average weekly income, hours, and hourly rate. For seasoning riders, it returns the city median. For established riders, it reads from seeded activity data.

**Layer 3 (Day 3-4, only if everything else is done):** Replace the hardcoded zone risk dictionary with an actual XGBoost model trained on synthetic data. Same input/output interface — just smarter internals. This is a nice-to-have that impresses judges during code review but is invisible in the demo.

---

### Zone Risk Multiplier

Create a JSON file or Python dictionary mapping pin codes to risk values. You need at least 10 entries across Chennai (3-4 zones), Mumbai (2-3 zones), Bangalore (2 zones), and Delhi (2 zones). The values should range from 0.85 (historically safe) to 1.35 (flood-prone). These aren't random — they should reflect real geographic patterns. For example, Dharavi in Mumbai should be high (flood-prone low-lying area), Koramangala in Bangalore should be low (well-drained, stable infrastructure).

The function takes a list of pin codes (a rider's top 3 zones) and returns the average risk multiplier across them. If a pin code isn't in the table, return 1.00 as the default.

---

### Seasonal Factor

A simple lookup: map each month (1-12) to a multiplier between 0.90 and 1.25. January-February and November-December are dry/stable (0.90). June-August are peak monsoon (1.20-1.25). April-May are pre-monsoon heat (1.05-1.10). The function takes a month number (or defaults to current month) and returns the factor.

---

### The Premium Formula

This is the core function. Takes four inputs: baseline_weekly_income, tier (kavach/suraksha/raksha), list of zone pin codes, and month. Computes:

`raw_premium = income × tier_rate × zone_risk × seasonal_factor`

Then applies guardrails: if raw_premium is below ₹15, clamp to ₹15. If raw_premium exceeds 3.5% of income, clamp to that ceiling. Then computes the weekly payout cap (tier's coverage percentage × income).

Returns the final premium, all four components of the breakdown, the raw (pre-guardrail) premium, the payout cap, and the premium as a percentage of income.

The tier rates are: kavach = 1.0%, suraksha = 1.8%, raksha = 2.5%.
The payout cap percentages are: kavach = 35%, suraksha = 55%, raksha = 70%.

---

### Baseline Profiler

A function that returns a rider's weekly income, hours, and hourly rate. Two modes:

If the rider is in their seasoning period (is_seasoning = true), return the city-level median. Store these as a simple dictionary: Chennai = ₹3,000/week and 50 hours, Mumbai = ₹3,500 and 50 hours, Bangalore = ₹3,200 and 48 hours, Delhi = ₹2,800 and 45 hours, Pune = ₹3,000 and 50 hours. The hourly rate is income divided by hours.

If the rider is established, return their actual baseline from the database (which will be pre-populated by Person 5's seed data). For the demo, this means the riders.baseline_weekly_income and riders.baseline_weekly_hours fields from the riders table.

---

### Endpoints (For Standalone Testing)

You should expose your premium calculator and zone risk lookup as API endpoints so Person 5 can test them independently and Person 4 can show the premium breakdown screen. A premium calculation endpoint that takes income, tier, zones, and month, and returns the full result. A zone risk endpoint that takes a pin code and returns its area name and multiplier. A baseline endpoint that takes a rider_id and returns their income/hours/hourly rate.

---

### How to Verify

Test Ravi's premium: income 3500, tier suraksha, zones 600017/600020/600032, month 7. Result should be approximately ₹72-80. Test Arjun's premium: income 1400, tier kavach, zone 560034, month 2. Result should be ₹15 (floor). Test a high earner on Raksha in Dharavi during monsoon: the result should not exceed 3.5% of their income (ceiling). Test two riders with the same income but different zones — the one in the riskier zone should pay more. These are the four checks that prove your formula works correctly.

---

---

## MODULE 3 — Trigger Monitor & Claims Engine - Kshitij 

**Owner:** Person 3
**Tech:** FastAPI (background tasks), httpx for API calls, Razorpay Python SDK (test mode)

---

### What You're Building

The engine that makes this product parametric. You detect disruptions from external APIs, find affected riders, validate their eligibility, calculate their payouts, and record the disbursement. This is the most complex module — but with the smart approach, you can have a working version by Day 2.

---

### Trigger Monitor

A background service that polls external APIs at a regular interval (60 seconds) and checks if any thresholds have been crossed in any monitored zone.

**OpenWeatherMap integration** — For each monitored zone (by lat/long coordinates), fetch current weather data. Check rainfall against the thresholds: 35-65mm/6hr = Moderate (30%), 65-115mm/6hr = Severe L1 (45%), 115-150mm/6hr = Severe L2 (60%). Also check temperature: above 42°C for 3+ hours = Moderate (30%). OpenWeatherMap's free tier gives you 60 calls per minute — more than enough for 10 zones at 60-second intervals.

**AQI integration** — Use OpenWeatherMap's Air Pollution API (included in the free tier). It returns PM2.5 values which you can approximate to the Indian AQI scale. Check against: AQI 200-300 = Moderate (30%), AQI above 300 = Severe L1 (45%).

**Mock civic disruption trigger** — Since there's no clean API for bandhs and curfews, build this as an admin-triggered endpoint. When someone hits the endpoint with a zone and severity, it creates a disruption event as if it came from a real API. This is how you'll demonstrate civic disruptions in the demo.

**Mock extreme heat trigger** — Same as civic — an admin endpoint that simulates extreme heat for a specific zone. Useful for demos in cities where real-time temperature won't hit 42°C.

When a threshold is crossed, you write a disruption event to the disruption_events table (which Module 1 created). Then you immediately kick off the claims engine for that event.

The severity classification must be a pure lookup — no ML, no judgment. Same input always produces the same severity and the same payout rate. This is explicitly stated in our README as a design principle.

---

### The Simulate Disruption Endpoint

This is the single most important endpoint for the demo. It's what you'll hit on camera to show the full automated flow.

It takes a zone pin code, event type, severity, duration in hours, and the raw measurement value. It creates the disruption event record. Then it queries the riders table for all riders who have that zone in any of their three zone slots. For each affected rider, it runs the eligibility check, and for those who pass, it calculates the payout. It returns a detailed response showing: how many riders were affected, how many claims were initiated, how many were rejected, the total payout amount, and a list of each rider's individual result including their gate results and payout amount (or rejection reason).

This endpoint essentially orchestrates the entire claims flow in one call. It's the demo button.

---

### 4-Gate Eligibility Validator

For each affected rider, run these four checks in sequence. If any gate fails, stop and record the rejection reason.

**Gate 1 — Zone match:** Does the disruption zone appear in the rider's three registered zones? This is a simple string comparison against zone1_pincode, zone2_pincode, zone3_pincode. If none match, reject with a message like "Disruption in zone 600017 is not in your registered zones."

**Gate 2 — Shift window overlap:** Does the disruption time fall within the rider's working hours? For the smart approach, hardcode typical shift windows: daytime riders work 10 AM to 3 PM and 6 PM to 10 PM. Check if the event's start hour falls within either window. If it doesn't, reject with a message like "Disruption at 1:00 AM is outside your established shift window (10 AM–3 PM, 6 PM–10 PM)." This is how Scenario E from the README works — a 1 AM storm triggers nothing for a daytime rider.

**Gate 3 — Platform inactivity:** Is the rider confirmed offline (not earning) on their delivery platform? For Phase 2, simplify this to always return true. In production, you'd check the delivery platform's API. Document this as a mock in the code with a comment explaining what the real implementation would do.

**Gate 4 — Sensor fusion:** Does sensor data confirm the rider's location? For Phase 2, simplify this to always return true. Full sensor fusion (GPS × Cell Tower × IMU × Wi-Fi) is a Phase 3 deliverable. Again, document what the real implementation would check.

The key is that even though gates 3 and 4 are simplified, the structure is there. The four-gate framework is visible in the code, the claim record stores all four boolean results, and the rejection reasons are plain-language. This satisfies the judges — they can see the architecture works even if two gates are mocked.

---

### Payout Calculator

Pure arithmetic, no ML. For a rider who passes all four gates:

1. Get the rider's hourly rate from Module 2's baseline profiler (hourly_rate = baseline_income / baseline_hours).
2. Multiply by disrupted hours to get disrupted income.
3. Multiply by the severity rate to get gross payout.
4. Get the rider's weekly payout cap from their policy (tier percentage × baseline income).
5. Query all approved claims for this rider in the current week to get already_paid_this_week.
6. Calculate remaining headroom: weekly_cap minus already_paid.
7. Final payout is the minimum of gross payout and remaining headroom. Cannot be negative.

Store every step of this calculation in the claim record — disrupted hours, hourly rate, disrupted income, severity rate, gross payout, weekly cap, already paid, and final payout. This transparency is important for the app's claim detail screen and for judges reviewing the logic.

---

### Razorpay Mock Disbursement

After a claim is approved and the payout is calculated, create a mock payment via Razorpay's test mode. This means: sign up for a Razorpay test account (free), use the test API keys, and make an API call to create a payout. In test mode, no real money moves — you get back a payment ID and a "completed" status. Store the Razorpay payment ID in the payouts table.

If Razorpay setup takes too long, an acceptable fallback is to simply write a log entry with the payout details and set the status to "completed" — then add Razorpay on Day 3-4 if time permits. The judges care about the claim flow, not whether Razorpay specifically was integrated.

---

### How to Verify

Test Scenario A from the README: simulate severe rainfall in zone 600017, 3 hours. Ravi (Suraksha, ₹3,500/week, ₹70/hr) should get a payout of ₹94.50 (3 × 70 × 0.45). Test Scenario D: simulate an extreme event for 50 hours. Ravi's gross payout would be ₹2,625 but it should be capped at ₹1,925 (55% × 3,500). Test Scenario E: simulate a disruption at 1 AM — Ravi should be rejected at Gate 2 with a plain-language reason. Test Scenario C: simulate two events in one week — the second payout should respect the remaining headroom after the first payout. These four scenarios are from the README and the judges know them — your results must match exactly.

---

---

## MODULE 4 — Mobile App (Rider-Facing)

**Owner:** Person 4
**Tech:** React Native (Android-first), Firebase Auth, Axios

---

### What You're Building

The complete rider experience — everything from opening the app to seeing a payout land. You build screens, connect them to the backend API, and make the whole thing look polished on an Android device (or emulator). Your output is what appears in the demo video.

---

### Smart Approach — Mock-First Development

Don't wait for the backend. On Day 1, create a mock data file that mirrors the exact JSON shapes from the API contract. Build all your screens against this mock data. When the backend goes live (Day 2-3), swap the mock import for a real API call — the screens don't change at all, only the data source. This way you're never blocked by backend delays.

---

### Screens — In Build Order

**Screen 1: Login (Day 1, first thing)**
Phone number input field and an OTP field. Use Firebase Auth for the OTP flow. On successful verification, check if the phone is registered (the auth/verify-otp response includes rider_id — if it's null, the phone isn't registered yet). Navigate to registration if new, dashboard if existing. Keep this simple — it's a gateway, not a showcase.

**Screen 2-4: Registration Flow (Day 1)**
Three screens, one per step. Step 1 collects Partner ID, platform (Swiggy/Zomato dropdown), full name, and city. Step 2 collects Aadhaar last 4 digits or PAN number — validate the format on the client side (Aadhaar: exactly 4 digits, PAN: 5 letters + 4 digits + 1 letter). Show a green checkmark when valid. This is mock KYC — you're validating format, not actually checking against a government database. Step 3 is tier selection — show three cards side by side (Kavach, Suraksha, Raksha) with rate, payout cap, coverage types, and claim speed from the /tiers endpoint. Below the cards, three dropdowns for zone selection (populated from /zones/available for the selected city). A "Calculate Premium" button that calls the premium endpoint and displays the result with the full formula breakdown. A "Confirm & Subscribe" button that calls the registration endpoint.

The tier selection screen with the live premium calculation is where you want to spend extra polish. This is the moment in the demo where judges see our USP — the percentage-based formula with zone risk. Make the formula visible: show "₹3,500 × 1.8% × 1.10 × 1.15 = ₹80/week" with labels under each number (income, tier rate, zone risk, season).

**Screen 5: Dashboard / Home (Day 2)**
The main screen after login. Show the rider's name and tier as a colored badge at the top. Below that, the weekly premium amount in large text with a "View Breakdown" link to the formula screen. Then a section showing the three covered zones with area names. Then a coverage section: weekly payout cap, amount already paid this week, and remaining headroom shown as a progress bar or simple numbers. Policy status and renewal date at the bottom. Add pull-to-refresh so after a disruption is simulated, the rider can refresh and see the updated headroom.

**Screen 6: Premium Breakdown (Day 2)**
A dedicated screen showing the formula visually. Four rows, each showing one component: baseline income, tier rate, zone risk multiplier, seasonal factor. Each row has a label explaining what it means in plain language (e.g., "Zone risk: 1.10 — your delivery zones have moderate flood history"). The final calculated premium at the bottom. This screen exists because our README explicitly promises transparent premium calculation — judges will look for it.

**Screen 7: Payout History (Day 2-3)**
A list of past payouts fetched from /rider/{id}/payouts. Each item is a card showing: the date, event type with an icon (rain cloud for rainfall, thermometer for heat, warning sign for civic), severity level, disrupted hours, payout amount in bold, and status (approved in green, rejected in red, pending in yellow). Tapping a card navigates to the claim detail screen.

**Screen 8: Claim Detail (Day 3)**
Shows the full breakdown for a single claim. Four rows showing the four gates with pass/fail indicators (green checkmark or red X). If a gate failed, show the rejection reason in plain language below it. Below the gates, show the payout math: disrupted hours × hourly rate × severity rate = gross payout, and if capped, show the cap amount and the final payout. This screen demonstrates two things judges want to see: the transparent claim process and the plain-language rejection reasons.

---

### Push Notifications

When a payout is disbursed, the rider should get a push notification. For Phase 2, the simplest approach: after the simulate-disruption endpoint runs, the backend can send a Firebase Cloud Message to the rider's device. If that's too complex to wire up, an acceptable fallback is to show an in-app notification banner on the next dashboard refresh — "You received ₹94.50 for severe rainfall in T. Nagar."

---

### How to Verify

Open the app on an Android emulator. Go through the full registration flow with Ravi's details. Confirm the premium matches ~₹80. Navigate to the dashboard — all fields should be populated. Ask Person 3 to hit the simulate-disruption endpoint. Pull-to-refresh the dashboard — the "already paid this week" should update and the payout should appear in the history screen. Tap the payout — gate results and math should be visible. Register a second rider and simulate a 1 AM storm — the payout history should show a rejected claim with a clear reason. These checks mirror the demo video script.

---

---

## MODULE 5 — Seed Data, Integration & Demo

**Owner:** Person 5
**Tech:** Python scripts, Postman, any screen recording tool

---

### What You're Building

You are the glue person. You don't build the deepest features, but you make sure all four modules actually work together. Without your work, the team has four separate apps that can't connect. You own three things: the API contract, the seed data, and the demo.

---

### Day 1 Deliverable — API Contract

Before anyone writes a single line of application code, you write the API contract and share it with the team. This is a document listing every endpoint in the system: the URL, the HTTP method, the request body JSON shape, and the response JSON shape. Every field name must be agreed upon — if Person 1 names it "rider_id" but Person 4 expects "riderId", integration breaks.

The contract should cover: auth endpoints (send-otp, verify-otp), registration (register, dashboard, payouts, zones, tiers), premium (calculate, zone-risk, baseline), and triggers/claims (simulate-disruption, active triggers, claim detail, disburse payout). Around 14 endpoints total.

Write this in a Markdown file and drop it in the shared repo. Also create a Postman collection with the same endpoints pre-filled with example requests. This collection becomes your integration test suite.

---

### Seed Data

You create the reference data that populates the system. Four files:

**Riders** — 10 pre-built rider profiles. Include: Ravi (Suraksha, Chennai, ₹3,500/week — the primary demo persona), Arjun (Kavach, Pune, ₹1,400/week — the part-time rider), Kiran (Raksha, Mumbai, ₹5,000/week — the high earner), a seasoning rider with zero baseline (to test provisional coverage), a night-shift rider (to test shift window rejection), and five more to fill out the demo. Each profile should have the Partner ID, platform, name, city, zones, tier, baseline income, baseline hours, and seasoning status. Make sure the zone pin codes match what Person 2 has in their zone risk table.

**Zones** — 10-12 pin codes across Chennai, Mumbai, Bangalore, and Delhi. Each entry has the pin code, city, area name, and risk multiplier. Coordinate with Person 2 — your values must match their zone risk table exactly.

**Disruption scenarios** — 4 pre-built scenarios ready to fire during the demo. Scenario 1: severe rainfall in Chennai zone 600017, 3 hours, 85mm — expected to pay Ravi ~₹94.50. Scenario 2: AQI spike in Delhi zone 110001, 6 hours, AQI 350. Scenario 3: extreme cyclone in Mumbai zone 400017, 9 hours. Scenario 4: severe rainfall at 1 AM in Chennai — expected to be rejected for daytime riders (shift window gate fails). These map directly to the README scenarios.

**City medians** — The provisional baseline values for each city. Chennai: ₹3,000/week, 50 hours. Mumbai: ₹3,500/week, 50 hours. Bangalore: ₹3,200/week, 48 hours. Delhi: ₹2,800/week, 45 hours. Pune: ₹3,000/week, 50 hours. Person 2 uses these for the seasoning rider fallback.

Write a Python script that loads this seed data into the PostgreSQL database. This script should be runnable with a single command — something like `python seed.py`. Person 1 creates the schema, you populate it.

---

### Integration Testing

Your main job from Day 3 onward. You write and run the end-to-end test that proves the full flow works. The test does this in sequence:

1. Register a rider through the registration endpoint. Verify the response includes a rider_id and a premium.
2. Hit the dashboard endpoint. Verify all fields are present and the premium matches.
3. Hit the simulate-disruption endpoint with Scenario 1 (rainfall in Chennai). Verify the response shows affected riders and calculated payouts.
4. Hit the dashboard endpoint again. Verify that "already paid this week" has increased and the remaining headroom has decreased.
5. Hit the payout history endpoint. Verify the payout appears with the correct amount and status.
6. Hit the simulate-disruption endpoint with Scenario 4 (1 AM storm). Verify that daytime riders are rejected with a plain-language reason.

If this test passes, the demo will work. If any step fails, you know exactly where the integration broke and can tell the relevant module owner what to fix.

Also test the edge cases: duplicate Partner ID registration (should fail), invalid zone pin code (should fail), Arjun's premium (should hit the ₹15 floor), catastrophic week payout (should hit the weekly cap).

---

### Demo Video (Day 4-5)

Record a 2-minute screen recording. The script:

0:00-0:15 — Open the app, login with OTP.
0:15-0:35 — Walk through registration: Partner ID, KYC, tier selection. Show the premium calculated live with the formula breakdown on screen.
0:35-0:50 — Show the dashboard: tier badge, premium, zones, headroom.
0:50-1:10 — Switch to terminal or Postman. Hit the simulate-disruption endpoint for Scenario 1. Show the response with affected riders, gate results, and payout amounts.
1:10-1:30 — Switch back to app. Refresh the dashboard. Show the payout appearing in history with the amount and gate details. Show the headroom has decreased.
1:30-1:50 — Demonstrate an ineligible claim: simulate a 1 AM storm, show the rejection with a plain-language reason visible in the app.
1:50-2:00 — Close with the premium formula visible one more time.

---

### Repo Setup (Judges Called This Out Specifically)

The Phase 1 feedback said "the repository lacks any technical implementation — no code, dependencies, or project setup." Fix this explicitly:

The root README must include clear setup instructions: what to install, how to set up the database, how to seed it, how to start the server, and how to run the app. A requirements.txt at the root with all Python dependencies. A package.json in the mobile app folder. A .env.example file showing what environment variables are needed (database URL, OpenWeatherMap API key, Firebase config, Razorpay test keys). The repo should be cloneable and runnable by someone following the README — even if they're a judge who wants to try it.

---

### How to Verify Your Work

The Postman collection has working examples for all 14 endpoints. The seed script runs without errors and populates the database. The end-to-end integration test passes all 6 steps. The demo video shows the full flow without cuts or errors. The repo has a README with setup instructions, requirements.txt, and .env.example.

---

---

## HOW ALL FIVE MODULES CONNECT

### The Shared Server

Modules 1, 2, and 3 are not three separate servers. They're three sets of route files that get imported into a single FastAPI application. Person 1 creates the main.py file at the project root that imports routes from all three modules and mounts them under their respective URL prefixes. Run one server, all endpoints are available.

### The Three Cross-Module Handoff Points

**Handoff 1: Registration (Module 1 calls Module 2)**
When a rider registers, Module 1 imports Module 2's baseline profiler to get the rider's income, and Module 2's premium calculator to compute the premium. This is a direct Python function import, not an HTTP call. Person 1 and Person 2 must agree on the function signatures on Day 1. The baseline profiler takes a rider_id, city, and is_seasoning flag, and returns a dictionary with weekly_income, weekly_hours, hourly_rate, and source. The premium calculator takes baseline_income, tier, zone_pincodes, and month, and returns a dictionary with weekly_amount, breakdown, and payout_cap.

**Handoff 2: Claim Processing (Module 3 calls Module 2 and reads Module 1's tables)**
When a disruption is detected, Module 3 queries the riders table (owned by Module 1) to find all riders in the affected zone. Then for each rider, Module 3 imports Module 2's baseline profiler to get their hourly rate for the payout calculation. Person 3 and Person 2 must agree that the get_baseline function works for any rider_id in the database.

**Handoff 3: Dashboard (Module 1 reads Module 3's tables)**
When the app requests the dashboard, Module 1 queries the claims and payouts tables (written by Module 3) to calculate "already paid this week" and "remaining headroom." Person 1 and Person 3 must agree on the claim status values (pending, approved, rejected, in_review, paid) and the payout status values (initiated, processing, completed, failed).

### The Mobile App Connection

Module 4 (the app) talks to the single FastAPI server over HTTP. It doesn't know or care which backend module handles which endpoint — it just hits URLs and gets JSON back. The API contract document from Person 5 is the single source of truth for what those URLs are and what the responses look like. Person 4 builds against mock data that matches the contract, then swaps in real API calls on integration day.

### Integration Day Sequence

Day 4 morning: Person 5 merges all branches into main. Runs pip install and npm install. Creates the database and runs the seed script. Starts the FastAPI server. Runs the Postman collection to verify all endpoints respond. Runs the end-to-end test script.

Day 4 afternoon: Person 4 updates the app's API base URL to point to the running server. Tests all screens with live data. Person 5 walks through the demo script and identifies any issues.

Day 4 evening or Day 5: Record the demo video. Push everything to GitHub. Verify the README has setup instructions. Submit.

---

*If it's not in this document, don't build it. If it is in this document, it must ship. No exceptions, no scope creep, no over-engineering. Ship by Saturday.*
