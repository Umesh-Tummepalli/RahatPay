# RahatPay — AI-Powered Parametric Income Insurance for India's Food Delivery Workers

> **Guidewire DEVTrails 2026 | Phase 1 Submission**  
> **Team:** Bool Sheet | **University:** SRM INSTITUTE OF SCIENCE AND TECHNOLOGY
> **Persona:** Food Delivery Partners — Zomato & Swiggy

---

## Table of Contents

1. [The Problem](#the-problem)
2. [Our Solution](#our-solution)
3. [Why Mobile-First](#why-mobile-first)
4. [Persona & Scenarios](#persona--scenarios)
5. [Coverage Tiers](#coverage-tiers)
6. [Weekly Premium Model](#weekly-premium-model)
7. [Parametric Triggers](#parametric-triggers)
8. [Payout Formula & Worked Examples](#payout-formula--worked-examples)
9. [Application Workflow](#application-workflow)
10. [AI/ML Integration](#aiml-integration)
11. [Adversarial Defense & Anti-Spoofing Strategy](#adversarial-defense--anti-spoofing-strategy)
12. [Trust Score System](#trust-score-system)
13. [Revenue Model](#revenue-model)
14. [Policy Terms & Rider Protections](#policy-terms--rider-protections)
15. [Exclusions](#exclusions)
16. [Tech Stack](#tech-stack)
17. [6-Week Development Roadmap](#6-week-development-roadmap)
18. [Open Questions](#open-questions)

---

## The Problem

India's food delivery riders earn only when they deliver. A single week of heavy monsoon rain, a cyclone warning, or a sudden city-wide bandh can wipe out 20–30% of a rider's monthly income overnight. There is no safety net — when the storm hits, the rider absorbs the entire loss.

**RahatPay** closes this gap with parametric insurance: coverage that triggers automatically from measurable external events, pays out without paperwork, and costs a small percentage of what the rider already earns.

---

## Our Solution

RahatPay is a mobile-first, AI-enabled parametric insurance platform designed exclusively for food delivery partners on Zomato and Swiggy. The core principles:

**Parametric, not indemnity-based.** Payouts are triggered automatically by measurable external events — no claim filing, no document submission, no waiting period.

**Income-proportionate premiums.** Your premium is a percentage of your own income, adjusted for how risky your delivery zone is. A rider earning ₹10,000/week pays more than one earning ₹3,000/week — but both pay the same proportion, and both receive proportionate coverage. No cross-subsidies.

**Weekly pricing.** Aligned with the week-to-week earning and payout cycle of gig workers. Auto-deducted from platform settlements.

**Zero-touch claims.** The system monitors weather, AQI, and civic disruptions in the background and initiates payouts automatically when triggers are met — the rider does nothing.

**Income loss only.** We strictly exclude health, life, accident, and vehicle repair coverage.

---

## Why Mobile-First

The rider-facing app is built as an Android-first mobile application. The insurer/admin interface is a React.js web dashboard. Here's why:

**Riders are on the road, not at desks.** Zomato and Swiggy delivery partners work from their bikes with a phone mounted on the handlebar. A mobile app is the only interface they interact with during working hours. Push notifications for instant payout confirmations, real-time coverage status during a storm, and premium deduction alerts all require a native mobile experience.

**Sensor access is critical for fraud prevention.** RahatPay's anti-spoofing layer depends on GPS, cell tower triangulation, accelerometer, gyroscope, magnetometer, and Wi-Fi SSID data. These sensors are only available through a native mobile app — a web browser cannot access them.

**Offline-first capability.** Disruptions that trigger claims (heavy rain, floods, network outages) are exactly the conditions where internet connectivity is unreliable. The mobile app caches the rider's baseline, shift data, and coverage details locally. Sensor heartbeat logs are stored on-device and synced when connectivity resumes, ensuring no claim is lost to a network gap.

**Target hardware.** Over 95% of Indian delivery partners use Android devices, predominantly mid-range (Redmi, Realme, Samsung M-series). React Native with Android-first optimisation targets this hardware directly. iOS is deprioritised but not excluded — the same codebase can ship to iOS when the user base warrants it.

---

## Persona & Scenarios

### Ravi — Swiggy Rider, Chennai (Suraksha)

Ravi has been delivering for Swiggy for 14 months. He works 10 AM–3 PM and 6 PM–10 PM daily — approximately 50 active hours per week. His 4-week rolling average income is **₹3,500/week** (₹70/hour). He operates across T. Nagar, Adyar, and Velachery. His zones carry a risk multiplier of **1.10** (moderate flood history). It's July — seasonal factor is **1.15** (monsoon).

**His weekly premium:** `₹3,500 × 1.8% × 1.10 × 1.15 = ₹80` — that's 2.28% of his income, roughly one delivery's worth.

### Arjun — Zomato Rider, Pune (Kavach)

Arjun is a college student who delivers part-time — 20 hours/week, evenings only. His 4-week rolling average is **₹1,400/week** (₹70/hour). He operates in a single zone (Kothrud), which is historically stable — zone multiplier **0.85**. It's February — seasonal factor **0.90**.

**His weekly premium:** `₹1,400 × 1.0% × 0.85 × 0.90 = ₹11` — clamped to the ₹15 floor. Arjun pays the minimum and gets environmental-only coverage with a weekly payout cap of 35% of his income (₹490).

---

**Scenario A — Severe Rainfall (Ravi, 3 hours lost)**  
IMD Red Alert for Chennai. Swiggy suspends operations 11 AM–2 PM in Ravi's zones.
```
Disrupted income = 3 × ₹70           = ₹210
Gross payout     = ₹210 × 45%        = ₹94.50
Weekly cap       = 55% × ₹3,500      = ₹1,925
Final payout     = ₹94.50 ✓  (auto-deposited to UPI within 6–12 hours)
```

**Scenario B — Cyclone (Ravi, full shift lost)**  
All platforms suspended city-wide, 9 hours lost.
```
Disrupted income = 9 × ₹70           = ₹630
Gross payout     = ₹630 × 75%        = ₹472.50
Weekly cap       = ₹1,925
Final payout     = ₹472.50 ✓
```

**Scenario C — Two events in one week (Ravi)**  
Tuesday: Severe L1, 3 hours → ₹94.50 paid. Thursday: Severe L1, 4 hours.
```
Thursday gross   = 4 × ₹70 × 45%     = ₹126
Remaining cap    = ₹1,925 − ₹94.50   = ₹1,830.50
Final payout     = ₹126 ✓  (weekly total: ₹220.50)
```

**Scenario D — Catastrophic week (Ravi, all 50 hours lost)**  
The cap does real work here:
```
Gross payout     = ₹3,500 × 75%      = ₹2,625
Weekly cap       = ₹1,925
Final payout     = ₹1,925 ✓  (capped — keeps the loss ratio viable)
```

**Scenario E — Storm at 1 AM (ineligible)**  
Ravi has never worked past 10 PM across his 4-week baseline. No income was at risk. No payout.

**Scenario F — New rider, seasoning period (Arjun)**  
Arjun enrolled 3 days ago. No personal baseline yet. RahatPay uses Pune's city-level median (₹3,000/week, ₹60/hr) as a provisional baseline. Once his 2-week seasoning period ends, his own data takes over.

---

## Coverage Tiers

The tier controls two things: how much of your income you're insuring (payout cap), and what types of disruptions are covered. The premium is a percentage of income — not a flat rupee amount.

| | **Kavach** | **Suraksha** | **Raksha** |
|---|---|---|---|
| **For** | Part-time / new riders | Full-time, standard risk | Full-time, high-risk zones |
| **Premium rate** | 1.0% of income | 1.8% of income | 2.5% of income |
| **Weekly payout cap** | 35% of income | 55% of income | 70% of income |
| **Disruptions covered** | Environmental only | Environmental + Social | Env + Social + Composite |
| **Claim speed** | 24–48 hours | 6–12 hours | 2–4 hours |
| **Trust score required** | None | 30+ | 60+ |

**Why percentage-based premiums matter:** Under a flat-premium model, a rider earning ₹10,000/week and one earning ₹3,000/week would both pay ~₹50 but receive wildly different coverage. The high earner gets subsidised by the low earner. A percentage-based premium eliminates this — you pay proportional to what you're insuring.

Riders begin at Kavach with zero friction. As their Trust Score grows and platform activity demonstrates consistent earnings, the app proactively offers tier upgrades with a side-by-side cost-vs-benefit comparison. Downgrades are permitted at any 4-week policy cycle boundary.

---

## Weekly Premium Model

### Why Weekly

Gig workers operate and are paid week-to-week. Monthly premiums create a cash-flow mismatch — demanding a lump payment before the worker has earned that month's income. Weekly pricing aligns with Swiggy/Zomato's own settlement cycles, enabling frictionless auto-deduction directly from the rider's weekly payout.

### The Formula

```
Weekly Premium = Baseline Income × Tier Rate × Zone Risk Multiplier × Seasonal Factor
```

**Baseline Income** — Rolling 4-week average of the rider's actual platform earnings. Calculated from real activity data, not self-reported. The same baseline that determines your premium also determines your payout — you can't game one without gaming the other.

**Tier Rate** — The rider's choice: 1.0% (Kavach), 1.8% (Suraksha), or 2.5% (Raksha). Higher rate = deeper coverage.

**Zone Risk Multiplier (0.80 – 1.50)** — A composite score per pin-code zone, built from four weighted data sources:

| Data Source | Weight | What It Measures |
|---|---|---|
| Weather history (IMD, 10yr) | 40% | Flood days, red alerts, heavy rainfall frequency per zone |
| Disaster frequency (NDMA) | 25% | Declared calamities per zone over the past decade |
| Civic disruption history | 20% | Govt gazette-verified bandhs, curfews, hartals that halted platform operations |
| Environmental hazards | 15% | Heatwave days (>42°C), AQI exceedance days (>200) from CPCB records |

A rider in flood-prone Dharavi, Mumbai might get 1.35. A rider in stable Koramangala, Bangalore might get 0.85. Recalculated quarterly.

**Seasonal Factor (0.90 – 1.25)** — Monsoon months cost more. Dry/stable months cost less. Updated every 4-week policy cycle.

**Affordability guardrails:** Floor of ₹15/week (below this, API costs aren't covered). Ceiling of 3.5% of weekly income (even worst-case monsoon + highest-risk zone + Raksha never exceeds this).

### Same Income, Different Zones

Both riders: **Suraksha, ₹4,000/week, same season (1.0).**

| | **Ravi — Bangalore** | **Kiran — Mumbai** |
|---|---|---|
| Zone | Koramangala (stable) | Dharavi (flood-prone) |
| Zone multiplier | 0.85 | 1.35 |
| **Weekly premium** | **₹61** | **₹97** |
| Max weekly payout | ₹2,200 | ₹2,200 |

Kiran pays 59% more because he's statistically far more likely to claim. Over 52 weeks, Kiran might file 8–10 valid claims while Ravi files 2–3. The expected payout per rupee of premium converges for both — standard actuarial fairness.

### Unit Economics (Suraksha avg. ₹72/week)

| Allocation | Amount | Purpose |
|---|---|---|
| Loss Reserve | ₹50 (70%) | Funds claim payouts |
| Operations | ₹7 (10%) | Cloud, API fees, payment gateway |
| Net Margin | ₹15 (20%) | Platform sustainability |

Target Loss Ratio: 60–70%.

---

## Parametric Triggers

Triggers are objective and externally verifiable. Once the threshold is crossed, the payout rate is a fixed lookup — no AI judgment, no discretion.

| Trigger | Source | Threshold | Severity | Payout Rate |
|---|---|---|---|---|
| Rainfall | IMD / OpenWeatherMap | 35–65mm / 6hr | Moderate | 30% |
| Rainfall | IMD / OpenWeatherMap | 65–115mm / 6hr | Severe L1 | 45% |
| Rainfall | IMD / OpenWeatherMap | 115–150mm / 6hr | Severe L2 | 60% |
| Cyclone / Flood | IMD Disaster Alerts | Cat 1+ or declared flood | Extreme | 75% |
| Extreme Heat | OpenWeatherMap | >42°C for 3+ hours | Moderate | 30% |
| Air Pollution | CPCB AQI API | AQI 200–300 | Moderate | 30% |
| Air Pollution | CPCB AQI API | AQI >300 | Severe L1 | 45% |
| Civic Disruption | Govt gazette + NewsAPI entity extraction | Zone-specific access restriction, cross-verified against 2+ independent sources | Severe L1 | 45% |

**Civic disruption verification:** Unlike weather events (which have authoritative APIs), bandhs and curfews require multi-source validation. RahatPay's civic alert pipeline uses NLP entity extraction on NewsAPI feeds, cross-references against government gazette RSS notifications, and requires corroboration from at least two independent sources before a trigger is confirmed. Single unverified social media reports do not activate triggers.

**Why not 100% payout?** Two reasons. Moral hazard — if full replacement is guaranteed, some riders stay home during marginal conditions hoping for a trigger. Actuarial sustainability — the premium pool can't fund 100% replacement during mass events when thousands claim simultaneously.

A rider is eligible only when the disruption occurs within their **Top 3 Delivery Zones** — established from historical GPS data during seasoning and recalculated every 4 weeks, visible in-app at all times.

---

## Payout Formula & Worked Examples

Pure arithmetic. No ML, no judgment calls.

```
Hourly Rate      = Baseline Weekly Income ÷ Baseline Weekly Hours
Disrupted Income = Lost Active Hours × Hourly Rate
Gross Payout     = Disrupted Income × Severity Rate (fixed lookup)
Weekly Cap       = Tier Coverage % × Baseline Weekly Income
Final Payout     = min(Gross Payout, Weekly Cap − Already Paid This Week, Safety Ceiling)
```

Three-layer payout safety ensures no erroneous amount reaches the rider: a PostgreSQL `CHECK` constraint at the database level, sequential cap validation in the FastAPI backend, and a per-transaction ceiling configured at the Razorpay gateway. A payment runaway would require breaching all three independently — architecturally near-impossible.

---

## Application Workflow

```
ONBOARDING
├── Download app → Register with Swiggy/Zomato Partner ID
├── Aadhaar/PAN verification + optional facial biometric (Trust Score bonus)
├── Select tier (Kavach / Suraksha / Raksha)
└── 2-week seasoning begins (provisional coverage active from Day 1)

POLICY CREATION
├── AI Risk Engine scores rider's zones → calculates premium within guardrails
├── Premium displayed before confirmation
└── Auto-deducted from platform weekly payout (or UPI auto-pay)

ACTIVE COVERAGE
├── Continuous monitoring: Weather APIs, AQI feeds, civic alert pipeline
│
DISRUPTION DETECTED
├── 4-gate eligibility: Zone match → Shift window overlap → Platform inactive → Sensor fusion
├── All pass → Payout calculated and disbursed automatically
└── Any fail → Flagged for review (plain-language reason logged, appeal available)

POST-PAYOUT
├── Weekly headroom tracker updated, Trust Score updated
└── Premium recalculated at next 4-week cycle boundary (7 days notice)
```

---

## AI/ML Integration

### Module 1 — Risk Scoring & Premium Engine
XGBoost Gradient Boosted Tree model trained on 10+ years of IMD weather records, NDMA disaster logs, and civic disruption data. Produces a continuous zone risk score mapped to the 0.80–1.50 multiplier range. Retrained monthly as new event and claim data accumulates.

**Training data strategy:** Phase 1–2 models train on synthetic claim data generated by replaying historical IMD weather events against simulated rider populations (zone distribution, shift patterns, income ranges sampled from published gig economy reports). Public datasets used: IMD district-level rainfall records (2013–2024), NDMA declared disaster logs, CPCB AQI station data, and OpenWeatherMap historical archives. From Phase 3 onward, synthetic data is progressively replaced with actual RahatPay claim records using a warm-start transfer approach.

### Module 2 — Rolling Baseline Profiler
Tracks each rider's shift hours, delivery zones, order count, and income on a rolling 4-week window updated weekly. This is the single source of truth for both premium calculation and payout eligibility — visible to the rider in-app at all times.

### Module 3 — Claim Eligibility Validator
Rule-based engine running four sequential checks (zone → shift → platform inactivity → sensor fusion). All four must pass. No silent rejections — every failed check produces a plain-language explanation in the rider's preferred language.

### Module 4 — Seasonal & Post-Event Recalibration
Bayesian updating on zone-level disruption probability. A zone that flooded this week has elevated near-term risk — premium adjusts at the next cycle boundary, not mid-cycle. 7 days advance notice to the rider.

### Module 5 — Fraud Anomaly Detection
Isolation Forest model monitoring claim density patterns at zone level. Sudden spikes without matching external API verification are flagged for human review. See the Adversarial Defense section for the full architecture.

---

## Adversarial Defense & Anti-Spoofing Strategy

RahatPay's parametric model auto-disburses payouts without claim filing. This creates a specific adversarial surface: bad actors who fake their presence in a disaster zone to receive payouts they're not entitled to, while genuine stranded riders must not be punished by overzealous fraud filters. This section addresses three questions: how we spot fakers from genuine stranded workers, what data catches fraud rings, and how we flag bad actors without punishing honest riders.

### 1. Spotting Fakers vs. Genuine Stranded Workers

The primary adversarial threat is **GPS spoofing** — a rider using a mock-location app to appear inside a disrupted zone while actually sitting at home or working elsewhere. RahatPay's 3-layer sensor fusion engine makes this extremely difficult to sustain:

**Layer 1 — Network Triangulation:** GPS coordinates are cross-referenced against Cell Tower ID (cannot be faked by software) and a passive Wi-Fi SSID scan. A rider genuinely in T. Nagar during a rainstorm sees a constantly changing set of commercial Wi-Fi networks. A rider faking their location from home sees the same 2–3 residential SSIDs repeatedly. This contradiction is flagged automatically.

**Layer 2 — Kinematic Analysis:** A delivery bike in an affected zone has a characteristic accelerometer and gyroscope signature — engine vibration, road bumps, lean angles. If GPS claims the rider is at a busy intersection but the IMU reads as perfectly stationary, it's a spoof. Conversely, a rider who was genuinely en-route when rain started will show the natural deceleration pattern of someone pulling over and stopping.

**Layer 3 — Magnetometer Cross-Check:** Urban traffic environments produce fluctuating magnetic interference. A phone in an active delivery zone produces a noisy, variable magnetometer reading. A phone at home on a table produces a quiet, stable reading — a third independent verification signal.

Sensors activate **only when a parametric trigger is live** in the rider's zone during their shift window. At all other times, sensors are dormant — protecting battery life and privacy. The heartbeat ping lasts 10 seconds and runs silently in the background.

### 2. Catching Fraud Rings

Organised fraud — coordinated groups of riders staging inactivity to exploit triggers — is detected through three mechanisms:

**Zone Claim Density Monitoring:** An Isolation Forest anomaly detection model continuously tracks the ratio of claims to enrolled riders per zone per event. If a social disruption triggers claims from >70% of enrolled riders in a single zone on the same day, and no API-verified external event exists, the entire batch is flagged for human review. For weather events (where mass simultaneous claims are expected and the triggering API independently confirms the event), this threshold does not apply.

**Device & Identity Correlation:** Every RahatPay account is bound to exactly one Aadhaar/PAN and one physical device (fingerprinted via hardware serial, IMEI hash, and Android ID). Multiple accounts from one device, or one ID appearing across multiple accounts, triggers immediate account suspension. This makes it expensive for fraud rings to create fake identities at scale.

**Behavioural Pattern Analysis:** The baseline deviation model tracks each rider's activity consistency score. A rider who historically works every Tuesday suddenly going offline only on Tuesdays when rain is forecast — but working normally on dry Tuesdays — produces a statistical anomaly that is flagged. One-off deviations score low (everyone has off days); repeated patterns correlated with trigger events score high.

### 3. Protecting Honest Riders

Every anti-fraud mechanism has an explicit false-positive safeguard to ensure genuine riders are never punished:

**No silent rejections.** Every flagged claim produces a specific, plain-language explanation of exactly which check failed and what data was used. The rider sees this in-app immediately.

**Sensor fusion is corroborative, not dispositive.** A failed sensor check does not auto-reject a claim — it routes the claim to human review with a longer processing window. Only the combination of multiple failed layers leads to rejection, and even then, the rider retains a 7-day appeal right reviewed by a human compliance officer.

**Trust Score rewards consistency.** Riders with a high Trust Score (80+) bypass extended sensor checks entirely — their claims process at maximum speed. This incentivises honest behaviour over time rather than punishing riders who happen to trigger an edge case.

**Mass-event override.** During city-wide events (cyclone, flood) where thousands of riders are affected simultaneously, individual sensor fusion checks are relaxed and the system relies on the external API trigger as the primary verification. Fraud detection shifts to post-hoc statistical analysis rather than real-time blocking — ensuring no genuine rider is delayed during a crisis.

**DPDP Act 2023 compliance.** All biometric data (facial vectors from KYC) is stored as irreversible hashed feature vectors — raw images are deleted post-onboarding. Sensor data from heartbeat pings is retained for 7 days post-event for audit purposes, then permanently deleted. Individual rider data is never sold or shared externally.

---

## Trust Score System

Each rider maintains a dynamic Trust Score (0–100). Higher scores mean faster payouts and reduced verification friction.

| Dimension | Weight |
|---|---|
| Account age & tenure on RahatPay | 20% |
| Verification completeness (all KYC levels) | 20% |
| Claim history (approval rate) | 25% |
| Activity consistency (shift pattern alignment) | 20% |
| Platform tenure (Swiggy/Zomato) | 15% |

| Score | Effect |
|---|---|
| 80–100 | Instant payout on trigger validation |
| 50–79 | Standard processing with full sensor fusion |
| 20–49 | Extended review + additional manual checks |
| 0–19 | Claim held for compliance team review |

---

## Revenue Model

**Pillar 1 — Premium Margin.** At an average Suraksha premium of ₹72/week: ₹50 (70%) to loss reserve, ₹7 (10%) to operations, ₹15 (20%) net margin. Target loss ratio: 60–70%. At 100,000 enrolled riders, weekly net margin is ~₹15 lakhs.

**Pillar 2 — B2B2C Platform Partnerships.** Delivery platforms lose fulfillment during disruptions. RahatPay offers platforms a deal: subsidise ₹20/rider/week as a Partner Welfare Fee, rider pays the rest. Premiums auto-deducted from weekly platform settlement — zero collection friction.

**Pillar 3 — Anonymised Zone Analytics.** Aggregated data on which zones fail at what rainfall levels, at what times — valuable for logistics companies, city planners, and EV infrastructure firms. Individual rider data is never sold.

---

## Policy Terms & Rider Protections

**Premium lock:** Confirmed premium holds for a minimum of 4 weeks. Recalculations apply only at the next cycle boundary with 7 days advance notice.

**Day-1 coverage:** Provisional flat-rate coverage from enrollment using city-level median baseline.

**Transparent rejections:** Every denied claim gets a plain-language explanation stating which eligibility check failed and what data was used.

**Zone visibility:** Rider's top 3 covered zones always visible in-app, updated every 4 weeks with notification.

**Appeal right:** Every rejection can be appealed within 7 days for human review.

**Shift window integrity:** Derived from the rider's own rolling 4-week GPS and activity data — not self-reported.

**Strategic re-enrollment prevention:** A rider who cancels and re-enrolls after a gap >30 days undergoes a 5-day cooling-off period. Historical baseline data is retained.

---

## Exclusions

Explicitly excluded from all tiers: health/medical expenses, life insurance, accidental death, vehicle damage or repairs, disruptions outside established shift windows, events outside the rider's top 3 zones, periods where the rider was active on any delivery platform, and disruptions from war or armed conflict.

---

## Tech Stack

| Layer | Technology | Rationale |
|---|---|---|
| Mobile App | React Native (Android-first) | Target hardware is mid-range Android; sensor access for fraud prevention |
| Admin Dashboard | React.js | Insurer-facing analytics and claim review |
| Backend API | FastAPI (Python) | High-performance async; native ML integration via scikit-learn |
| Database | PostgreSQL | CHECK constraints enforce payout caps at schema level |
| Cache | Redis | Fast trigger state lookup and active session management |
| ML Models | XGBoost, Isolation Forest (scikit-learn) | Risk scoring, premium engine, anomaly detection |
| Weather/AQI | OpenWeatherMap API, CPCB AQI India API | Real-time parametric trigger monitoring |
| Training Data | IMD records, NDMA logs, CPCB archives, OWM Historical | 10+ years of zone-level risk data |
| Civic Alerts | NewsAPI (NLP entity extraction) + Govt gazette RSS | Multi-source civic disruption verification |
| Payments | Razorpay Test Mode | Simulated payout with per-transaction gateway ceiling |
| Auth | Firebase Auth | OTP-based mobile login |
| Hosting | AWS EC2 + S3 | Scalable cloud infrastructure |

---

## 6-Week Development Roadmap

### Phase 1 — Ideation & Foundation (Weeks 1–2) ✅

- Persona research: Zomato/Swiggy rider demographics, shift patterns, income distribution from published gig economy reports.
- Premium model: %-based formula with zone risk multiplier, seasonal factor, affordability guardrails.
- Trigger framework: 8 parametric triggers across environmental and social categories with fixed severity-to-rate mapping.
- Fraud architecture: 3-layer sensor fusion, adversarial defense strategy, Trust Score system.
- Repository structure established, README complete, 2-minute strategy video produced.

### Phase 2 — Automation & Protection (Weeks 3–4)

- **Onboarding flow:** Registration with platform Partner ID, Aadhaar/PAN verification (mock DigiLocker integration), tier selection UI.
- **AI Risk Engine v1:** XGBoost model trained on synthetic claims data (historical IMD events replayed against simulated rider populations). Zone risk multiplier generation for 50+ pin codes across Chennai, Mumbai, Bangalore, Delhi.
- **Rolling Baseline Profiler:** 4-week income/shift tracking module with city-median provisional fallback for new riders.
- **Trigger monitoring pipeline:** 3–5 live API integrations (OpenWeatherMap real-time, CPCB AQI, IMD RSS) + 2 mock triggers (civic disruption, extreme heat) running on a 60-second polling loop.
- **Claims pipeline:** 4-gate eligibility validator → payout calculator → three-layer safety enforcement → Razorpay test-mode disbursement.
- **Rider UI:** Coverage status dashboard, premium breakdown, zone map, payout history.

### Phase 3 — Scale & Optimise (Weeks 5–6)

- **Sensor fusion engine:** GPS × Cell Tower × Wi-Fi SSID × IMU verification, activated only during live trigger events. Tested against simulated spoofing scenarios.
- **Isolation Forest anomaly detection:** Zone-level claim density monitoring with configurable thresholds. Trained on synthetic collusion patterns.
- **Instant payout simulation:** Full Razorpay sandbox integration demonstrating end-to-end disruption → verification → UPI payout flow.
- **Intelligent dashboards:** Rider-facing (earnings protected, active coverage, Trust Score) and Admin-facing (loss ratios, zone risk heatmap, predictive next-week disruption probability).
- **Demo video (5 min):** Simulated rainstorm trigger → automated claim approval → payout confirmation walkthrough.
- **Final pitch deck:** Persona, AI architecture, fraud defense, business viability of the %-based weekly pricing model.

---

## Open Questions

1. **Trust Score calibration** — Dimension weights to be refined through simulated scenario testing in Phase 2.
2. **Collusion threshold** — The 70% zone claim density cap needs calibration against real mass-event patterns to avoid flagging genuine claims.
3. **Offline claim handling** — Grace-window mechanism for low-connectivity zones where heartbeat pings fail during disruptions. On-device log sync on reconnection under evaluation.
4. **New zone lag** — A rider starting in a new zone mid-cycle won't have it in their top 3 until the next recalculation. Edge case handling under discussion.

---

```
RahatPay/
├── README.md
├── backend/
│   ├── api/              # FastAPI routes
│   ├── models/           # XGBoost risk engine, Isolation Forest
│   ├── services/         # Trigger monitor, claim engine, payout validator
│   └── db/               # PostgreSQL schemas with CHECK constraints
├── mobile/src/           # React Native (rider-facing)
├── dashboard/src/        # React.js admin dashboard
├── data/training/        # IMD, NDMA, CPCB, NewsAPI historical datasets
├── docs/                 # Architecture diagrams, wireframes
└── scripts/seed_data/    # Mock rider and zone data
```

---

Admin Dashboard - [https://admin-dashboard-ui-liard.vercel.app/](https://admin-dashboard-ui-liard.vercel.app/)
Install Our app - [https://expo.dev/accounts/vanshien/projects/rahatpay/builds/94f640bb-7907-43e5-a8da-338556e8d173](https://expo.dev/accounts/vanshien/projects/rahatpay/builds/94f640bb-7907-43e5-a8da-338556e8d173)
*RahatPay — Because every delivery partner deserves a safety net.*
