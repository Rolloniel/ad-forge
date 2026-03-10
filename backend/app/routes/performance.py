"""Performance feedback loop routes.

POST /api/performance/simulate — trigger the feedback loop pipeline
GET  /api/performance/insights  — query insights for a brand
GET  /api/performance/metrics   — query performance metrics
"""
from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.engine import job_queue
from app.engine.pipeline_engine import create_job
from app.models import Insight, Output, PerformanceMetric
from app.models.brand import Brand
from app.models.user import User
from app.routes.auth import require_auth

router = APIRouter(prefix="/api/performance", tags=["performance"])


# ---------- Schemas ----------


class SimulateRequest(BaseModel):
    brand_id: uuid.UUID
    source_job_id: uuid.UUID | None = None
    output_count: int = 10
    seed: int | None = None


class SimulateResponse(BaseModel):
    job_id: uuid.UUID
    pipeline_name: str
    status: str


class InsightOut(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    brand_id: uuid.UUID
    insight_type: str
    content: str | None = None
    confidence: float | None = None
    source_metrics: dict | None = None
    created_at: datetime


class InsightListResponse(BaseModel):
    items: list[InsightOut]
    total: int


class MetricOut(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    output_id: uuid.UUID
    impressions: int | None = None
    clicks: int | None = None
    ctr: float | None = None
    conversions: int | None = None
    cpa: float | None = None
    roas: float | None = None
    simulated_at: datetime | None = None


class MetricListResponse(BaseModel):
    items: list[MetricOut]
    total: int


# ---------- Routes ----------


@router.post("/simulate", response_model=SimulateResponse, status_code=201)
async def simulate_performance(
    body: SimulateRequest,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_auth),
):
    """Trigger the performance feedback loop pipeline."""
    # Verify brand belongs to user
    if not user.is_admin:
        brand_result = await session.execute(
            select(Brand.id).where(Brand.id == body.brand_id, Brand.user_id == user.id)
        )
        if brand_result.scalar_one_or_none() is None:
            raise HTTPException(status_code=404, detail="Brand not found")

    config = {
        "brand_id": str(body.brand_id),
        "output_count": body.output_count,
    }
    if body.source_job_id:
        config["source_job_id"] = str(body.source_job_id)
    if body.seed is not None:
        config["seed"] = body.seed

    try:
        job = await create_job(session, "feedback_loop", body.brand_id, config)
        # Inject job_id into config so pipeline steps can reference it
        config["job_id"] = str(job.id)
        job.config = config
        await session.commit()
        await job_queue.put(str(job.id))
        return SimulateResponse(
            job_id=job.id,
            pipeline_name="feedback_loop",
            status="pending",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/insights", response_model=InsightListResponse)
async def get_insights(
    brand_id: uuid.UUID = Query(...),
    insight_type: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_auth),
):
    """Query insights for a brand, optionally filtered by type."""
    # Verify brand belongs to user
    if not user.is_admin:
        brand_result = await session.execute(
            select(Brand.id).where(Brand.id == brand_id, Brand.user_id == user.id)
        )
        if brand_result.scalar_one_or_none() is None:
            raise HTTPException(status_code=404, detail="Brand not found")

    query = select(Insight).where(Insight.brand_id == brand_id)
    count_query = select(func.count()).select_from(Insight).where(
        Insight.brand_id == brand_id
    )

    if insight_type:
        query = query.where(Insight.insight_type == insight_type)
        count_query = count_query.where(Insight.insight_type == insight_type)

    total = (await session.execute(count_query)).scalar() or 0

    query = query.order_by(Insight.created_at.desc()).offset(offset).limit(limit)
    result = await session.execute(query)
    items = list(result.scalars().all())

    return InsightListResponse(items=items, total=total)


@router.get("/metrics", response_model=MetricListResponse)
async def get_metrics(
    brand_id: uuid.UUID = Query(...),
    output_id: uuid.UUID | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_auth),
):
    """Query performance metrics, filtered by brand or specific output."""
    # Verify brand belongs to user
    if not user.is_admin:
        brand_result = await session.execute(
            select(Brand.id).where(Brand.id == brand_id, Brand.user_id == user.id)
        )
        if brand_result.scalar_one_or_none() is None:
            raise HTTPException(status_code=404, detail="Brand not found")

    # Join through Output to filter by brand
    query = (
        select(PerformanceMetric)
        .join(Output, PerformanceMetric.output_id == Output.id)
    )
    count_query = (
        select(func.count())
        .select_from(PerformanceMetric)
        .join(Output, PerformanceMetric.output_id == Output.id)
    )

    # Filter by brand via output metadata or job's brand_id
    from app.models import Job

    query = query.join(Job, Output.job_id == Job.id).where(Job.brand_id == brand_id)
    count_query = count_query.join(Job, Output.job_id == Job.id).where(
        Job.brand_id == brand_id
    )

    if output_id:
        query = query.where(PerformanceMetric.output_id == output_id)
        count_query = count_query.where(PerformanceMetric.output_id == output_id)

    total = (await session.execute(count_query)).scalar() or 0

    query = (
        query.order_by(PerformanceMetric.simulated_at.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await session.execute(query)
    items = list(result.scalars().all())

    return MetricListResponse(items=items, total=total)
