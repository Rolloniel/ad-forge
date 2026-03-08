from __future__ import annotations

import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import get_session
from app.models.brand import Audience, Brand, Product
from app.routes.auth import require_auth

router = APIRouter(
    prefix="/api/brands",
    tags=["brands"],
    dependencies=[Depends(require_auth)],
)


# ---------- Schemas ----------


class ProductIn(BaseModel):
    name: str
    description: str | None = None
    price: Decimal | None = None
    image_url: str | None = None


class ProductOut(ProductIn):
    id: uuid.UUID
    brand_id: uuid.UUID

    model_config = {"from_attributes": True}


class AudienceIn(BaseModel):
    name: str
    demographics: str | None = None
    interests: str | None = None


class AudienceOut(AudienceIn):
    id: uuid.UUID
    brand_id: uuid.UUID

    model_config = {"from_attributes": True}


class BrandCreate(BaseModel):
    name: str
    voice: str | None = None
    visual_guidelines: str | None = None
    offers: dict | None = None
    products: list[ProductIn] | None = None
    audiences: list[AudienceIn] | None = None


class BrandUpdate(BaseModel):
    name: str | None = None
    voice: str | None = None
    visual_guidelines: str | None = None
    offers: dict | None = None
    products: list[ProductIn] | None = None
    audiences: list[AudienceIn] | None = None


class BrandOut(BaseModel):
    id: uuid.UUID
    name: str
    voice: str | None = None
    visual_guidelines: str | None = None
    offers: dict | None = None
    products: list[ProductOut] = []
    audiences: list[AudienceOut] = []

    model_config = {"from_attributes": True}


# ---------- Helpers ----------


def _eager_brand_opts():
    return [selectinload(Brand.products), selectinload(Brand.audiences)]


# ---------- Routes ----------


@router.get("", response_model=list[BrandOut])
async def list_brands(session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(Brand).options(*_eager_brand_opts()).order_by(Brand.name)
    )
    return result.scalars().all()


@router.post("", response_model=BrandOut, status_code=status.HTTP_201_CREATED)
async def create_brand(
    body: BrandCreate,
    session: AsyncSession = Depends(get_session),
):
    brand = Brand(
        name=body.name,
        voice=body.voice,
        visual_guidelines=body.visual_guidelines,
        offers=body.offers,
    )
    if body.products:
        brand.products = [Product(**p.model_dump()) for p in body.products]
    if body.audiences:
        brand.audiences = [Audience(**a.model_dump()) for a in body.audiences]
    session.add(brand)
    await session.commit()
    await session.refresh(brand, attribute_names=["products", "audiences"])
    return brand


@router.get("/{brand_id}", response_model=BrandOut)
async def get_brand(
    brand_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(Brand).where(Brand.id == brand_id).options(*_eager_brand_opts())
    )
    brand = result.scalar_one_or_none()
    if brand is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Brand not found")
    return brand


@router.put("/{brand_id}", response_model=BrandOut)
async def update_brand(
    brand_id: uuid.UUID,
    body: BrandUpdate,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(Brand).where(Brand.id == brand_id).options(*_eager_brand_opts())
    )
    brand = result.scalar_one_or_none()
    if brand is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Brand not found")

    updates = body.model_dump(exclude_unset=True)

    # Handle nested products replacement
    if "products" in updates:
        products_data = updates.pop("products")
        if products_data is not None:
            brand.products = [Product(**p) for p in products_data]

    # Handle nested audiences replacement
    if "audiences" in updates:
        audiences_data = updates.pop("audiences")
        if audiences_data is not None:
            brand.audiences = [Audience(**a) for a in audiences_data]

    for key, value in updates.items():
        setattr(brand, key, value)

    await session.commit()
    await session.refresh(brand, attribute_names=["products", "audiences"])
    return brand
