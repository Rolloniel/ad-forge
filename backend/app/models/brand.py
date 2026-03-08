from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .insight import Insight
    from .job import Job


class Brand(TimestampMixin, Base):
    __tablename__ = "brands"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    voice: Mapped[str | None] = mapped_column(Text)
    visual_guidelines: Mapped[str | None] = mapped_column(Text)
    offers: Mapped[dict | None] = mapped_column(JSONB)

    products: Mapped[list[Product]] = relationship(back_populates="brand", cascade="all, delete-orphan")
    audiences: Mapped[list[Audience]] = relationship(back_populates="brand", cascade="all, delete-orphan")
    jobs: Mapped[list[Job]] = relationship(back_populates="brand")
    insights: Mapped[list[Insight]] = relationship(back_populates="brand")


class Product(Base):
    __tablename__ = "products"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    brand_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("brands.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    image_url: Mapped[str | None] = mapped_column(String(2048))

    brand: Mapped[Brand] = relationship(back_populates="products")


class Audience(Base):
    __tablename__ = "audiences"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    brand_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("brands.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    demographics: Mapped[str | None] = mapped_column(Text)
    interests: Mapped[str | None] = mapped_column(Text)

    brand: Mapped[Brand] = relationship(back_populates="audiences")
