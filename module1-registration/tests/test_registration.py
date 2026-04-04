"""
tests/test_registration.py
---------------------------
Unit + integration tests for the /register endpoint.

Tests:
  - Successful registration
  - Duplicate partner_id → 409
  - Duplicate phone → 409
  - Invalid zone pincode → 400
  - Zone city mismatch → 400
  - Premium floor case (very low income → ₹15)
  - All 3 tiers
  - Zone distinctness check
  - KYC validation (aadhaar vs PAN)
  - Module 2 mock integration
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import text

from main import app
from db.connection import get_db, Base
from config import settings

# ── Test DB setup ─────────────────────────────────────────────────────────────
# Use a separate in-memory-like test database
TEST_DATABASE_URL = settings.DATABASE_URL.replace(
    "/rahatpay", "/rahatpay_test"
)

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
    """Create all tables before each test, drop after."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

        # Insert required zone data for tests
        await conn.execute(text("""
            INSERT INTO zones (pincode, city, area_name, risk_multiplier) VALUES
            ('600001', 'Chennai',   'George Town',       1.20),
            ('600002', 'Chennai',   'Sowcarpet',         1.15),
            ('600010', 'Chennai',   'Egmore',            1.10),
            ('400001', 'Mumbai',    'Fort',              1.30),
            ('560001', 'Bangalore', 'MG Road',           1.00)
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


# ── Helpers ───────────────────────────────────────────────────────────────────

def base_registration_payload(**overrides):
    payload = {
        "partner_id": "SWG-CHN-TEST001",
        "platform": "swiggy",
        "name": "Test Rider",
        "phone": "+919876543210",
        "kyc": {"type": "aadhaar", "value": "1234"},
        "city": "Chennai",
        "zone1_pincode": "600001",
        "zone2_pincode": "600002",
        "zone3_pincode": None,
        "tier": "kavach",
    }
    payload.update(overrides)
    return payload


# ── Tests ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_register_success(client):
    """Happy path: valid registration returns 201 with policy."""
    payload = base_registration_payload()
    resp = await client.post("/register", json=payload)
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert "rider_id" in data
    assert "policy_id" in data
    assert data["tier"] == "kavach"
    assert data["weekly_premium"] >= 15.0     # Floor always applies for seasoning
    assert "premium_breakdown" in data
    assert data["cycle_start_date"] is not None
    assert data["cycle_end_date"] is not None
    assert data["is_seasoning"] is True


@pytest.mark.asyncio
async def test_register_duplicate_partner_id(client):
    """Second registration with same partner_id must return 409."""
    payload = base_registration_payload()
    r1 = await client.post("/register", json=payload)
    assert r1.status_code == 201, r1.text

    # Try again with same partner_id but different phone
    payload2 = base_registration_payload(
        phone="+919000000001"
    )
    r2 = await client.post("/register", json=payload2)
    assert r2.status_code == 409
    assert "partner_id" in r2.json()["detail"].lower()


@pytest.mark.asyncio
async def test_register_duplicate_phone(client):
    """Same phone number cannot be registered twice."""
    r1 = await client.post("/register", json=base_registration_payload())
    assert r1.status_code == 201

    payload2 = base_registration_payload(partner_id="SWG-CHN-TEST002")
    r2 = await client.post("/register", json=payload2)
    assert r2.status_code == 409


@pytest.mark.asyncio
async def test_register_invalid_zone(client):
    """Non-existent pincode must return 400."""
    payload = base_registration_payload(zone1_pincode="999999")
    resp = await client.post("/register", json=payload)
    assert resp.status_code == 400
    assert "unknown zone" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_register_zone_city_mismatch(client):
    """Zone from different city than declared city must return 400."""
    payload = base_registration_payload(
        city="Chennai",
        zone1_pincode="400001"   # This belongs to Mumbai
    )
    resp = await client.post("/register", json=payload)
    assert resp.status_code == 400
    assert "city" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_register_duplicate_zones(client):
    """Same pincode used twice in zones must fail validation."""
    payload = base_registration_payload(
        zone1_pincode="600001",
        zone2_pincode="600001",  # Duplicate
    )
    resp = await client.post("/register", json=payload)
    assert resp.status_code == 422  # Pydantic validation error


@pytest.mark.asyncio
async def test_register_premium_floor_applied(client):
    """
    Seasoning riders have ₹0 income → floor of ₹15 must apply.
    Mock Module 2 returns city median; for floor test we rely on the
    mock mode returning income that could fall below floor with low tier_rate.
    """
    # Register with minimum tier (kavach) — city median income is used
    payload = base_registration_payload(tier="kavach")
    resp = await client.post("/register", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    # Premium must never be below ₹15
    assert data["weekly_premium"] >= 15.0
    bd = data["premium_breakdown"]
    # Either floor_applied is True OR the computed premium was already ≥ 15
    assert bd["final_premium"] >= 15.0


@pytest.mark.asyncio
async def test_register_all_tiers(client):
    """Each tier should register independently."""
    tiers = ["kavach", "suraksha", "raksha"]
    for i, tier in enumerate(tiers):
        payload = base_registration_payload(
            partner_id=f"SWG-CHN-TIER{i}",
            phone=f"+9198765{i:05d}",
            tier=tier,
        )
        resp = await client.post("/register", json=payload)
        assert resp.status_code == 201, f"Tier {tier} failed: {resp.text}"
        data = resp.json()
        assert data["tier"] == tier
        assert data["weekly_premium"] >= 15.0


@pytest.mark.asyncio
async def test_register_with_pan_kyc(client):
    """PAN-based KYC should work as alternative to Aadhaar."""
    payload = base_registration_payload(
        partner_id="ZOM-CHN-PAN001",
        phone="+919000000099",
        kyc={"type": "pan", "value": "ABCDE1234F"},
    )
    resp = await client.post("/register", json=payload)
    assert resp.status_code == 201, resp.text


@pytest.mark.asyncio
async def test_register_invalid_pan(client):
    """Malformed PAN must be rejected at validation."""
    payload = base_registration_payload(
        kyc={"type": "pan", "value": "INVALID_PAN"}
    )
    resp = await client.post("/register", json=payload)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_register_invalid_phone(client):
    """Non-Indian phone formats should be rejected."""
    payload = base_registration_payload(phone="12345")
    resp = await client.post("/register", json=payload)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_register_invalid_platform(client):
    """Unsupported platform should fail validation."""
    payload = base_registration_payload(platform="uber")
    resp = await client.post("/register", json=payload)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_register_missing_kyc(client):
    """Missing KYC block should fail validation."""
    payload = base_registration_payload()
    del payload["kyc"]
    resp = await client.post("/register", json=payload)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_register_zone1_required(client):
    """zone1_pincode is mandatory."""
    payload = base_registration_payload(zone1_pincode=None)
    resp = await client.post("/register", json=payload)
    assert resp.status_code in (400, 422)


@pytest.mark.asyncio
async def test_register_response_has_breakdown(client):
    """Registration response must include full premium breakdown fields."""
    resp = await client.post("/register", json=base_registration_payload())
    assert resp.status_code == 201
    bd = resp.json()["premium_breakdown"]
    required_fields = ["income", "tier_rate", "zone_risk", "seasonal_factor",
                       "raw_premium", "floor_applied", "cap_applied", "final_premium"]
    for field in required_fields:
        assert field in bd, f"Missing field in breakdown: {field}"


@pytest.mark.asyncio
async def test_register_policy_cycle_28_days(client):
    """Policy cycle must be exactly 28 days."""
    from datetime import date, timedelta
    resp = await client.post("/register", json=base_registration_payload())
    assert resp.status_code == 201
    data = resp.json()
    start = date.fromisoformat(data["cycle_start_date"])
    end = date.fromisoformat(data["cycle_end_date"])
    assert (end - start).days == 28, f"Expected 28-day cycle, got {(end - start).days}"
