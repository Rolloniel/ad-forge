"""Tests for the pipeline engine: job creation, step execution, failure handling."""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.engine.pipeline_engine import create_job
from app.engine.job_worker import execute_job
from app.models.brand import Brand
from app.models.job import Job, JobStatus, JobStep, StepStatus
from app.models.user import User
from app.pipelines import PipelineDefinition, REGISTRY as _registry


BRAND_ID = uuid.UUID("a1b2c3d4-e5f6-7890-abcd-ef1234567890")
USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000099")


@pytest.fixture(autouse=True)
def clean_registry():
    """Ensure test pipelines don't leak between tests."""
    saved = dict(_registry)
    yield
    _registry.clear()
    _registry.update(saved)


@pytest.fixture
async def brand(session: AsyncSession) -> Brand:
    user = User(id=USER_ID, name="PipelineTestUser", is_admin=False)
    session.add(user)
    await session.flush()
    brand = Brand(id=BRAND_ID, name="TestBrand", user_id=USER_ID)
    session.add(brand)
    await session.commit()
    return brand


# ---------------------------------------------------------------------------
# create_job
# ---------------------------------------------------------------------------


async def test_create_job_success(session: AsyncSession, brand):
    async def step_a(*, job_id, config, prev_outputs, session):
        return {"a": 1}

    _registry["demo"] = PipelineDefinition(
        name="demo", steps=[("step_a", step_a)]
    )

    job = await create_job(session, "demo", BRAND_ID, {"key": "val"})
    await session.commit()

    assert job.pipeline_name == "demo"
    assert job.status == JobStatus.pending
    assert job.config == {"key": "val"}

    # Verify steps were created
    result = await session.execute(select(JobStep).where(JobStep.job_id == job.id))
    steps = result.scalars().all()
    assert len(steps) == 1
    assert steps[0].step_name == "step_a"


async def test_create_job_unknown_pipeline(session: AsyncSession, brand):
    with pytest.raises(ValueError, match="Unknown pipeline"):
        await create_job(session, "nonexistent", BRAND_ID)


# ---------------------------------------------------------------------------
# execute_job — happy path
# ---------------------------------------------------------------------------


@patch("app.engine.job_worker.notify_step_event", new_callable=AsyncMock)
async def test_execute_job_success(mock_notify, session: AsyncSession, brand):
    async def step_a(*, job_id, config, prev_outputs, session):
        return {"from_a": True}

    async def step_b(*, job_id, config, prev_outputs, session):
        return {"from_b": True, "got_a": prev_outputs.get("step_a", {}).get("from_a")}

    _registry["two_step"] = PipelineDefinition(
        name="two_step",
        steps=[("step_a", step_a), ("step_b", step_b)],
    )

    job = await create_job(session, "two_step", BRAND_ID, {})
    await session.commit()

    result = await session.execute(select(JobStep).where(JobStep.job_id == job.id))
    steps = list(result.scalars().all())

    await execute_job(job, steps, session)

    assert job.status == JobStatus.completed
    assert job.started_at is not None
    assert job.completed_at is not None

    # Reload steps to check output
    result = await session.execute(
        select(JobStep).where(JobStep.job_id == job.id).order_by(JobStep.step_name)
    )
    steps = result.scalars().all()
    completed_steps = [s for s in steps if s.status == StepStatus.completed]
    assert len(completed_steps) == 2

    step_b_row = next(s for s in steps if s.step_name == "step_b")
    assert step_b_row.output["got_a"] is True


# ---------------------------------------------------------------------------
# execute_job — step chaining (output forwarded)
# ---------------------------------------------------------------------------


@patch("app.engine.job_worker.notify_step_event", new_callable=AsyncMock)
async def test_step_output_chaining(mock_notify, session: AsyncSession, brand):
    async def first(*, job_id, config, prev_outputs, session):
        return {"x": 42}

    async def second(*, job_id, config, prev_outputs, session):
        return {"doubled": prev_outputs["first"]["x"] * 2}

    _registry["chain"] = PipelineDefinition(
        name="chain",
        steps=[("first", first), ("second", second)],
    )

    job = await create_job(session, "chain", BRAND_ID, {})
    await session.commit()

    result = await session.execute(select(JobStep).where(JobStep.job_id == job.id))
    steps = list(result.scalars().all())

    await execute_job(job, steps, session)

    result = await session.execute(
        select(JobStep).where(JobStep.job_id == job.id, JobStep.step_name == "second")
    )
    step = result.scalar_one()
    assert step.output["doubled"] == 84


# ---------------------------------------------------------------------------
# execute_job — failure handling
# ---------------------------------------------------------------------------


@patch("app.engine.job_worker.notify_step_event", new_callable=AsyncMock)
async def test_execute_job_step_failure(mock_notify, session: AsyncSession, brand):
    async def good_step(*, job_id, config, prev_outputs, session):
        return {"ok": True}

    async def bad_step(*, job_id, config, prev_outputs, session):
        raise RuntimeError("boom")

    _registry["fail_pipe"] = PipelineDefinition(
        name="fail_pipe",
        steps=[("good", good_step), ("bad", bad_step)],
    )

    job = await create_job(session, "fail_pipe", BRAND_ID, {})
    await session.commit()

    result = await session.execute(select(JobStep).where(JobStep.job_id == job.id))
    steps = list(result.scalars().all())

    await execute_job(job, steps, session)

    assert job.status == JobStatus.failed
    assert job.completed_at is not None

    result = await session.execute(
        select(JobStep).where(JobStep.job_id == job.id, JobStep.step_name == "bad")
    )
    bad = result.scalar_one()
    assert bad.status == StepStatus.failed
    assert "boom" in bad.error


@patch("app.engine.job_worker.notify_step_event", new_callable=AsyncMock)
async def test_execute_job_unknown_pipeline(mock_notify, session: AsyncSession, brand):
    """If pipeline was removed after job creation, job should be marked failed."""
    _registry["ephemeral"] = PipelineDefinition(
        name="ephemeral", steps=[("s", AsyncMock(return_value={}))]
    )

    job = await create_job(session, "ephemeral", BRAND_ID, {})
    await session.commit()

    result = await session.execute(select(JobStep).where(JobStep.job_id == job.id))
    steps = list(result.scalars().all())

    # Remove from registry before execution
    del _registry["ephemeral"]

    await execute_job(job, steps, session)
    assert job.status == JobStatus.failed


# ---------------------------------------------------------------------------
# execute_job — config passed to first step
# ---------------------------------------------------------------------------


@patch("app.engine.job_worker.notify_step_event", new_callable=AsyncMock)
async def test_config_passed_as_initial_input(mock_notify, session: AsyncSession, brand):
    received = {}

    async def capture(*, job_id, config, prev_outputs, session):
        received.update(config)
        return {"done": True}

    _registry["cfg_pipe"] = PipelineDefinition(
        name="cfg_pipe", steps=[("capture", capture)]
    )

    config = {"campaign_goal": "awareness", "platform": "instagram"}
    job = await create_job(session, "cfg_pipe", BRAND_ID, config)
    await session.commit()

    result = await session.execute(select(JobStep).where(JobStep.job_id == job.id))
    steps = list(result.scalars().all())

    await execute_job(job, steps, session)

    assert received["campaign_goal"] == "awareness"
    assert received["platform"] == "instagram"
