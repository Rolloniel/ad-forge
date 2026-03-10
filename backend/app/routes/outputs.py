from __future__ import annotations

import mimetypes
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import get_session
from app.models.brand import Brand
from app.models.job import Job
from app.models.output import Output
from app.models.user import User
from app.routes.auth import require_auth

router = APIRouter(prefix="/api/outputs", tags=["outputs"])


class OutputResponse(BaseModel):
    id: uuid.UUID
    job_id: uuid.UUID
    pipeline_name: str
    output_type: str
    file_path: str | None
    metadata: dict[str, Any] | None
    created_at: datetime

    model_config = {"from_attributes": True}


class OutputListResponse(BaseModel):
    items: list[OutputResponse]
    total: int
    page: int
    page_size: int


def _output_to_response(output: Output) -> OutputResponse:
    return OutputResponse(
        id=output.id,
        job_id=output.job_id,
        pipeline_name=output.pipeline_name,
        output_type=output.output_type,
        file_path=output.file_path,
        metadata=output.metadata_,
        created_at=output.created_at,
    )


@router.get("", response_model=OutputListResponse)
async def list_outputs(
    pipeline_name: str | None = Query(None),
    output_type: str | None = Query(None),
    created_after: datetime | None = Query(None),
    created_before: datetime | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_auth),
) -> OutputListResponse:
    """List outputs with optional filters and pagination."""
    filters = []
    if pipeline_name is not None:
        filters.append(Output.pipeline_name == pipeline_name)
    if output_type is not None:
        filters.append(Output.output_type == output_type)
    if created_after is not None:
        filters.append(Output.created_at >= created_after)
    if created_before is not None:
        filters.append(Output.created_at <= created_before)

    count_query = select(func.count(Output.id)).where(*filters)
    data_query = (
        select(Output)
        .where(*filters)
        .order_by(Output.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )

    if not user.is_admin:
        count_query = count_query.join(Job, Output.job_id == Job.id).join(Brand, Job.brand_id == Brand.id).where(Brand.user_id == user.id)
        data_query = data_query.join(Job, Output.job_id == Job.id).join(Brand, Job.brand_id == Brand.id).where(Brand.user_id == user.id)

    count_result = await session.execute(count_query)
    total = count_result.scalar_one()

    result = await session.execute(data_query)
    outputs = result.scalars().all()

    return OutputListResponse(
        items=[_output_to_response(o) for o in outputs],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{output_id}", response_model=OutputResponse)
async def get_output(
    output_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_auth),
) -> OutputResponse:
    """Get a single output with full metadata."""
    query = (
        select(Output)
        .where(Output.id == output_id)
        .options(selectinload(Output.performance_metrics))
    )
    if not user.is_admin:
        query = query.join(Job, Output.job_id == Job.id).join(Brand, Job.brand_id == Brand.id).where(Brand.user_id == user.id)
    result = await session.execute(query)
    output = result.scalar_one_or_none()
    if output is None:
        raise HTTPException(status_code=404, detail="Output not found")
    return _output_to_response(output)


@router.get("/{output_id}/file")
async def get_output_file(
    output_id: uuid.UUID,
    download: bool = Query(False),
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_auth),
) -> FileResponse:
    """Serve the actual generated file from local disk."""
    query = select(Output).where(Output.id == output_id)
    if not user.is_admin:
        query = query.join(Job, Output.job_id == Job.id).join(Brand, Job.brand_id == Brand.id).where(Brand.user_id == user.id)
    result = await session.execute(query)
    output = result.scalar_one_or_none()
    if output is None:
        raise HTTPException(status_code=404, detail="Output not found")

    if not output.file_path:
        raise HTTPException(status_code=404, detail="Output has no associated file")

    file = Path(output.file_path)
    if not file.is_file():
        raise HTTPException(status_code=404, detail="File not found on disk")

    media_type = mimetypes.guess_type(file.name)[0] or "application/octet-stream"

    headers = {}
    if download:
        headers["Content-Disposition"] = f'attachment; filename="{file.name}"'

    return FileResponse(
        path=file,
        media_type=media_type,
        headers=headers,
    )
