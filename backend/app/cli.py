"""AdForge user management CLI.

Usage:
    python -m app.cli create-user "Name" [--admin] [--expires-days 14]
    python -m app.cli list-users
    python -m app.cli revoke-key <key_prefix>
    python -m app.cli delete-user <user_id>
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import selectinload

from app.config import settings
from app.models.brand import Audience, Brand, Product
from app.models.user import ApiKey, User


def _generate_key() -> tuple[str, str, str]:
    """Generate API key. Returns (raw_key, key_hash, key_prefix)."""
    raw_key = "adf_" + secrets.token_hex(16)
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    key_prefix = raw_key[:8]
    return raw_key, key_hash, key_prefix


async def _get_session() -> tuple[async_sessionmaker, AsyncEngine]:
    """Create a new engine and session factory."""
    engine = create_async_engine(settings.database_url, echo=False)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    return factory, engine


async def _seed_for_user(session: AsyncSession, user_id: uuid.UUID) -> None:
    """Copy GlowVita seed data with fresh UUIDs, assigned to the given user."""
    brand = Brand(
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
    brand.products = [
        Product(name="Vitamin C Brightening Serum", description="20% stabilized Vitamin C with hyaluronic acid and ferulic acid.", price=49),
        Product(name="Collagen Peptide Complex", description="Multi-peptide complex with retinol and niacinamide.", price=59),
        Product(name="Hydration Boost Bundle", description="Complete hydration system: hyaluronic acid serum + ceramide moisturizer.", price=89),
    ]
    brand.audiences = [
        Audience(name="Women 25-40 Skincare Enthusiasts", demographics="Women, age 25-40, urban, $60K+ household income", interests="Skincare routines, clean beauty, wellness"),
        Audience(name="Women 40-55 Anti-Aging", demographics="Women, age 40-55, suburban/urban, $80K+ household income", interests="Anti-aging, dermatologist recommendations, luxury skincare"),
        Audience(name="Men 30-45 Wellness", demographics="Men, age 30-45, urban, $70K+ household income", interests="Men's grooming, fitness, biohacking"),
    ]
    session.add(brand)


async def create_user(name: str, is_admin: bool = False, expires_days: int = 14) -> None:
    factory, engine = await _get_session()
    async with factory() as session:
        user = User(name=name, is_admin=is_admin)
        session.add(user)
        await session.flush()

        raw_key, key_hash, key_prefix = _generate_key()
        expires_at = datetime.now(timezone.utc) + timedelta(days=expires_days)
        api_key = ApiKey(
            user_id=user.id,
            key_hash=key_hash,
            key_prefix=key_prefix,
            expires_at=expires_at,
            is_active=True,
        )
        session.add(api_key)

        await _seed_for_user(session, user.id)
        await session.commit()

        print(f"User created: {user.name} (id: {user.id})")
        print(f"Admin: {is_admin}")
        print(f"API Key: {raw_key}")
        print(f"Expires: {expires_at.strftime('%Y-%m-%d %H:%M UTC')}")
        print("Save this key — it will not be shown again.")

    await engine.dispose()


async def list_users() -> None:
    factory, engine = await _get_session()
    async with factory() as session:
        result = await session.execute(
            select(User).options(selectinload(User.api_keys), selectinload(User.brands))
        )
        users = result.scalars().all()

        if not users:
            print("No users found.")
            return

        print(f"{'Name':<25} {'Key Prefix':<12} {'Expires':<22} {'Active':<8} {'Admin':<7} {'Brands'}")
        print("-" * 90)
        for user in users:
            for key in user.api_keys:
                print(
                    f"{user.name:<25} "
                    f"{key.key_prefix:<12} "
                    f"{key.expires_at.strftime('%Y-%m-%d %H:%M UTC'):<22} "
                    f"{'yes' if key.is_active else 'no':<8} "
                    f"{'yes' if user.is_admin else 'no':<7} "
                    f"{len(user.brands)}"
                )

    await engine.dispose()


async def revoke_key(key_prefix: str) -> None:
    factory, engine = await _get_session()
    async with factory() as session:
        result = await session.execute(
            select(ApiKey).where(ApiKey.key_prefix == key_prefix).options(selectinload(ApiKey.user))
        )
        api_key = result.scalar_one_or_none()
        if api_key is None:
            print(f"No API key found with prefix: {key_prefix}")
            return

        api_key.is_active = False
        await session.commit()
        print(f"Revoked key {key_prefix} for user: {api_key.user.name}")

    await engine.dispose()


async def delete_user(user_id_str: str) -> None:
    factory, engine = await _get_session()
    async with factory() as session:
        uid = uuid.UUID(user_id_str)
        user = await session.get(User, uid)
        if user is None:
            print(f"No user found with id: {user_id_str}")
            return

        name = user.name
        await session.delete(user)
        await session.commit()
        print(f"Deleted user: {name} (and all their data)")

    await engine.dispose()


def main():
    parser = argparse.ArgumentParser(description="AdForge user management")
    sub = parser.add_subparsers(dest="command")

    create = sub.add_parser("create-user", help="Create a new user with API key")
    create.add_argument("name", help="User display name")
    create.add_argument("--admin", action="store_true", help="Grant admin privileges")
    create.add_argument("--expires-days", type=int, default=14, help="Key expiry in days (default: 14)")

    sub.add_parser("list-users", help="List all users")

    revoke = sub.add_parser("revoke-key", help="Revoke an API key")
    revoke.add_argument("key_prefix", help="First 8 characters of the key")

    delete = sub.add_parser("delete-user", help="Delete a user and all their data")
    delete.add_argument("user_id", help="User UUID")

    args = parser.parse_args()

    if args.command == "create-user":
        asyncio.run(create_user(args.name, args.admin, args.expires_days))
    elif args.command == "list-users":
        asyncio.run(list_users())
    elif args.command == "revoke-key":
        asyncio.run(revoke_key(args.key_prefix))
    elif args.command == "delete-user":
        asyncio.run(delete_user(args.user_id))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
