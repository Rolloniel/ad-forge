from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import async_session
from app.engine import job_queue
from app.engine.event_bus import notify_step_event
from app.engine.pipeline_engine import get_pipeline
from app.models.job import Job, JobStatus, JobStep, StepStatus

logger = logging.getLogger(__name__)


async def claim_job(session: AsyncSession, job_id: str) -> Job | None:
    result = await session.execute(
        select(Job)
        .where(Job.id == job_id, Job.status == JobStatus.pending)
        .with_for_update(skip_locked=True)
    )
    return result.scalar_one_or_none()


async def execute_job(job: Job, steps: list[JobStep], session: AsyncSession) -> None:
    pipeline = get_pipeline(job.pipeline_name)
    if pipeline is None:
        job.status = JobStatus.failed
        await session.commit()
        return

    # Build step order and handler lookup from PipelineDefinition
    step_order = {name: i for i, (name, _) in enumerate(pipeline.steps)}
    step_funcs = {name: func for name, func in pipeline.steps}

    sorted_steps = sorted(steps, key=lambda s: step_order.get(s.step_name, 999))

    job.status = JobStatus.running
    job.started_at = datetime.now(timezone.utc)
    await session.commit()

    prev_outputs: dict[str, dict] = {}
    config = job.config or {}

    for step in sorted_steps:
        step_func = step_funcs.get(step.step_name)
        if step_func is None:
            step.status = StepStatus.failed
            step.error = f"No function registered for step '{step.step_name}'"
            step.completed_at = datetime.now(timezone.utc)
            job.status = JobStatus.failed
            job.completed_at = datetime.now(timezone.utc)
            await notify_step_event(session, str(job.id), step.step_name, "failed")
            await session.commit()
            return

        step.status = StepStatus.running
        step.started_at = datetime.now(timezone.utc)
        step.input = config
        await session.commit()

        try:
            result = await step_func(
                job_id=job.id,
                config=config,
                prev_outputs=prev_outputs,
                session=session,
            )
            step.status = StepStatus.completed
            step.output = result
            step.completed_at = datetime.now(timezone.utc)
            prev_outputs[step.step_name] = result
            output_preview = str(result)[:200] if result else None
            await notify_step_event(
                session, str(job.id), step.step_name, "completed", output_preview
            )
            await session.commit()
        except Exception as exc:
            logger.exception("Step %s failed for job %s", step.step_name, job.id)
            step.status = StepStatus.failed
            step.error = str(exc)
            step.completed_at = datetime.now(timezone.utc)
            job.status = JobStatus.failed
            job.completed_at = datetime.now(timezone.utc)
            await notify_step_event(session, str(job.id), step.step_name, "failed")
            await session.commit()
            return

    job.status = JobStatus.completed
    job.completed_at = datetime.now(timezone.utc)
    await session.commit()


async def worker_loop(worker_id: int) -> None:
    logger.info("Worker %d started", worker_id)
    while True:
        job_id = await job_queue.get()
        logger.info("Worker %d picked up job %s", worker_id, job_id)
        try:
            async with async_session() as session:
                job = await claim_job(session, job_id)
                if job is None:
                    logger.info("Worker %d: job %s already claimed", worker_id, job_id)
                    continue

                result = await session.execute(
                    select(JobStep).where(JobStep.job_id == job.id)
                )
                steps = list(result.scalars().all())
                await execute_job(job, steps, session)
                logger.info("Worker %d completed job %s", worker_id, job_id)
        except Exception:
            logger.exception("Worker %d error processing job %s", worker_id, job_id)
        finally:
            job_queue.task_done()


async def recover_pending_jobs() -> None:
    async with async_session() as session:
        result = await session.execute(
            select(Job.id).where(Job.status == JobStatus.pending)
        )
        for (job_id,) in result.all():
            await job_queue.put(str(job_id))
            logger.info("Recovered pending job %s", job_id)


def start_workers(count: int) -> list[asyncio.Task]:
    tasks = []
    for i in range(count):
        task = asyncio.create_task(worker_loop(i), name=f"job-worker-{i}")
        tasks.append(task)
    return tasks
