"""Tests for Brand CRUD routes."""
from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from tests.conftest import SEED_BRAND_ID


async def test_list_brands_empty(authed_client: AsyncClient):
    resp = await authed_client.get("/api/brands")
    assert resp.status_code == 200
    assert resp.json() == []


async def test_create_brand_minimal(authed_client: AsyncClient):
    resp = await authed_client.post("/api/brands", json={"name": "Acme"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Acme"
    assert data["products"] == []
    assert data["audiences"] == []
    assert "id" in data


async def test_create_brand_with_nested(authed_client: AsyncClient):
    payload = {
        "name": "FullBrand",
        "voice": "Bold",
        "visual_guidelines": "Bright colors",
        "offers": {"summer": "20% off"},
        "products": [
            {"name": "Gadget", "description": "Cool gadget", "price": "19.99"},
        ],
        "audiences": [
            {
                "name": "Millennials",
                "demographics": "25-40",
                "interests": "Tech",
            },
        ],
    }
    resp = await authed_client.post("/api/brands", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "FullBrand"
    assert data["voice"] == "Bold"
    assert len(data["products"]) == 1
    assert data["products"][0]["name"] == "Gadget"
    assert len(data["audiences"]) == 1
    assert data["audiences"][0]["name"] == "Millennials"


async def test_get_brand(authed_client: AsyncClient, seed_brand):
    resp = await authed_client.get(f"/api/brands/{SEED_BRAND_ID}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "TestBrand"
    assert len(data["products"]) == 1
    assert len(data["audiences"]) == 1


async def test_get_brand_not_found(authed_client: AsyncClient):
    fake_id = uuid.uuid4()
    resp = await authed_client.get(f"/api/brands/{fake_id}")
    assert resp.status_code == 404


async def test_list_brands_with_data(authed_client: AsyncClient, seed_brand):
    resp = await authed_client.get("/api/brands")
    assert resp.status_code == 200
    brands = resp.json()
    assert len(brands) >= 1
    names = [b["name"] for b in brands]
    assert "TestBrand" in names


async def test_update_brand_name(authed_client: AsyncClient, seed_brand):
    resp = await authed_client.put(
        f"/api/brands/{SEED_BRAND_ID}", json={"name": "RenamedBrand"}
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "RenamedBrand"


async def test_update_brand_replace_products(authed_client: AsyncClient, seed_brand):
    new_products = [{"name": "NewProduct", "description": "Shiny", "price": "49.99"}]
    resp = await authed_client.put(
        f"/api/brands/{SEED_BRAND_ID}", json={"products": new_products}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["products"]) == 1
    assert data["products"][0]["name"] == "NewProduct"


async def test_update_brand_not_found(authed_client: AsyncClient):
    fake_id = uuid.uuid4()
    resp = await authed_client.put(f"/api/brands/{fake_id}", json={"name": "X"})
    assert resp.status_code == 404
