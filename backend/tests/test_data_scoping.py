"""Tests that users only see their own data."""
from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timedelta, timezone

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models.brand import Brand
from app.models.user import ApiKey, User


async def _make_user_client(session, name, raw_key):
    """Helper: create user+key, return (user, AsyncClient)."""
    user = User(name=name, is_admin=False)
    session.add(user)
    await session.flush()
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    api_key = ApiKey(
        user_id=user.id,
        key_hash=key_hash,
        key_prefix=raw_key[:8],
        expires_at=datetime.now(timezone.utc) + timedelta(days=14),
        is_active=True,
    )
    session.add(api_key)
    await session.commit()

    from app.main import app

    async def _override():
        yield session

    app.dependency_overrides[get_session] = _override

    transport = ASGITransport(app=app)
    client = AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"Authorization": f"Bearer {raw_key}"},
    )
    return user, client


@pytest_asyncio.fixture
async def two_users(session):
    """Create two users, each with a brand."""
    user_a, client_a = await _make_user_client(session, "UserA", "adf_" + "1" * 32)
    user_b, client_b = await _make_user_client(session, "UserB", "adf_" + "2" * 32)

    brand_a = Brand(name="BrandA", user_id=user_a.id)
    brand_b = Brand(name="BrandB", user_id=user_b.id)
    session.add_all([brand_a, brand_b])
    await session.commit()

    yield {
        "user_a": user_a, "client_a": client_a, "brand_a": brand_a,
        "user_b": user_b, "client_b": client_b, "brand_b": brand_b,
    }

    from app.main import app

    app.dependency_overrides.clear()
    await client_a.aclose()
    await client_b.aclose()


async def test_user_sees_only_own_brands(two_users):
    resp_a = await two_users["client_a"].get("/api/brands")
    assert resp_a.status_code == 200
    brands_a = resp_a.json()
    assert len(brands_a) == 1
    assert brands_a[0]["name"] == "BrandA"

    resp_b = await two_users["client_b"].get("/api/brands")
    assert resp_b.status_code == 200
    brands_b = resp_b.json()
    assert len(brands_b) == 1
    assert brands_b[0]["name"] == "BrandB"


async def test_user_cannot_access_other_users_brand(two_users):
    brand_b_id = str(two_users["brand_b"].id)
    resp = await two_users["client_a"].get(f"/api/brands/{brand_b_id}")
    assert resp.status_code == 404


async def test_created_brand_belongs_to_user(two_users):
    resp = await two_users["client_a"].post("/api/brands", json={"name": "NewBrand"})
    assert resp.status_code == 201

    # UserA sees it
    resp_a = await two_users["client_a"].get("/api/brands")
    names = [b["name"] for b in resp_a.json()]
    assert "NewBrand" in names

    # UserB does not
    resp_b = await two_users["client_b"].get("/api/brands")
    names = [b["name"] for b in resp_b.json()]
    assert "NewBrand" not in names
