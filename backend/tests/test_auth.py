"""Tests for authentication routes and the require_auth dependency."""
from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import ApiKey, User


@pytest_asyncio.fixture
async def demo_user(session: AsyncSession) -> tuple[User, str]:
    """Create a demo user with a valid API key. Returns (user, raw_key)."""
    user = User(name="TestUser", is_admin=False)
    session.add(user)
    await session.flush()

    raw_key = "adf_" + "a" * 32
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
    return user, raw_key


@pytest_asyncio.fixture
async def expired_user(session: AsyncSession) -> tuple[User, str]:
    """Create a user with an expired API key."""
    user = User(name="ExpiredUser", is_admin=False)
    session.add(user)
    await session.flush()

    raw_key = "adf_" + "b" * 32
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    api_key = ApiKey(
        user_id=user.id,
        key_hash=key_hash,
        key_prefix=raw_key[:8],
        expires_at=datetime.now(timezone.utc) - timedelta(days=1),
        is_active=True,
    )
    session.add(api_key)
    await session.commit()
    return user, raw_key


@pytest_asyncio.fixture
async def revoked_user(session: AsyncSession) -> tuple[User, str]:
    """Create a user with a revoked API key."""
    user = User(name="RevokedUser", is_admin=False)
    session.add(user)
    await session.flush()

    raw_key = "adf_" + "c" * 32
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    api_key = ApiKey(
        user_id=user.id,
        key_hash=key_hash,
        key_prefix=raw_key[:8],
        expires_at=datetime.now(timezone.utc) + timedelta(days=14),
        is_active=False,
    )
    session.add(api_key)
    await session.commit()
    return user, raw_key


async def test_validate_valid_key(client: AsyncClient, demo_user):
    _, raw_key = demo_user
    resp = await client.post("/api/auth/validate", json={"api_key": raw_key})
    assert resp.status_code == 200
    data = resp.json()
    assert data["valid"] is True
    assert data["user_name"] == "TestUser"


async def test_validate_invalid_key(client: AsyncClient):
    resp = await client.post("/api/auth/validate", json={"api_key": "wrong-key"})
    assert resp.status_code == 401
    assert "Invalid" in resp.json()["detail"]


async def test_validate_expired_key(client: AsyncClient, expired_user):
    _, raw_key = expired_user
    resp = await client.post("/api/auth/validate", json={"api_key": raw_key})
    assert resp.status_code == 401


async def test_validate_revoked_key(client: AsyncClient, revoked_user):
    _, raw_key = revoked_user
    resp = await client.post("/api/auth/validate", json={"api_key": raw_key})
    assert resp.status_code == 401


async def test_protected_route_no_header(client: AsyncClient):
    resp = await client.get("/api/brands")
    assert resp.status_code == 422  # missing Authorization header


async def test_protected_route_bad_scheme(client: AsyncClient):
    resp = await client.get("/api/brands", headers={"Authorization": "Basic abc"})
    assert resp.status_code == 401
    assert "Bearer" in resp.json()["detail"]


async def test_protected_route_invalid_token(client: AsyncClient):
    resp = await client.get(
        "/api/brands", headers={"Authorization": "Bearer wrong-token"}
    )
    assert resp.status_code == 401


async def test_protected_route_valid_token(client: AsyncClient, demo_user):
    _, raw_key = demo_user
    resp = await client.get(
        "/api/brands", headers={"Authorization": f"Bearer {raw_key}"}
    )
    assert resp.status_code == 200
