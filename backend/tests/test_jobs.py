"""Tests for job creation, listing, and status routes."""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from tests.conftest import SEED_BRAND_ID


# Register a simple test pipeline in the engine registry so routes can find it.
def _register_test_pipeline():
    from app.engine.pipeline_engine import StepDef, PipelineDef, _registry

    async def noop_step(prev: dict, config: dict) -> dict:
        return {"result": "ok"}

    if "test_pipe" not in _registry:
        _registry["test_pipe"] = PipelineDef(
            name="test_pipe",
            steps=[StepDef("step_one", noop_step)],
        )


@pytest.fixture(autouse=True)
def register_pipeline():
    _register_test_pipeline()


async def test_run_pipeline_creates_job(authed_client: AsyncClient, seed_brand):
    resp = await authed_client.post(
        "/api/pipelines/test_pipe/run",
        json={"brand_id": str(SEED_BRAND_ID)},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["pipeline_name"] == "test_pipe"
    assert data["status"] == "pending"
    assert data["brand_id"] == str(SEED_BRAND_ID)
    assert len(data["steps"]) == 1
    assert data["steps"][0]["step_name"] == "step_one"


async def test_run_pipeline_unknown_returns_404(authed_client: AsyncClient, seed_brand):
    resp = await authed_client.post(
        "/api/pipelines/nonexistent/run",
        json={"brand_id": str(SEED_BRAND_ID)},
    )
    assert resp.status_code == 404


async def test_list_jobs_empty(authed_client: AsyncClient):
    resp = await authed_client.get("/api/jobs")
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0


async def test_list_jobs_after_create(authed_client: AsyncClient, seed_brand):
    # Create a job first
    await authed_client.post(
        "/api/pipelines/test_pipe/run",
        json={"brand_id": str(SEED_BRAND_ID)},
    )
    resp = await authed_client.get("/api/jobs")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert data["items"][0]["pipeline_name"] == "test_pipe"


async def test_list_jobs_filter_by_pipeline(authed_client: AsyncClient, seed_brand):
    await authed_client.post(
        "/api/pipelines/test_pipe/run",
        json={"brand_id": str(SEED_BRAND_ID)},
    )
    resp = await authed_client.get("/api/jobs", params={"pipeline": "test_pipe"})
    assert resp.status_code == 200
    assert resp.json()["total"] >= 1

    resp = await authed_client.get("/api/jobs", params={"pipeline": "other"})
    assert resp.json()["total"] == 0


async def test_list_jobs_filter_by_status(authed_client: AsyncClient, seed_brand):
    await authed_client.post(
        "/api/pipelines/test_pipe/run",
        json={"brand_id": str(SEED_BRAND_ID)},
    )
    resp = await authed_client.get("/api/jobs", params={"status": "pending"})
    assert resp.status_code == 200
    assert resp.json()["total"] >= 1

    resp = await authed_client.get("/api/jobs", params={"status": "completed"})
    assert resp.json()["total"] == 0


async def test_get_job_by_id(authed_client: AsyncClient, seed_brand):
    create_resp = await authed_client.post(
        "/api/pipelines/test_pipe/run",
        json={"brand_id": str(SEED_BRAND_ID)},
    )
    job_id = create_resp.json()["id"]

    resp = await authed_client.get(f"/api/jobs/{job_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == job_id
    assert "steps" in data


async def test_get_job_not_found(authed_client: AsyncClient):
    fake_id = uuid.uuid4()
    resp = await authed_client.get(f"/api/jobs/{fake_id}")
    assert resp.status_code == 404


async def test_list_jobs_pagination(authed_client: AsyncClient, seed_brand):
    # Create 3 jobs
    for _ in range(3):
        await authed_client.post(
            "/api/pipelines/test_pipe/run",
            json={"brand_id": str(SEED_BRAND_ID)},
        )

    resp = await authed_client.get("/api/jobs", params={"page": 1, "page_size": 2})
    data = resp.json()
    assert data["total"] == 3
    assert len(data["items"]) == 2
    assert data["page"] == 1
    assert data["page_size"] == 2

    resp = await authed_client.get("/api/jobs", params={"page": 2, "page_size": 2})
    data = resp.json()
    assert len(data["items"]) == 1
