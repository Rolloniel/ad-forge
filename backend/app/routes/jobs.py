from __future__ import annotations

import json
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
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
from app.models.job import Job

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
):
    try:
        job = await create_job(session, name, body.brand_id, body.config)
        await session.commit()
        await job_queue.put(str(job.id))
        await session.refresh(job, ["steps"])
        return job
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/jobs", response_model=JobListResponse)
async def list_jobs(
    session: AsyncSession = Depends(get_session),
    status: str | None = None,
    pipeline: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    query = select(Job)
    count_query = select(func.count()).select_from(Job)

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
):
    result = await session.execute(
        select(Job).where(Job.id == job_id).options(selectinload(Job.steps))
    )
    job = result.scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/jobs/{job_id}/events")
async def job_events_sse(job_id: uuid.UUID):
    async with async_session() as session:
        result = await session.execute(select(Job.id).where(Job.id == job_id))
        if result.scalar_one_or_none() is None:
            raise HTTPException(status_code=404, detail="Job not found")

    dsn = settings.database_url.replace("+asyncpg", "")

    async def event_stream():
        async for event in listen_job_events(dsn):
            if event.get("job_id") == str(job_id):
                yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
