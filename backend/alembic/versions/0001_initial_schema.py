"""Initial schema: brands, products, audiences, jobs, outputs, events, insights

Revision ID: 0001
Revises:
Create Date: 2026-03-08
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

job_status = postgresql.ENUM("pending", "running", "completed", "failed", name="job_status", create_type=False)
step_status = postgresql.ENUM("pending", "running", "completed", "failed", name="step_status", create_type=False)


def upgrade() -> None:
    # Create enum types
    job_status.create(op.get_bind(), checkfirst=True)
    step_status.create(op.get_bind(), checkfirst=True)

    # brands
    op.create_table(
        "brands",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("voice", sa.Text),
        sa.Column("visual_guidelines", sa.Text),
        sa.Column("offers", postgresql.JSONB),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # products
    op.create_table(
        "products",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("brand_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("brands.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("price", sa.Numeric(10, 2)),
        sa.Column("image_url", sa.String(2048)),
    )

    # audiences
    op.create_table(
        "audiences",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("brand_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("brands.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("demographics", sa.Text),
        sa.Column("interests", sa.Text),
    )

    # jobs
    op.create_table(
        "jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("pipeline_name", sa.String(255), nullable=False),
        sa.Column("brand_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("brands.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", job_status, nullable=False, server_default="pending"),
        sa.Column("config", postgresql.JSONB),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
    )

    # job_steps
    op.create_table(
        "job_steps",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("step_name", sa.String(255), nullable=False),
        sa.Column("status", step_status, nullable=False, server_default="pending"),
        sa.Column("input", postgresql.JSONB),
        sa.Column("output", postgresql.JSONB),
        sa.Column("error", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
    )

    # outputs
    op.create_table(
        "outputs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("pipeline_name", sa.String(255), nullable=False),
        sa.Column("output_type", sa.String(100), nullable=False),
        sa.Column("file_path", sa.String(2048)),
        sa.Column("metadata", postgresql.JSONB),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # performance_metrics
    op.create_table(
        "performance_metrics",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("output_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("outputs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("impressions", sa.Integer),
        sa.Column("clicks", sa.Integer),
        sa.Column("ctr", sa.Float),
        sa.Column("conversions", sa.Integer),
        sa.Column("cpa", sa.Float),
        sa.Column("roas", sa.Float),
        sa.Column("simulated_at", sa.DateTime(timezone=True)),
    )

    # insights
    op.create_table(
        "insights",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("brand_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("brands.id", ondelete="CASCADE"), nullable=False),
        sa.Column("insight_type", sa.String(100), nullable=False),
        sa.Column("content", sa.Text),
        sa.Column("confidence", sa.Float),
        sa.Column("source_metrics", postgresql.JSONB),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # events
    op.create_table(
        "events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("payload", postgresql.JSONB),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # Indexes for common queries
    op.create_index("ix_jobs_brand_id", "jobs", ["brand_id"])
    op.create_index("ix_jobs_status", "jobs", ["status"])
    op.create_index("ix_job_steps_job_id", "job_steps", ["job_id"])
    op.create_index("ix_outputs_job_id", "outputs", ["job_id"])
    op.create_index("ix_events_job_id", "events", ["job_id"])
    op.create_index("ix_events_event_type", "events", ["event_type"])
    op.create_index("ix_insights_brand_id", "insights", ["brand_id"])
    op.create_index("ix_performance_metrics_output_id", "performance_metrics", ["output_id"])


def downgrade() -> None:
    op.drop_table("events")
    op.drop_table("insights")
    op.drop_table("performance_metrics")
    op.drop_table("outputs")
    op.drop_table("job_steps")
    op.drop_table("jobs")
    op.drop_table("audiences")
    op.drop_table("products")
    op.drop_table("brands")
    step_status.drop(op.get_bind(), checkfirst=True)
    job_status.drop(op.get_bind(), checkfirst=True)
