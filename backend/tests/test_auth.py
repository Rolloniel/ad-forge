"""Tests for authentication routes and the require_auth dependency."""
from __future__ import annotations

import pytest
from httpx import AsyncClient


async def test_validate_valid_key(client: AsyncClient):
    resp = await client.post("/api/auth/validate", json={"api_key": "dev-key"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["valid"] is True
    assert data["token"] == "dev-key"


async def test_validate_invalid_key(client: AsyncClient):
    resp = await client.post("/api/auth/validate", json={"api_key": "wrong-key"})
    assert resp.status_code == 401
    assert "Invalid API key" in resp.json()["detail"]


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
    assert "Invalid token" in resp.json()["detail"]


async def test_protected_route_valid_token(authed_client: AsyncClient):
    resp = await authed_client.get("/api/brands")
    assert resp.status_code == 200
