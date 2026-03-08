"""Shared fixtures for the AdForge backend test suite."""
from __future__ import annotations

import sqlite3
import uuid
from collections.abc import AsyncGenerator
from decimal import Decimal

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID

# Register sqlite3 adapter so UUID objects are stored as strings, not floats.
sqlite3.register_adapter(uuid.UUID, str)

# Patch missing function that ad_copy.py tries to import before any app module
# is loaded during test collection.
import app.integrations.openai_client as _oai_mod

if not hasattr(_oai_mod, "generate_structured_json"):

    async def _stub(**kwargs):
        raise NotImplementedError("generate_structured_json stub")

    _oai_mod.generate_structured_json = _stub

from app.db import get_session
from app.models.base import Base
from app.models.brand import Audience, Brand, Product

# Map PostgreSQL types to SQLite-compatible equivalents
@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(type_, compiler, **kw):
    return "JSON"


@compiles(PG_UUID, "sqlite")
def _compile_uuid_sqlite(type_, compiler, **kw):
    return "VARCHAR(36)"


TEST_DB_URL = "sqlite+aiosqlite://"
AUTH_HEADERS = {"Authorization": "Bearer dev-key"}


# ---------------------------------------------------------------------------
# Database fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def engine():
    eng = create_async_engine(TEST_DB_URL, echo=False)

    # Enable foreign keys on SQLite connections
    @event.listens_for(eng.sync_engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await eng.dispose()


@pytest_asyncio.fixture
async def session(engine) -> AsyncGenerator[AsyncSession]:
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as sess:
        yield sess


# ---------------------------------------------------------------------------
# HTTP client fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def client(session) -> AsyncGenerator[AsyncClient]:
    """Unauthenticated test client."""
    from app.main import app

    async def _override_get_session():
        yield session

    app.dependency_overrides[get_session] = _override_get_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def authed_client(session) -> AsyncGenerator[AsyncClient]:
    """Test client with valid Bearer auth header."""
    from app.main import app

    async def _override_get_session():
        yield session

    app.dependency_overrides[get_session] = _override_get_session
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test", headers=AUTH_HEADERS
    ) as c:
        yield c
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Seed data fixtures
# ---------------------------------------------------------------------------

SEED_BRAND_ID = uuid.UUID("a1b2c3d4-e5f6-7890-abcd-ef1234567890")
SEED_PRODUCT_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
SEED_AUDIENCE_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")


@pytest_asyncio.fixture
async def seed_brand(session) -> Brand:
    """Create a brand with one product and one audience."""
    brand = Brand(
        id=SEED_BRAND_ID,
        name="TestBrand",
        voice="Friendly and professional",
        visual_guidelines="Minimalist design",
        offers={"promos": [{"name": "10% Off", "code": "SAVE10"}]},
    )
    brand.products = [
        Product(
            id=SEED_PRODUCT_ID,
            name="Widget Pro",
            description="A premium widget",
            price=Decimal("29.99"),
        ),
    ]
    brand.audiences = [
        Audience(
            id=SEED_AUDIENCE_ID,
            name="Tech Enthusiasts",
            demographics="Ages 25-40",
            interests="Technology, gadgets",
        ),
    ]
    session.add(brand)
    await session.commit()
    await session.refresh(brand, attribute_names=["products", "audiences"])
    return brand
