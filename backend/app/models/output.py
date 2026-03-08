from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .job import Job


class Output(TimestampMixin, Base):
    __tablename__ = "outputs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False
    )
    pipeline_name: Mapped[str] = mapped_column(String(255), nullable=False)
    output_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_path: Mapped[str | None] = mapped_column(String(2048))
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB)

    job: Mapped[Job] = relationship(back_populates="outputs")
    performance_metrics: Mapped[list[PerformanceMetric]] = relationship(
        back_populates="output", cascade="all, delete-orphan"
    )


class PerformanceMetric(Base):
    __tablename__ = "performance_metrics"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    output_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("outputs.id", ondelete="CASCADE"), nullable=False
    )
    impressions: Mapped[int | None] = mapped_column(Integer)
    clicks: Mapped[int | None] = mapped_column(Integer)
    ctr: Mapped[float | None] = mapped_column(Float)
    conversions: Mapped[int | None] = mapped_column(Integer)
    cpa: Mapped[float | None] = mapped_column(Float)
    roas: Mapped[float | None] = mapped_column(Float)
    simulated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    output: Mapped[Output] = relationship(back_populates="performance_metrics")
