"""Seed data for GlowVita — fictional DTC premium skincare supplement brand."""
from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.models import Audience, Brand, Product

BRAND_ID = uuid.UUID("a1b2c3d4-e5f6-7890-abcd-ef1234567890")


async def seed_glowvita(engine: AsyncEngine, user_id: uuid.UUID | None = None) -> None:
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        existing = await session.get(Brand, BRAND_ID)
        if existing:
            print("GlowVita seed data already exists, skipping.")
            return

        brand = Brand(
            id=BRAND_ID,
            name="GlowVita",
            user_id=user_id,
            voice="Clean, confident, science-backed but approachable. No hype.",
            visual_guidelines=(
                "Minimalist aesthetic with warm earth tones. "
                "Primary: soft gold (#C9A96E), cream (#F5F0E8). "
                "Accent: forest green (#2D5F3E). "
                "Typography: modern sans-serif. "
                "Photography: natural light, clean backgrounds, diverse models."
            ),
            offers=[
                {"name": "Buy 2 Get 1 Free", "type": "bundle", "discount_pct": 33},
                {"name": "30-Day Glow Guarantee", "type": "guarantee", "days": 30},
                {"name": "Subscribe & Save 20%", "type": "subscription", "discount_pct": 20},
            ],
        )
        session.add(brand)

        products = [
            Product(
                id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
                brand_id=BRAND_ID,
                name="Vitamin C Brightening Serum",
                description=(
                    "20% stabilized Vitamin C with hyaluronic acid and ferulic acid. "
                    "Targets dark spots, uneven tone, and dullness. "
                    "Lightweight, fast-absorbing formula suitable for all skin types."
                ),
                price=Decimal("49.00"),
                image_url=None,
            ),
            Product(
                id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
                brand_id=BRAND_ID,
                name="Collagen Peptide Complex",
                description=(
                    "Multi-peptide complex with retinol and niacinamide. "
                    "Boosts collagen production, reduces fine lines, and firms skin. "
                    "Clinically tested, visible results in 4 weeks."
                ),
                price=Decimal("59.00"),
                image_url=None,
            ),
            Product(
                id=uuid.UUID("33333333-3333-3333-3333-333333333333"),
                brand_id=BRAND_ID,
                name="Hydration Boost Bundle",
                description=(
                    "Complete hydration system: hyaluronic acid serum + ceramide moisturizer "
                    "+ overnight recovery mask. 72-hour moisture lock technology. "
                    "Perfect for dry and combination skin."
                ),
                price=Decimal("89.00"),
                image_url=None,
            ),
        ]
        session.add_all(products)

        audiences = [
            Audience(
                id=uuid.UUID("aaaa1111-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
                brand_id=BRAND_ID,
                name="Women 25-40 Skincare Enthusiasts",
                demographics="Women, age 25-40, urban, $60K+ household income",
                interests=(
                    "Skincare routines, clean beauty, wellness, self-care, "
                    "ingredient transparency, sustainable packaging"
                ),
            ),
            Audience(
                id=uuid.UUID("bbbb2222-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
                brand_id=BRAND_ID,
                name="Women 40-55 Anti-Aging",
                demographics="Women, age 40-55, suburban/urban, $80K+ household income",
                interests=(
                    "Anti-aging, dermatologist recommendations, luxury skincare, "
                    "preventive health, collagen supplements"
                ),
            ),
            Audience(
                id=uuid.UUID("cccc3333-cccc-cccc-cccc-cccccccccccc"),
                brand_id=BRAND_ID,
                name="Men 30-45 Wellness",
                demographics="Men, age 30-45, urban, $70K+ household income",
                interests=(
                    "Men's grooming, fitness, biohacking, minimalist routines, "
                    "performance optimization"
                ),
            ),
        ]
        session.add_all(audiences)

        await session.commit()
        print(f"Seeded GlowVita: 1 brand, {len(products)} products, {len(audiences)} audiences.")
