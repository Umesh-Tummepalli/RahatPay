"""
tests/test_policy.py
---------------------
Tests for policy endpoints:
  - Dashboard correctness
  - Payout history
  - Tier change rules (mid-cycle block)
  - Policy renewal
  - Zones and tiers endpoints
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import text

from main import app
from db.connection import get_db, Base
from config import settings, TIER_CONFIG

TEST_DATABASE_URL = settings.DATABASE_URL.replace("/rahatpay", "/rahatpay_test")
test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
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


@pytest_asyncio.fixture(scope="function", autouse=True)
async def setup_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(text("""
            INSERT INTO zones (pincode, city, area_name, risk_multiplier) VALUES
            ('600001', 'Chennai',   'George Town',  1.20),
            ('600002', 'Chennai',   'Sowcarpet',    1.15),
            ('600010', 'Chennai',   'Egmore',       1.10),
            ('400001', 'Mumbai',    'Fort',         1.30)
            ON CONFLICT (pincode) DO NOTHING
        """))
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


# ── Fixture: registered rider ─────────────────────────────────────────────────

@pytest_asyncio.fixture
async def registered_rider(client):
    """Returns (rider_id, policy_id) from a successful registration."""
    payload = {
        "partner_id": "SWG-CHN-POLICY001",
        "platform": "swiggy",
        "name": "Policy Test Rider",
        "phone": "+919876543211",
        "kyc": {"type": "aadhaar", "value": "9999"},
        "city": "Chennai",
        "zone1_pincode": "600001",
        "zone2_pincode": "600002",
        "zone3_pincode": None,
        "tier": "suraksha",
    }
    resp = await client.post("/register", json=payload)
    assert resp.status_code == 201, resp.text
    data = resp.json()
    return data["rider_id"], data["policy_id"]


# ── Dashboard tests ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_dashboard_structure(client, registered_rider):
    """Dashboard must return all required fields."""
    rider_id, _ = registered_rider
    resp = await client.get(f"/rider/{rider_id}/dashboard")
    assert resp.status_code == 200, resp.text
    data = resp.json()

    required_fields = [
        "rider_id", "name", "tier", "policy_id", "policy_status",
        "weekly_premium", "weekly_payout_cap", "premium_breakdown",
        "zones", "baseline_weekly_income", "baseline_weekly_hours",
        "baseline_hourly_rate", "is_seasoning",
        "already_paid_this_week", "remaining_headroom",
        "cycle_start_date", "cycle_end_date", "days_remaining", "trust_score",
    ]
    for field in required_fields:
        assert field in data, f"Missing field: {field}"


@pytest.mark.asyncio
async def test_dashboard_premium_values(client, registered_rider):
    """Dashboard must return correct premium and payout cap for tier."""
    rider_id, _ = registered_rider
    resp = await client.get(f"/rider/{rider_id}/dashboard")
    assert resp.status_code == 200
    data = resp.json()

    # Suraksha cap is ₹3000
    assert data["weekly_payout_cap"] == TIER_CONFIG["suraksha"]["weekly_payout_cap"]
    assert data["weekly_premium"] >= 15.0
    assert data["tier"] == "suraksha"


@pytest.mark.asyncio
async def test_dashboard_zones_present(client, registered_rider):
    """Dashboard zones must include area_name and risk_multiplier."""
    rider_id, _ = registered_rider
    resp = await client.get(f"/rider/{rider_id}/dashboard")
    assert resp.status_code == 200
    zones = resp.json()["zones"]
    assert len(zones) >= 1
    for zone in zones:
        assert "pincode" in zone
        assert "area_name" in zone
        assert "risk_multiplier" in zone


@pytest.mark.asyncio
async def test_dashboard_remaining_headroom_initial(client, registered_rider):
    """Before any claims, remaining_headroom == weekly_payout_cap."""
    rider_id, _ = registered_rider
    resp = await client.get(f"/rider/{rider_id}/dashboard")
    assert resp.status_code == 200
    data = resp.json()
    assert data["already_paid_this_week"] == 0.0
    assert data["remaining_headroom"] == data["weekly_payout_cap"]


@pytest.mark.asyncio
async def test_dashboard_not_found(client):
    """Non-existent rider should return 404."""
    resp = await client.get("/rider/00000000-0000-0000-0000-000000000000/dashboard")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_dashboard_invalid_uuid(client):
    """Invalid UUID format should return 422."""
    resp = await client.get("/rider/not-a-uuid/dashboard")
    assert resp.status_code in (404, 422)


# ── Payout history tests ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_payout_history_empty(client, registered_rider):
    """New rider should have empty payout history."""
    rider_id, _ = registered_rider
    resp = await client.get(f"/rider/{rider_id}/payouts")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_claims"] == 0
    assert data["total_paid"] == 0.0
    assert data["claims"] == []


@pytest.mark.asyncio
async def test_payout_history_structure(client, registered_rider):
    """Payout history response must have all aggregate fields."""
    rider_id, _ = registered_rider
    resp = await client.get(f"/rider/{rider_id}/payouts")
    assert resp.status_code == 200
    data = resp.json()
    for field in ["rider_id", "total_paid", "total_claims", "approved_claims", "rejected_claims", "claims"]:
        assert field in data


# ── Zones endpoint ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_zones_all(client):
    """GET /zones should return all seeded zones."""
    resp = await client.get("/zones")
    assert resp.status_code == 200
    zones = resp.json()
    assert len(zones) >= 4


@pytest.mark.asyncio
async def test_get_zones_by_city(client):
    """Filter by city should return only that city's zones."""
    resp = await client.get("/zones?city=Chennai")
    assert resp.status_code == 200
    zones = resp.json()
    assert all(z["city"] == "Chennai" for z in zones)
    assert len(zones) == 3  # George Town, Sowcarpet, Egmore


@pytest.mark.asyncio
async def test_get_zones_unknown_city(client):
    """Unknown city should return 404."""
    resp = await client.get("/zones?city=Atlantis")
    assert resp.status_code == 404


# ── Tiers endpoint ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_tiers(client):
    """GET /tiers must return all 3 tiers with rates and caps."""
    resp = await client.get("/tiers")
    assert resp.status_code == 200
    tiers = resp.json()
    tier_names = {t["name"].lower() for t in tiers}
    assert {"kavach", "suraksha", "raksha"} == tier_names


@pytest.mark.asyncio
async def test_tiers_have_required_fields(client):
    """Each tier must have rate, cap, and coverage info."""
    resp = await client.get("/tiers")
    assert resp.status_code == 200
    for tier in resp.json():
        assert "tier_rate" in tier
        assert "weekly_payout_cap" in tier
        assert "coverage_triggers" in tier
        assert tier["premium_floor"] == 15.0


# ── Tier change tests ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_tier_change_blocked_mid_cycle(client, registered_rider):
    """Tier change must be rejected while active policy is running."""
    rider_id, _ = registered_rider
    resp = await client.post(f"/rider/{rider_id}/change-tier", json={"new_tier": "raksha"})
    # Must be 409 — cannot change mid-cycle
    assert resp.status_code == 409
    assert "mid-cycle" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_tier_change_same_tier(client, registered_rider):
    """Changing to the same tier should return 400."""
    rider_id, _ = registered_rider
    resp = await client.post(f"/rider/{rider_id}/change-tier", json={"new_tier": "suraksha"})
    assert resp.status_code == 400
    assert "already" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_tier_change_invalid_tier(client, registered_rider):
    """Invalid tier name should return 400."""
    rider_id, _ = registered_rider
    resp = await client.post(f"/rider/{rider_id}/change-tier", json={"new_tier": "platinum"})
    assert resp.status_code == 400


# ── Policy renewal tests ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_renewal_blocked_if_active(client, registered_rider):
    """Renewal should be rejected if there is already an active policy."""
    rider_id, _ = registered_rider
    resp = await client.post(f"/rider/{rider_id}/renew")
    assert resp.status_code == 409
    assert "active policy" in resp.json()["detail"].lower()


# ── Health check ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_health_check(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["module"] == "module1-registration"
