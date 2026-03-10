from __future__ import annotations

import json
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.db import async_session, get_session
from app.engine import job_queue
from app.engine.event_bus import listen_job_events
from app.engine.pipeline_engine import create_job
from app.models.brand import Brand
from app.models.job import Job
from app.models.user import User
from app.routes.auth import _lookup_user_by_key, require_auth

router = APIRouter(prefix="/api", tags=["jobs"])


class RunPipelineRequest(BaseModel):
    brand_id: uuid.UUID
    config: dict | None = None


class StepResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    step_name: str
    status: str
    input: dict | None = None
    output: dict | None = None
    error: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


class JobResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    pipeline_name: str
    brand_id: uuid.UUID
    status: str
    config: dict | None = None
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None


class JobDetailResponse(JobResponse):
    steps: list[StepResponse] = []


class JobListResponse(BaseModel):
    items: list[JobResponse]
    total: int
    page: int
    page_size: int


@router.post("/pipelines/{name}/run", response_model=JobDetailResponse, status_code=201)
async def run_pipeline(
    name: str,
    body: RunPipelineRequest,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_auth),
):
    try:
        query = (
            select(Brand).where(Brand.id == body.brand_id)
            .options(selectinload(Brand.products), selectinload(Brand.audiences))
        )
        if not user.is_admin:
            query = query.where(Brand.user_id == user.id)
        brand = (await session.execute(query)).scalar_one_or_none()
        if brand is None:
            raise HTTPException(status_code=404, detail=f"Brand {body.brand_id} not found")

        config = {
            **(body.config or {}),
            "brand_id": str(body.brand_id),
            "brand": {"name": brand.name, "voice": brand.voice or ""},
        }
        job = await create_job(session, name, body.brand_id, config)
        await session.commit()
        await job_queue.put(str(job.id))
        await session.refresh(job, ["steps"])
        return job
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/jobs", response_model=JobListResponse)
async def list_jobs(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_auth),
    status: str | None = None,
    pipeline: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    query = select(Job)
    count_query = select(func.count()).select_from(Job)

    if not user.is_admin:
        query = query.join(Brand, Job.brand_id == Brand.id).where(Brand.user_id == user.id)
        count_query = count_query.join(Brand, Job.brand_id == Brand.id).where(Brand.user_id == user.id)

    if status:
        query = query.where(Job.status == status)
        count_query = count_query.where(Job.status == status)
    if pipeline:
        query = query.where(Job.pipeline_name == pipeline)
        count_query = count_query.where(Job.pipeline_name == pipeline)

    total = (await session.execute(count_query)).scalar()

    query = query.order_by(Job.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await session.execute(query)
    jobs = list(result.scalars().all())

    return JobListResponse(items=jobs, total=total, page=page, page_size=page_size)


@router.get("/jobs/{job_id}", response_model=JobDetailResponse)
async def get_job(
    job_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_auth),
):
    query = select(Job).where(Job.id == job_id).options(selectinload(Job.steps))
    if not user.is_admin:
        query = query.join(Brand, Job.brand_id == Brand.id).where(Brand.user_id == user.id)
    result = await session.execute(query)
    job = result.scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/jobs/{job_id}/events")
async def job_events_sse(
    job_id: uuid.UUID,
    token: str | None = Query(None),
    authorization: str | None = Header(None),
):
    # Extract token from header or query param
    raw_token = None
    if authorization and authorization.startswith("Bearer "):
        raw_token = authorization.removeprefix("Bearer ")
    elif token:
        raw_token = token

    if not raw_token:
        raise HTTPException(
            status_code=401,
            detail="Provide Authorization header or token query parameter",
        )

    async with async_session() as session:
        user = await _lookup_user_by_key(session, raw_token)
        if user is None:
            raise HTTPException(status_code=401, detail="Invalid or expired token")

        query = select(Job).where(Job.id == job_id)
        if not user.is_admin:
            query = query.join(Brand, Job.brand_id == Brand.id).where(Brand.user_id == user.id)
        result = await session.execute(query)
        if result.scalar_one_or_none() is None:
            raise HTTPException(status_code=404, detail="Job not found")

    dsn = settings.database_url.replace("+asyncpg", "")

    async def event_stream():
        async for event in listen_job_events(dsn):
            if event.get("job_id") == str(job_id):
                yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
