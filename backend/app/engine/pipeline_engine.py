from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import Job, JobStatus, JobStep


def get_pipeline(name: str):
    from app.pipelines import REGISTRY
    return REGISTRY.get(name)


def list_pipelines() -> list[str]:
    from app.pipelines import REGISTRY
    return list(REGISTRY.keys())


def register_pipeline(name: str, steps: list[tuple[str, Any]]) -> None:
    """Compatibility shim for pipelines using (prev_output, config) signature.

    Wraps each step function to match the standard
    ``(*, job_id, config, prev_outputs, session)`` calling convention,
    then registers via ``app.pipelines.register()``.
    """
    from app.pipelines import PipelineDefinition, register

    ordered_step_names = [sn for sn, _ in steps]

    def _wrap(fn, step_idx):
        prev_step_name = ordered_step_names[step_idx - 1] if step_idx > 0 else None

        async def wrapper(*, job_id, config, prev_outputs, session):
            if prev_step_name and prev_step_name in prev_outputs:
                prev_output = prev_outputs[prev_step_name]
            else:
                prev_output = config
            # Inject session into config so steps can create Output records
            config_with_session = {**config, "_session": session, "job_id": str(job_id)}
            return await fn(prev_output, config_with_session)

        return wrapper

    wrapped_steps = [
        (sn, _wrap(fn, i)) for i, (sn, fn) in enumerate(steps)
    ]
    register(PipelineDefinition(name=name, steps=wrapped_steps))


async def create_job(
    session: AsyncSession,
    pipeline_name: str,
    brand_id: uuid.UUID,
    config: dict | None = None,
) -> Job:
    pipeline = get_pipeline(pipeline_name)
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

    for step_name, _ in pipeline.steps:
        step = JobStep(job_id=job.id, step_name=step_name)
        session.add(step)

    await session.flush()
    return job
