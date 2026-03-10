"""add users and api keys

Revision ID: 0002
Revises: 0001
Create Date: 2026-03-10
"""
from __future__ import annotations

import uuid
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Create users table
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # 2. Create api_keys table
    op.create_table(
        "api_keys",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("key_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("key_prefix", sa.String(8), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # 3. Add user_id to brands (nullable first)
    op.add_column("brands", sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True))
    op.create_index("ix_brands_user_id", "brands", ["user_id"])

    # 4. Data migration: create admin user and assign existing brands
    admin_id = uuid.uuid4()
    raw_key = "adf_" + secrets.token_hex(16)
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    key_prefix = raw_key[:8]
    now = datetime.now(timezone.utc)
    expires = now + timedelta(days=365)  # admin key: 1 year

    users_table = sa.table("users",
        sa.column("id", UUID(as_uuid=True)),
        sa.column("name", sa.String),
        sa.column("is_admin", sa.Boolean),
        sa.column("created_at", sa.DateTime(timezone=True)),
    )
    op.bulk_insert(users_table, [{
        "id": admin_id,
        "name": "Admin",
        "is_admin": True,
        "created_at": now,
    }])

    api_keys_table = sa.table("api_keys",
        sa.column("id", UUID(as_uuid=True)),
        sa.column("user_id", UUID(as_uuid=True)),
        sa.column("key_hash", sa.String),
        sa.column("key_prefix", sa.String),
        sa.column("expires_at", sa.DateTime(timezone=True)),
        sa.column("is_active", sa.Boolean),
        sa.column("created_at", sa.DateTime(timezone=True)),
    )
    op.bulk_insert(api_keys_table, [{
        "id": uuid.uuid4(),
        "user_id": admin_id,
        "key_hash": key_hash,
        "key_prefix": key_prefix,
        "expires_at": expires,
        "is_active": True,
        "created_at": now,
    }])

    # Assign all existing brands to admin
    op.execute(sa.text(f"UPDATE brands SET user_id = '{admin_id}'"))

    # 5. Make user_id NOT NULL
    op.alter_column("brands", "user_id", nullable=False)

    # Print the admin key (visible in migration output)
    print(f"\n{'='*60}")
    print(f"ADMIN API KEY: {raw_key}")
    print(f"Save this key — it will not be shown again.")
    print(f"Expires: {expires.isoformat()}")
    print(f"{'='*60}\n")


def downgrade() -> None:
    op.drop_index("ix_brands_user_id", table_name="brands")
    op.drop_column("brands", "user_id")
    op.drop_table("api_keys")
    op.drop_table("users")
