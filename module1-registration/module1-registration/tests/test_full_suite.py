"""
tests/test_full_suite.py
-------------------------
Comprehensive QA test suite for the refactored RahatPay Module 1.

Covers:
  - Server startup & DB connectivity
  - Registration lifecycle (happy path + negative cases)
  - Policy creation, dashboard, payout history
  - Admin auth (no token, bad token, valid token)
  - Admin Worker management (list, get, block, kyc)
  - Admin Claims & Payouts
  - Admin Fraud Monitoring (structured JSON responses)
  - Admin Zone Management (list, toggle)
  - Admin Financial Analytics (no divide-by-zero, real math)
  - Admin System Config (GET + PATCH)
  - Module 2 integration (premium floor & cap)
  - Edge cases (very low income, high income, blocked user)
  - DB integrity (integer IDs, no UUID, check constraints)
  - Polygon validation (application-level notes)
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import text
from sqlalchemy.pool import NullPool

from main import app
from db.connection import get_db, Base
from config import settings, TIER_CONFIG

# ── Test DB ───────────────────────────────────────────────────────────────────

# Use same credentials as DATABASE_URL but a separate DB name (avoid replacing username).
TEST_DATABASE_URL = settings.DATABASE_URL.rsplit("/", 1)[0] + "/rahatpay_test"
test_engine = create_async_engine(
    TEST_DATABASE_URL, echo=False, poolclass=NullPool
)


def split_postgres_sql(sql: str) -> list[str]:
    """Split SQL into statements for asyncpg (respect --, /* */, ', dollar-quotes)."""
    out: list[str] = []
    chunk: list[str] = []
    i, n = 0, len(sql)

    def skip_line_comment() -> None:
        nonlocal i
        while i < n and sql[i] != "\n":
            i += 1

    def skip_block_comment() -> None:
        nonlocal i
        end = sql.find("*/", i + 2)
        i = n if end == -1 else end + 2

    while i < n:
        if sql[i : i + 2] == "--":
            skip_line_comment()
            continue
        if sql[i : i + 2] == "/*":
            skip_block_comment()
            continue
        if sql[i] == "'":
            chunk.append(sql[i])
            i += 1
            while i < n:
                chunk.append(sql[i])
                if sql[i] == "'":
                    i += 1
                    break
                i += 1
            continue
        if sql[i] == "$":
            start = i
            i += 1
            tag_start = i
            while i < n and sql[i] != "$":
                i += 1
            tag = sql[tag_start:i]
            if i >= n:
                chunk.extend(sql[start:])
                break
            i += 1
            close = f"${tag}$"
            endpos = sql.find(close, i)
            if endpos == -1:
                chunk.extend(sql[start:])
                break
            chunk.extend(sql[start : endpos + len(close)])
            i = endpos + len(close)
            continue
        if sql[i] == ";":
            stmt = "".join(chunk).strip()
            chunk = []
            if stmt:
                out.append(stmt)
            i += 1
            continue
        chunk.append(sql[i])
        i += 1
    tail = "".join(chunk).strip()
    if tail:
        out.append(tail)
    return out
TestSessionLocal = async_sessionmaker(
    bind=test_engine, class_=AsyncSession,
    expire_on_commit=False, autoflush=False
)


async def override_get_db():
    async with TestSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


app.dependency_overrides[get_db] = override_get_db

ADMIN_HEADERS = {"Authorization": "Bearer admin_token"}
BAD_HEADERS   = {"Authorization": "Bearer wrong_token"}


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture(scope="function", autouse=True)
async def setup_db():
    """Create clean schema + seed zones before each test."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        
        # Read and execute raw schema.sql for accurate constraint/trigger testing
        import os
        schema_path = os.path.join(os.path.dirname(__file__), "..", "db", "schema.sql")
        with open(schema_path, "r", encoding="utf-8") as f:
            schema_sql = f.read()

        for stmt in split_postgres_sql(schema_sql):
            await conn.execute(text(stmt))

        # Seed polygon-capable zones matching the new schema
        await conn.execute(text("""
            INSERT INTO zones (city, area_name, risk_multiplier, polygon) VALUES
            ('Chennai',   'George Town',  1.20, '[{"lat": 13.0827, "lng": 80.2707}, {"lat": 13.0850, "lng": 80.2750}, {"lat": 13.0800, "lng": 80.2780}]'),
            ('Chennai',   'Sowcarpet',    1.15, '[{"lat": 13.0897, "lng": 80.2787}, {"lat": 13.0950, "lng": 80.2850}, {"lat": 13.0850, "lng": 80.2880}]'),
            ('Chennai',   'Egmore',       1.10, '[{"lat": 13.0783, "lng": 80.2603}, {"lat": 13.0820, "lng": 80.2650}, {"lat": 13.0730, "lng": 80.2680}]'),
            ('Mumbai',    'Fort',         1.30, '[{"lat": 18.9322, "lng": 72.8315}, {"lat": 18.9400, "lng": 72.8350}, {"lat": 18.9250, "lng": 72.8400}]'),
            ('Bangalore', 'MG Road',      1.00, '[{"lat": 12.9716, "lng": 77.5946}, {"lat": 12.9800, "lng": 77.6000}, {"lat": 12.9650, "lng": 77.6050}]')
        """))

        # Fetch zone IDs so we can reference them in tests
        result = await conn.execute(text("SELECT zone_id, city FROM zones ORDER BY zone_id"))
        rows = result.fetchall()

    # Per-city zone_id lists (ORDER BY zone_id — do not collapse duplicates)
    global _zones_by_city
    _zones_by_city = {}
    for zid, city in rows:
        _zones_by_city.setdefault(city, []).append(zid)

    yield

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


_zones_by_city: dict[str, list[int]] = {}


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


def chennai_zone_id() -> int:
    return _zones_by_city.get("Chennai", [1])[0]

def chennai_zone2_id() -> int:
    z = _zones_by_city.get("Chennai", [1, 2])
    return z[1] if len(z) > 1 else z[0]

def mumbai_zone_id() -> int:
    return _zones_by_city.get("Mumbai", [4])[0]

def bangalore_zone_id() -> int:
    return _zones_by_city.get("Bangalore", [5])[0]


def base_payload(**overrides):
    """Default valid registration payload using integer zone IDs."""
    z1 = chennai_zone_id()
    z2 = chennai_zone2_id()
    payload = {
        "partner_id": "SWG-CHN-TEST001",
        "platform": "swiggy",
        "name": "Test Rider",
        "phone": "+919876543210",
        "kyc": {"type": "aadhaar", "value": "1234"},
        "city": "Chennai",
        "zone1_id": z1,
        "zone2_id": z2,
        "zone3_id": None,
        "tier": "kavach",
    }
    payload.update(overrides)
    return payload


@pytest_asyncio.fixture
async def registered_rider(client):
    """Returns (rider_id: int, policy_id: int) from successful registration."""
    z1 = chennai_zone_id()
    z2 = chennai_zone2_id()
    payload = {
        "partner_id": "SWG-CHN-FIXTURE001",
        "platform": "swiggy",
        "name": "Fixture Rider",
        "phone": "+919876540001",
        "kyc": {"type": "aadhaar", "value": "9999"},
        "city": "Chennai",
        "zone1_id": z1,
        "zone2_id": z2,
        "zone3_id": None,
        "tier": "suraksha",
    }
    resp = await client.post("/register", json=payload)
    assert resp.status_code == 201, f"Fixture registration failed: {resp.text}"
    data = resp.json()
    return data["rider_id"], data["policy_id"]


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — SERVER HEALTH
# ═══════════════════════════════════════════════════════════════════════════════

class TestServerHealth:

    @pytest.mark.asyncio
    async def test_health_endpoint(self, client):
        """Health check must return 200 and module identity."""
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["module"] == "module1-registration"
        assert "database" in data
        assert "version" in data

    @pytest.mark.asyncio
    async def test_root_endpoint(self, client):
        """Root must return module metadata and endpoint map."""
        resp = await client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert "endpoints" in data
        assert "admin" in data["endpoints"]

    @pytest.mark.asyncio
    async def test_docs_reachable(self, client):
        """OpenAPI docs should be available."""
        resp = await client.get("/docs")
        assert resp.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — REGISTRATION (Core Flow)
# ═══════════════════════════════════════════════════════════════════════════════

class TestRegistration:

    @pytest.mark.asyncio
    async def test_register_success_returns_integer_ids(self, client):
        """Happy path: IDs in response must be integers, not UUIDs."""
        resp = await client.post("/register", json=base_payload())
        assert resp.status_code == 201, resp.text
        data = resp.json()
        # CRITICAL: IDs must be integers
        assert isinstance(data["rider_id"], int), f"rider_id is not int: {type(data['rider_id'])}"
        assert isinstance(data["policy_id"], int), f"policy_id is not int: {type(data['policy_id'])}"
        assert data["rider_id"] > 0
        assert data["policy_id"] > 0

    @pytest.mark.asyncio
    async def test_register_policy_created_correctly(self, client):
        """Registration must create an active 4-week policy."""
        from datetime import date, timedelta
        resp = await client.post("/register", json=base_payload())
        assert resp.status_code == 201
        data = resp.json()
        assert data["tier"] == "kavach"
        assert data["weekly_premium"] >= 15.0
        assert data["weekly_payout_cap"] == TIER_CONFIG["kavach"]["weekly_payout_cap"]
        assert data["is_seasoning"] is True
        start = date.fromisoformat(data["cycle_start_date"])
        end   = date.fromisoformat(data["cycle_end_date"])
        assert (end - start).days == 28

    @pytest.mark.asyncio
    async def test_register_premium_breakdown_present(self, client):
        """Response must include all breakdown fields."""
        resp = await client.post("/register", json=base_payload())
        assert resp.status_code == 201
        bd = resp.json()["premium_breakdown"]
        for field in ["income", "tier_rate", "zone_risk", "seasonal_factor",
                      "raw_premium", "floor_applied", "cap_applied", "final_premium"]:
            assert field in bd, f"Missing breakdown field: {field}"

    @pytest.mark.asyncio
    async def test_register_duplicate_partner_id_returns_409(self, client):
        """Second call with same partner_id must return 409."""
        p = base_payload()
        r1 = await client.post("/register", json=p)
        assert r1.status_code == 201
        p2 = base_payload(phone="+919000000002")
        r2 = await client.post("/register", json=p2)
        assert r2.status_code == 409

    @pytest.mark.asyncio
    async def test_register_duplicate_phone_returns_409(self, client):
        """Same phone must be rejected."""
        r1 = await client.post("/register", json=base_payload())
        assert r1.status_code == 201
        r2 = await client.post("/register", json=base_payload(partner_id="SWG-CHN-TEST002"))
        assert r2.status_code == 409

    @pytest.mark.asyncio
    async def test_register_invalid_zone_id_returns_400(self, client):
        """Non-existent zone_id must return 400."""
        p = base_payload(zone1_id=99999)
        resp = await client.post("/register", json=p)
        assert resp.status_code == 400
        assert "zone" in resp.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_register_zone_city_mismatch_returns_400(self, client):
        """Using a Mumbai zone for a Chennai rider must fail."""
        p = base_payload(city="Chennai", zone1_id=mumbai_zone_id())
        resp = await client.post("/register", json=p)
        assert resp.status_code == 400
        assert "city" in resp.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_register_duplicate_zone_ids_returns_400(self, client):
        """Same zone_id in zone1 and zone2 must fail validation."""
        z = chennai_zone_id()
        p = base_payload(zone1_id=z, zone2_id=z)
        resp = await client.post("/register", json=p)
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_register_invalid_platform_returns_400(self, client):
        resp = await client.post("/register", json=base_payload(platform="uber"))
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_register_invalid_phone_returns_400(self, client):
        resp = await client.post("/register", json=base_payload(phone="12345"))
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_register_invalid_pan_format_returns_400(self, client):
        p = base_payload(kyc={"type": "pan", "value": "INVALID_PAN"})
        resp = await client.post("/register", json=p)
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_register_valid_pan_kyc(self, client):
        p = base_payload(
            partner_id="ZOM-CHN-PAN001",
            phone="+919000000099",
            kyc={"type": "pan", "value": "ABCDE1234F"},
        )
        resp = await client.post("/register", json=p)
        assert resp.status_code == 201

    @pytest.mark.asyncio
    async def test_register_missing_kyc_returns_400(self, client):
        p = base_payload()
        del p["kyc"]
        resp = await client.post("/register", json=p)
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_register_all_three_tiers(self, client):
        """All 3 tiers should register successfully."""
        for i, tier in enumerate(["kavach", "suraksha", "raksha"]):
            p = base_payload(
                partner_id=f"SWG-CHN-TIER{i}",
                phone=f"+9198765{i:05d}",
                tier=tier,
            )
            resp = await client.post("/register", json=p)
            assert resp.status_code == 201, f"Tier {tier} failed: {resp.text}"
            assert resp.json()["tier"] == tier
            assert resp.json()["weekly_premium"] >= 15.0

    @pytest.mark.asyncio
    async def test_register_zone1_required(self, client):
        """zone1_id is mandatory; omitting it must fail."""
        p = base_payload()
        del p["zone1_id"]
        resp = await client.post("/register", json=p)
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_register_invalid_tier_returns_400(self, client):
        resp = await client.post("/register", json=base_payload(tier="gold"))
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_register_negative_zone_id_returns_400(self, client):
        """Negative zone_id must be rejected."""
        p = base_payload(zone1_id=-1)
        resp = await client.post("/register", json=p)
        assert resp.status_code == 400


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — DASHBOARD & PAYOUT HISTORY
# ═══════════════════════════════════════════════════════════════════════════════

class TestDashboard:

    @pytest.mark.asyncio
    async def test_dashboard_returns_200(self, client, registered_rider):
        rider_id, _ = registered_rider
        resp = await client.get(f"/rider/{rider_id}/dashboard")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_dashboard_all_required_fields(self, client, registered_rider):
        rider_id, _ = registered_rider
        resp = await client.get(f"/rider/{rider_id}/dashboard")
        data = resp.json()
        for field in [
            "rider_id", "name", "tier", "platform", "city",
            "policy_id", "policy_status", "weekly_premium", "weekly_payout_cap",
            "premium_breakdown", "zones", "baseline_weekly_income",
            "baseline_weekly_hours", "baseline_hourly_rate", "is_seasoning",
            "already_paid_this_week", "remaining_headroom",
            "cycle_start_date", "cycle_end_date", "days_remaining", "trust_score",
        ]:
            assert field in data, f"Missing field: {field}"

    @pytest.mark.asyncio
    async def test_dashboard_returns_integer_ids(self, client, registered_rider):
        """Dashboard rider_id and policy_id must be integers."""
        rider_id, _ = registered_rider
        resp = await client.get(f"/rider/{rider_id}/dashboard")
        data = resp.json()
        assert isinstance(data["rider_id"], int)
        assert isinstance(data["policy_id"], int)

    @pytest.mark.asyncio
    async def test_dashboard_zones_include_polygon(self, client, registered_rider):
        """Zones in dashboard must include polygon data (new schema field)."""
        rider_id, _ = registered_rider
        resp = await client.get(f"/rider/{rider_id}/dashboard")
        zones = resp.json()["zones"]
        assert len(zones) >= 1
        for zone in zones:
            assert "zone_id" in zone, "zone_id missing from zone"
            assert "polygon" in zone, "polygon missing from zone (schema regression!)"
            assert "area_name" in zone
            assert "risk_multiplier" in zone
            assert isinstance(zone["zone_id"], int)
            # polygon must be a list (can be empty but should be a list)
            assert isinstance(zone["polygon"], list)

    @pytest.mark.asyncio
    async def test_dashboard_premium_values_match_tier(self, client, registered_rider):
        """Dashboard payout cap must match the suraksha tier config."""
        rider_id, _ = registered_rider
        resp = await client.get(f"/rider/{rider_id}/dashboard")
        data = resp.json()
        assert data["weekly_payout_cap"] == TIER_CONFIG["suraksha"]["weekly_payout_cap"]
        assert data["weekly_premium"] >= 15.0
        assert data["tier"] == "suraksha"

    @pytest.mark.asyncio
    async def test_dashboard_initial_headroom(self, client, registered_rider):
        """Before any claims, headroom == weekly_payout_cap."""
        rider_id, _ = registered_rider
        resp = await client.get(f"/rider/{rider_id}/dashboard")
        data = resp.json()
        assert data["already_paid_this_week"] == 0.0
        assert data["remaining_headroom"] == data["weekly_payout_cap"]

    @pytest.mark.asyncio
    async def test_dashboard_not_found_returns_404(self, client):
        resp = await client.get("/rider/999999/dashboard")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_dashboard_invalid_id_type_returns_400(self, client):
        """String ID (UUID format) should return 400 for integer route."""
        resp = await client.get("/rider/not-an-integer/dashboard")
        assert resp.status_code == 400


class TestPayoutHistory:

    @pytest.mark.asyncio
    async def test_payout_history_empty_for_new_rider(self, client, registered_rider):
        rider_id, _ = registered_rider
        resp = await client.get(f"/rider/{rider_id}/payouts")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_claims"] == 0
        assert data["total_paid"] == 0.0
        assert data["claims"] == []

    @pytest.mark.asyncio
    async def test_payout_history_structure(self, client, registered_rider):
        rider_id, _ = registered_rider
        resp = await client.get(f"/rider/{rider_id}/payouts")
        assert resp.status_code == 200
        data = resp.json()
        for field in ["rider_id", "total_paid", "total_claims",
                      "approved_claims", "rejected_claims", "claims"]:
            assert field in data

    @pytest.mark.asyncio
    async def test_payout_history_rider_id_is_integer(self, client, registered_rider):
        rider_id, _ = registered_rider
        resp = await client.get(f"/rider/{rider_id}/payouts")
        data = resp.json()
        assert isinstance(data["rider_id"], int)

    @pytest.mark.asyncio
    async def test_payout_history_not_found(self, client):
        resp = await client.get("/rider/999999/payouts")
        assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 4 — ZONES & TIERS
# ═══════════════════════════════════════════════════════════════════════════════

class TestZonesAndTiers:

    @pytest.mark.asyncio
    async def test_get_all_zones(self, client):
        resp = await client.get("/zones")
        assert resp.status_code == 200
        zones = resp.json()
        assert len(zones) >= 5

    @pytest.mark.asyncio
    async def test_zones_include_zone_id_not_pincode(self, client):
        """Zones must have zone_id (integer), not the old pincode field."""
        resp = await client.get("/zones")
        assert resp.status_code == 200
        for zone in resp.json():
            assert "zone_id" in zone, "zone_id missing — old pincode schema may still be in use"
            assert "pincode" not in zone, "pincode field should be gone from zone schema"
            assert isinstance(zone["zone_id"], int)

    @pytest.mark.asyncio
    async def test_zones_include_polygon(self, client):
        """Polygon must be returned in zone response."""
        resp = await client.get("/zones")
        for zone in resp.json():
            assert "polygon" in zone, "polygon missing from zone response"
            assert isinstance(zone["polygon"], list)

    @pytest.mark.asyncio
    async def test_get_zones_by_city(self, client):
        resp = await client.get("/zones?city=Chennai")
        assert resp.status_code == 200
        zones = resp.json()
        assert all(z["city"] == "Chennai" for z in zones)
        assert len(zones) == 3

    @pytest.mark.asyncio
    async def test_get_zones_unknown_city_returns_404(self, client):
        resp = await client.get("/zones?city=Atlantis")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_tiers(self, client):
        resp = await client.get("/tiers")
        assert resp.status_code == 200
        tiers = resp.json()
        tier_names = {t["name"].lower() for t in tiers}
        assert {"kavach", "suraksha", "raksha"} == tier_names

    @pytest.mark.asyncio
    async def test_tiers_have_required_fields(self, client):
        resp = await client.get("/tiers")
        for t in resp.json():
            assert "tier_rate" in t
            assert "weekly_payout_cap" in t
            assert "coverage_triggers" in t
            assert t["premium_floor"] == 15.0


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 5 — POLICY LIFECYCLE (Tier Change + Renewal)
# ═══════════════════════════════════════════════════════════════════════════════

class TestPolicyLifecycle:

    @pytest.mark.asyncio
    async def test_tier_change_blocked_mid_cycle(self, client, registered_rider):
        rider_id, _ = registered_rider
        resp = await client.post(f"/rider/{rider_id}/change-tier", json={"new_tier": "raksha"})
        assert resp.status_code == 409
        assert "mid-cycle" in resp.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_tier_change_same_tier_returns_400(self, client, registered_rider):
        rider_id, _ = registered_rider
        resp = await client.post(f"/rider/{rider_id}/change-tier", json={"new_tier": "suraksha"})
        assert resp.status_code == 400
        assert "already" in resp.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_tier_change_invalid_tier_returns_400(self, client, registered_rider):
        rider_id, _ = registered_rider
        resp = await client.post(f"/rider/{rider_id}/change-tier", json={"new_tier": "platinum"})
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_renewal_blocked_if_active_policy(self, client, registered_rider):
        rider_id, _ = registered_rider
        resp = await client.post(f"/rider/{rider_id}/renew")
        assert resp.status_code == 409
        assert "active policy" in resp.json()["detail"].lower()


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 6 — ADMIN AUTHENTICATION
# ═══════════════════════════════════════════════════════════════════════════════

class TestAdminAuth:

    @pytest.mark.asyncio
    async def test_no_token_returns_403(self, client):
        """No auth header → 403."""
        resp = await client.get("/admin/workers")
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_wrong_token_returns_403(self, client):
        """Wrong bearer token → 403."""
        resp = await client.get("/admin/workers", headers=BAD_HEADERS)
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_valid_token_returns_200(self, client):
        """Correct admin token → 200."""
        resp = await client.get("/admin/workers", headers=ADMIN_HEADERS)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_fraud_endpoint_requires_auth(self, client):
        resp = await client.get("/admin/fraud/flagged")
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_analytics_endpoint_requires_auth(self, client):
        resp = await client.get("/admin/analytics/financial")
        assert resp.status_code == 403


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 7 — ADMIN WORKER MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════════

class TestAdminWorkers:

    @pytest.mark.asyncio
    async def test_list_workers_empty(self, client):
        """With no riders, list should be empty."""
        resp = await client.get("/admin/workers", headers=ADMIN_HEADERS)
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_list_workers_after_registration(self, client, registered_rider):
        resp = await client.get("/admin/workers", headers=ADMIN_HEADERS)
        assert resp.status_code == 200
        workers = resp.json()
        assert len(workers) == 1
        w = workers[0]
        # IDs must be integers
        assert isinstance(w["id"], int)
        assert "partner_id" in w
        assert "is_blocked" in w
        assert "kyc_verified" in w

    @pytest.mark.asyncio
    async def test_list_workers_filter_by_platform(self, client, registered_rider):
        resp = await client.get("/admin/workers?platform=swiggy", headers=ADMIN_HEADERS)
        assert resp.status_code == 200
        for w in resp.json():
            assert w["platform"] == "swiggy"

    @pytest.mark.asyncio
    async def test_list_workers_filter_by_tier(self, client, registered_rider):
        resp = await client.get("/admin/workers?tier=suraksha", headers=ADMIN_HEADERS)
        assert resp.status_code == 200
        for w in resp.json():
            assert w["tier"] == "suraksha"

    @pytest.mark.asyncio
    async def test_list_workers_filter_by_zone_id(self, client, registered_rider):
        rider_id, _ = registered_rider
        z1 = (await client.get(f"/admin/workers/{rider_id}", headers=ADMIN_HEADERS)).json()["zone1_id"]
        resp = await client.get(f"/admin/workers?zone_id={z1}", headers=ADMIN_HEADERS)
        assert resp.status_code == 200
        for w in resp.json():
            assert w["zone1_id"] == z1

    @pytest.mark.asyncio
    async def test_get_single_worker(self, client, registered_rider):
        rider_id, _ = registered_rider
        resp = await client.get(f"/admin/workers/{rider_id}", headers=ADMIN_HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == rider_id
        assert "active_policy" in data

    @pytest.mark.asyncio
    async def test_get_nonexistent_worker_returns_404(self, client):
        resp = await client.get("/admin/workers/999999", headers=ADMIN_HEADERS)
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_block_worker(self, client, registered_rider):
        rider_id, _ = registered_rider
        resp = await client.patch(
            f"/admin/workers/{rider_id}/block",
            json={"is_blocked": True},
            headers=ADMIN_HEADERS
        )
        assert resp.status_code == 200
        # Verify state persisted
        get_resp = await client.get(f"/admin/workers/{rider_id}", headers=ADMIN_HEADERS)
        assert get_resp.json()["is_blocked"] is True

    @pytest.mark.asyncio
    async def test_unblock_worker(self, client, registered_rider):
        rider_id, _ = registered_rider
        # Block first
        await client.patch(f"/admin/workers/{rider_id}/block", json={"is_blocked": True}, headers=ADMIN_HEADERS)
        # Then unblock
        resp = await client.patch(
            f"/admin/workers/{rider_id}/block",
            json={"is_blocked": False},
            headers=ADMIN_HEADERS
        )
        assert resp.status_code == 200
        get_resp = await client.get(f"/admin/workers/{rider_id}", headers=ADMIN_HEADERS)
        assert get_resp.json()["is_blocked"] is False

    @pytest.mark.asyncio
    async def test_verify_kyc(self, client, registered_rider):
        rider_id, _ = registered_rider
        resp = await client.patch(
            f"/admin/workers/{rider_id}/verify-kyc",
            headers=ADMIN_HEADERS
        )
        assert resp.status_code == 200
        get_resp = await client.get(f"/admin/workers/{rider_id}", headers=ADMIN_HEADERS)
        assert get_resp.json()["kyc_verified"] is True

    @pytest.mark.asyncio
    async def test_block_nonexistent_worker_returns_404(self, client):
        resp = await client.patch(
            "/admin/workers/999999/block",
            json={"is_blocked": True},
            headers=ADMIN_HEADERS
        )
        assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 8 — ADMIN CLAIMS & PAYOUTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestAdminClaims:

    @pytest.mark.asyncio
    async def test_live_claims_empty(self, client):
        resp = await client.get("/admin/claims/live", headers=ADMIN_HEADERS)
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_get_rider_claims_empty(self, client, registered_rider):
        rider_id, _ = registered_rider
        resp = await client.get(f"/admin/claims/{rider_id}", headers=ADMIN_HEADERS)
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_get_all_payouts_empty(self, client):
        resp = await client.get("/admin/payouts", headers=ADMIN_HEADERS)
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_override_claim_nonexistent_returns_404(self, client):
        resp = await client.patch(
            "/admin/claims/999999/override",
            json={"status": "approved"},
            headers=ADMIN_HEADERS
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_override_claim_invalid_status_returns_400(self, client):
        """Bad status value must return 400, not 500."""
        resp = await client.patch(
            "/admin/claims/1/override",
            json={"status": "HACKED"},
            headers=ADMIN_HEADERS
        )
        assert resp.status_code == 400


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 9 — ADMIN FRAUD MONITORING
# ═══════════════════════════════════════════════════════════════════════════════

class TestAdminFraud:

    @pytest.mark.asyncio
    async def test_fraud_flagged_structured_response(self, client):
        """Must return structured JSON, not placeholder text."""
        resp = await client.get("/admin/fraud/flagged", headers=ADMIN_HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert "flagged_users" in data
        users = data["flagged_users"]
        assert isinstance(users, list)
        for user in users:
            assert "rider_id" in user
            assert "risk_score" in user
            assert "reason" in user
            assert "flagged_at" in user
            # Must not be a generic placeholder
            assert user["reason"] != "placeholder"
            assert 0.0 <= user["risk_score"] <= 1.0

    @pytest.mark.asyncio
    async def test_zone_anomalies_structured(self, client):
        resp = await client.get("/admin/fraud/zone-anomalies", headers=ADMIN_HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert "anomalous_zones" in data
        for az in data["anomalous_zones"]:
            assert "zone_id" in az
            assert "anomaly_type" in az
            assert "severity" in az

    @pytest.mark.asyncio
    async def test_fraud_referrals_structured(self, client):
        resp = await client.get("/admin/fraud/referrals", headers=ADMIN_HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert "suspicious_referral_clusters" in data

    @pytest.mark.asyncio
    async def test_fraud_collusion_structured(self, client):
        resp = await client.get("/admin/fraud/collusion", headers=ADMIN_HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert "collusion_rings" in data


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 10 — ADMIN ZONE MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════════

class TestAdminZones:

    @pytest.mark.asyncio
    async def test_admin_list_zones(self, client):
        resp = await client.get("/admin/zones", headers=ADMIN_HEADERS)
        assert resp.status_code == 200
        zones = resp.json()
        assert len(zones) >= 5
        for z in zones:
            assert "zone_id" in z
            assert "polygon" in z
            assert "is_active" in z
            assert "registration_cap" in z

    @pytest.mark.asyncio
    async def test_toggle_zone_off(self, client):
        """Disable a zone and verify state change."""
        # Get first zone
        zones = (await client.get("/admin/zones", headers=ADMIN_HEADERS)).json()
        zone_id = zones[0]["zone_id"]

        resp = await client.patch(
            f"/admin/zones/{zone_id}/toggle",
            json={"is_active": False},
            headers=ADMIN_HEADERS
        )
        assert resp.status_code == 200

        # Verify
        zones_after = (await client.get("/admin/zones", headers=ADMIN_HEADERS)).json()
        zone_after = next(z for z in zones_after if z["zone_id"] == zone_id)
        assert zone_after["is_active"] is False

    @pytest.mark.asyncio
    async def test_toggle_zone_on(self, client):
        """Re-enable a zone."""
        zones = (await client.get("/admin/zones", headers=ADMIN_HEADERS)).json()
        zone_id = zones[0]["zone_id"]

        # Disable then re-enable
        await client.patch(f"/admin/zones/{zone_id}/toggle", json={"is_active": False}, headers=ADMIN_HEADERS)
        resp = await client.patch(f"/admin/zones/{zone_id}/toggle", json={"is_active": True}, headers=ADMIN_HEADERS)
        assert resp.status_code == 200

        zones_after = (await client.get("/admin/zones", headers=ADMIN_HEADERS)).json()
        zone_after = next(z for z in zones_after if z["zone_id"] == zone_id)
        assert zone_after["is_active"] is True

    @pytest.mark.asyncio
    async def test_toggle_nonexistent_zone_returns_404(self, client):
        resp = await client.patch(
            "/admin/zones/999999/toggle",
            json={"is_active": False},
            headers=ADMIN_HEADERS
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_zone_events_empty(self, client):
        """GET /admin/zones/{id}/events with no events = empty list."""
        zones = (await client.get("/admin/zones", headers=ADMIN_HEADERS)).json()
        zone_id = zones[0]["zone_id"]
        resp = await client.get(f"/admin/zones/{zone_id}/events", headers=ADMIN_HEADERS)
        assert resp.status_code == 200
        assert resp.json() == []


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 11 — ADMIN FINANCIAL ANALYTICS
# ═══════════════════════════════════════════════════════════════════════════════

class TestAdminFinancialAnalytics:

    @pytest.mark.asyncio
    async def test_financial_analytics_structure(self, client):
        resp = await client.get("/admin/analytics/financial", headers=ADMIN_HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        for field in ["total_premiums", "total_payouts", "loss_ratio",
                      "total_liability", "payout_cap_utilization", "churn_rate"]:
            assert field in data, f"Missing field: {field}"

    @pytest.mark.asyncio
    async def test_financial_analytics_no_divide_by_zero_empty_db(self, client):
        """With empty DB (no riders, no policies), must not 500."""
        resp = await client.get("/admin/analytics/financial", headers=ADMIN_HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        # All should be 0.0 safely
        assert data["loss_ratio"] == 0.0
        assert data["payout_cap_utilization"] == 0.0

    @pytest.mark.asyncio
    async def test_financial_analytics_with_registered_rider(self, client, registered_rider):
        """After a registration, premiums should be > 0."""
        resp = await client.get("/admin/analytics/financial", headers=ADMIN_HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_premiums"] >= 15.0, "Premium must be at least ₹15 (floor)"
        # Total payouts should still be 0 (no actual payouts yet)
        assert data["total_payouts"] == 0.0
        # Loss ratio = payouts/premiums = 0
        assert data["loss_ratio"] == 0.0

    @pytest.mark.asyncio
    async def test_financial_analytics_churn_rate_range(self, client, registered_rider):
        """Churn rate must always be between 0 and 1."""
        resp = await client.get("/admin/analytics/financial", headers=ADMIN_HEADERS)
        data = resp.json()
        assert 0.0 <= data["churn_rate"] <= 1.0

    @pytest.mark.asyncio
    async def test_financial_analytics_loss_ratio_range(self, client, registered_rider):
        """Loss ratio must always be >= 0 and not negative."""
        resp = await client.get("/admin/analytics/financial", headers=ADMIN_HEADERS)
        data = resp.json()
        assert data["loss_ratio"] >= 0.0


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 12 — ADMIN SYSTEM CONFIG
# ═══════════════════════════════════════════════════════════════════════════════

class TestAdminConfig:

    @pytest.mark.asyncio
    async def test_get_config_structure(self, client):
        resp = await client.get("/admin/config", headers=ADMIN_HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert "tier_parameters" in data
        assert "fraud_thresholds" in data
        assert "batch_job_status" in data

    @pytest.mark.asyncio
    async def test_get_config_tiers_present(self, client):
        resp = await client.get("/admin/config", headers=ADMIN_HEADERS)
        tier_params = resp.json()["tier_parameters"]
        assert "kavach" in tier_params
        assert "suraksha" in tier_params
        assert "raksha" in tier_params

    @pytest.mark.asyncio
    async def test_patch_config_accepts_updates(self, client):
        """PATCH /admin/config must accept fraud threshold updates."""
        payload = {
            "fraud_thresholds": {"high_claim_frequency": 5},
            "update_message": "Updated for test"
        }
        resp = await client.patch("/admin/config", json=payload, headers=ADMIN_HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert data["fraud_thresholds"]["high_claim_frequency"] == 5

    @pytest.mark.asyncio
    async def test_patch_config_empty_body_ok(self, client):
        """PATCH with no body should not crash."""
        resp = await client.patch("/admin/config", json={}, headers=ADMIN_HEADERS)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_patch_config_persists_for_get(self, client, monkeypatch, tmp_path):
        from routes import admin as admin_mod

        monkeypatch.setattr(admin_mod, "_RUNTIME_CONFIG_PATH", tmp_path / "admin_cfg.json")
        await client.patch(
            "/admin/config",
            json={"fraud_thresholds": {"high_claim_frequency": 77}},
            headers=ADMIN_HEADERS,
        )
        get_r = await client.get("/admin/config", headers=ADMIN_HEADERS)
        assert get_r.status_code == 200
        assert get_r.json()["fraud_thresholds"]["high_claim_frequency"] == 77


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 13 — MODULE 2 PREMIUM CALCULATION (Edge Cases)
# ═══════════════════════════════════════════════════════════════════════════════

class TestModule2Integration:

    @pytest.mark.asyncio
    async def test_premium_floor_applied_for_low_income(self, client):
        """
        Seasoning riders get city median income.
        Premium = income × tier_rate × zone_risk × seasonal_factor.
        For kavach (1.5%) on Chennai (~₹3500) = ~₹63 typically.
        But the ₹15 floor must be the minimum in all cases.
        """
        p = base_payload(tier="kavach")
        resp = await client.post("/register", json=p)
        assert resp.status_code == 201
        assert resp.json()["weekly_premium"] >= 15.0
        assert resp.json()["premium_breakdown"]["final_premium"] >= 15.0

    @pytest.mark.asyncio
    async def test_premium_cap_not_exceeded(self, client):
        """
        Premium must not exceed 3.5% of baseline income.
        With Chennai median (~₹3500), cap = ₹122.50.
        """
        p = base_payload(tier="raksha")
        resp = await client.post("/register", json=p)
        assert resp.status_code == 201
        data = resp.json()
        bd = data["premium_breakdown"]
        # If cap was applied, final_premium <= 3.5% of income
        if bd.get("cap_applied"):
            assert bd["final_premium"] <= bd["income"] * 0.035 + 0.01  # small float tolerance

    @pytest.mark.asyncio
    async def test_premium_breakdown_math_consistent(self, client):
        """final_premium in breakdown must match weekly_premium returned."""
        resp = await client.post("/register", json=base_payload())
        assert resp.status_code == 201
        data = resp.json()
        assert abs(data["weekly_premium"] - data["premium_breakdown"]["final_premium"]) < 0.01

    @pytest.mark.asyncio
    async def test_premium_positive_always(self, client):
        """Premium can never be 0 or negative."""
        for tier in ["kavach", "suraksha", "raksha"]:
            p = base_payload(
                partner_id=f"TEST-{tier.upper()}",
                phone=f"+919000{tier.__hash__() % 100000:05d}",
                tier=tier
            )
            resp = await client.post("/register", json=p)
            if resp.status_code == 201:
                assert resp.json()["weekly_premium"] > 0


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 14 — DATABASE INTEGRITY CHECKS
# ═══════════════════════════════════════════════════════════════════════════════

class TestDatabaseIntegrity:

    @pytest.mark.asyncio
    async def test_rider_id_is_sequential_integer(self, client):
        """Multiple registrations should produce sequential integer IDs."""
        ids = []
        for i in range(3):
            p = base_payload(
                partner_id=f"SEQ-TEST-{i:03d}",
                phone=f"+9190000{i:05d}",
            )
            resp = await client.post("/register", json=p)
            assert resp.status_code == 201
            ids.append(resp.json()["rider_id"])

        # All IDs must be unique integers
        assert len(set(ids)) == 3
        for id_ in ids:
            assert isinstance(id_, int)
            assert id_ > 0

        # IDs should be monotonically increasing (sequential identity)
        assert ids == sorted(ids)

    @pytest.mark.asyncio
    async def test_no_uuid_format_in_response(self, client):
        """No response field should look like a UUID (xxxxxxxx-xxxx-...)."""
        import re
        uuid_pattern = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.I)

        resp = await client.post("/register", json=base_payload())
        assert resp.status_code == 201
        data = resp.json()
        for key in ["rider_id", "policy_id"]:
            assert not uuid_pattern.match(str(data[key])), \
                f"{key} looks like a UUID: {data[key]}"

    @pytest.mark.asyncio
    async def test_zone_response_contains_integer_ids(self, client):
        """Zones endpoint must return integer zone_id, not string pincode."""
        resp = await client.get("/zones")
        for zone in resp.json():
            assert isinstance(zone["zone_id"], int)
            assert "pincode" not in zone

    @pytest.mark.asyncio
    async def test_foreign_key_consistency(self, client, registered_rider):
        """policy.rider_id must match the registered rider's id."""
        rider_id, policy_id = registered_rider
        resp = await client.get(f"/rider/{rider_id}/dashboard")
        data = resp.json()
        assert data["rider_id"] == rider_id
        assert data["policy_id"] == policy_id

    @pytest.mark.asyncio
    async def test_premium_check_constraint_floor(self, client):
        """Premium must always be >= 15 (enforced at both app + DB level)."""
        resp = await client.post("/register", json=base_payload(tier="kavach"))
        assert resp.status_code == 201
        assert resp.json()["weekly_premium"] >= 15.0
