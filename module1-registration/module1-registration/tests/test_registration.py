"""
tests/test_registration.py
---------------------------
Integration tests for POST /register (current API: zone_id fields, optional demo_income_override).
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import text
from sqlalchemy.pool import NullPool

from main import app
from db.connection import get_db, Base
from config import settings

TEST_DATABASE_URL = settings.DATABASE_URL.rsplit("/", 1)[0] + "/rahatpay_test"

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False, poolclass=NullPool)
TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
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

# Populated in setup_db: lists of zone_id per city (ordered)
_reg_zones: dict[str, list[int]] = {}


@pytest_asyncio.fixture(scope="function", autouse=True)
async def setup_db():
    global _reg_zones
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

        await conn.execute(
            text("""
            INSERT INTO zones (city, area_name, risk_multiplier, polygon, is_active, registration_cap) VALUES
            ('Chennai', 'George Town', 1.20, '[]'::jsonb, TRUE, 1000),
            ('Chennai', 'Sowcarpet', 1.15, '[]'::jsonb, TRUE, 1000),
            ('Chennai', 'Egmore', 1.10, '[]'::jsonb, TRUE, 1000),
            ('Mumbai', 'Fort', 1.30, '[]'::jsonb, TRUE, 1000),
            ('Bangalore', 'MG Road', 1.00, '[]'::jsonb, TRUE, 1000)
        """)
        )
        res = await conn.execute(
            text("SELECT zone_id, city FROM zones ORDER BY zone_id")
        )
        rows = res.fetchall()
    _reg_zones = {}
    for zid, city in rows:
        _reg_zones.setdefault(city, []).append(zid)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


def _chennai_ids() -> list[int]:
    return _reg_zones.get("Chennai", [1, 2, 3])


def _mumbai_id() -> int:
    return _reg_zones.get("Mumbai", [4])[0]


def base_registration_payload(**overrides):
    ch = _chennai_ids()
    payload = {
        "partner_id": "SWG-CHN-TEST001",
        "platform": "swiggy",
        "name": "Test Rider",
        "phone": "+919876543210",
        "kyc": {"type": "aadhaar", "value": "1234"},
        "city": "Chennai",
        "zone1_id": ch[0],
        "zone2_id": ch[1],
        "zone3_id": None,
        "tier": "kavach",
    }
    payload.update(overrides)
    return payload


@pytest.mark.asyncio
async def test_register_success(client):
    payload = base_registration_payload()
    resp = await client.post("/register", json=payload)
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert "rider_id" in data
    assert "policy_id" in data
    assert data["tier"] == "kavach"
    assert data["weekly_premium"] >= 15.0
    assert "premium_breakdown" in data
    assert data["cycle_start_date"] is not None
    assert data["cycle_end_date"] is not None
    assert data["is_seasoning"] is True


@pytest.mark.asyncio
async def test_register_duplicate_partner_id(client):
    payload = base_registration_payload()
    r1 = await client.post("/register", json=payload)
    assert r1.status_code == 201, r1.text

    payload2 = base_registration_payload(phone="+919000000001")
    r2 = await client.post("/register", json=payload2)
    assert r2.status_code == 409
    assert "partner_id" in r2.json()["detail"].lower()


@pytest.mark.asyncio
async def test_register_duplicate_phone(client):
    r1 = await client.post("/register", json=base_registration_payload())
    assert r1.status_code == 201

    payload2 = base_registration_payload(partner_id="SWG-CHN-TEST002")
    r2 = await client.post("/register", json=payload2)
    assert r2.status_code == 409


@pytest.mark.asyncio
async def test_register_invalid_zone(client):
    payload = base_registration_payload(zone1_id=99999)
    resp = await client.post("/register", json=payload)
    assert resp.status_code == 400
    assert "unknown zone" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_register_zone_city_mismatch(client):
    payload = base_registration_payload(city="Chennai", zone1_id=_mumbai_id())
    resp = await client.post("/register", json=payload)
    assert resp.status_code == 400
    assert "city" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_register_duplicate_zones(client):
    ch = _chennai_ids()
    payload = base_registration_payload(zone1_id=ch[0], zone2_id=ch[0])
    resp = await client.post("/register", json=payload)
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_register_premium_floor_applied(client):
    payload = base_registration_payload(
        partner_id="DEMO-FLOOR-01",
        phone="+919111111111",
        tier="kavach",
        demo_income_override=800.0,
    )
    resp = await client.post("/register", json=payload)
    assert resp.status_code == 201, resp.text
    data = resp.json()
    bd = data["premium_breakdown"]
    assert bd["floor_applied"] is True
    assert data["weekly_premium"] >= 15.0
    assert bd["final_premium"] >= 15.0


@pytest.mark.asyncio
async def test_register_demo_income_respects_percent_cap(client):
    """High demo income: final premium never exceeds 3.5% of income (floor still applies)."""
    payload = base_registration_payload(
        partner_id="DEMO-CAP-01",
        phone="+919222222222",
        tier="raksha",
        demo_income_override=50_000.0,
    )
    resp = await client.post("/register", json=payload)
    assert resp.status_code == 201, resp.text
    bd = resp.json()["premium_breakdown"]
    assert bd["income"] == 50_000.0
    assert bd["final_premium"] <= 50_000.0 * 0.035 + 0.02
    assert bd["final_premium"] >= 15.0


@pytest.mark.asyncio
async def test_register_all_tiers(client):
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
    payload = base_registration_payload(
        partner_id="ZOM-CHN-PAN001",
        phone="+919000000099",
        kyc={"type": "pan", "value": "ABCDE1234F"},
    )
    resp = await client.post("/register", json=payload)
    assert resp.status_code == 201, resp.text


@pytest.mark.asyncio
async def test_register_invalid_pan(client):
    payload = base_registration_payload(kyc={"type": "pan", "value": "INVALID_PAN"})
    resp = await client.post("/register", json=payload)
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_register_invalid_phone(client):
    payload = base_registration_payload(phone="12345")
    resp = await client.post("/register", json=payload)
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_register_invalid_platform(client):
    payload = base_registration_payload(platform="uber")
    resp = await client.post("/register", json=payload)
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_register_missing_kyc(client):
    payload = base_registration_payload()
    del payload["kyc"]
    resp = await client.post("/register", json=payload)
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_register_zone1_required(client):
    payload = base_registration_payload()
    del payload["zone1_id"]
    resp = await client.post("/register", json=payload)
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_register_response_has_breakdown(client):
    resp = await client.post("/register", json=base_registration_payload())
    assert resp.status_code == 201
    bd = resp.json()["premium_breakdown"]
    required_fields = [
        "income",
        "tier_rate",
        "zone_risk",
        "seasonal_factor",
        "raw_premium",
        "floor_applied",
        "cap_applied",
        "final_premium",
    ]
    for field in required_fields:
        assert field in bd, f"Missing field in breakdown: {field}"


@pytest.mark.asyncio
async def test_register_policy_cycle_28_days(client):
    from datetime import date

    resp = await client.post("/register", json=base_registration_payload())
    assert resp.status_code == 201
    data = resp.json()
    start = date.fromisoformat(data["cycle_start_date"])
    end = date.fromisoformat(data["cycle_end_date"])
    assert (end - start).days == 28
