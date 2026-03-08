from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.engine.job_worker import recover_pending_jobs, start_workers
from app.routes.auth import router as auth_router
from app.routes.brands import router as brands_router
from app.routes.jobs import router as jobs_router
from app.routes.deployment import router as deployment_router
from app.routes.outputs import router as outputs_router
from app.routes.performance import router as performance_router
import app.pipelines  # noqa: F401  — trigger pipeline registration


@asynccontextmanager
async def lifespan(app: FastAPI):
    await recover_pending_jobs()
    workers = start_workers(settings.worker_count)
    yield
    for task in workers:
        task.cancel()


app = FastAPI(title="AdForge", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(brands_router)
app.include_router(jobs_router)
app.include_router(deployment_router)
app.include_router(outputs_router)
app.include_router(performance_router)


@app.get("/health")
async def health():
    return {"status": "healthy"}
