from __future__ import annotations

import uuid
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import Job, JobStatus, JobStep

StepFunc = Callable[[dict, dict], Coroutine[Any, Any, dict]]


@dataclass
class StepDef:
    name: str
    func: StepFunc


@dataclass
class PipelineDef:
    name: str
    steps: list[StepDef] = field(default_factory=list)


_registry: dict[str, PipelineDef] = {}


def register_pipeline(name: str, steps: list[tuple[str, StepFunc]]) -> None:
    _registry[name] = PipelineDef(
        name=name,
        steps=[StepDef(n, f) for n, f in steps],
    )


def get_pipeline(name: str) -> PipelineDef | None:
    return _registry.get(name)


def list_pipelines() -> list[str]:
    return list(_registry.keys())


async def create_job(
    session: AsyncSession,
    pipeline_name: str,
    brand_id: uuid.UUID,
    config: dict | None = None,
) -> Job:
    pipeline = _registry.get(pipeline_name)
    if pipeline is None:
        raise ValueError(f"Unknown pipeline: {pipeline_name}")

    job = Job(
        pipeline_name=pipeline_name,
        brand_id=brand_id,
        status=JobStatus.pending,
        config=config,
    )
    session.add(job)
    await session.flush()

    for step_def in pipeline.steps:
        step = JobStep(job_id=job.id, step_name=step_def.name)
        session.add(step)

    await session.flush()
    return job
