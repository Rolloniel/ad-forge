# AdForge

AI-powered ad creative generation platform. FastAPI backend + Next.js frontend monorepo.

## Project Structure

- `backend/app/main.py` — FastAPI app entry point, lifespan (worker startup/shutdown), CORS
- `backend/app/config.py` — `Settings` via pydantic-settings, all env vars
- `backend/app/db.py` — Async SQLAlchemy engine, `async_sessionmaker`, `get_session` dependency
- `backend/app/models/` — SQLAlchemy 2.0 declarative models (Brand, Product, Audience, Job, JobStep, Output, PerformanceMetric, Event, Insight)
- `backend/app/routes/` — FastAPI routers: auth, brands, jobs, outputs
- `backend/app/engine/` — Pipeline engine (`pipeline_engine.py`), job worker pool (`job_worker.py`), PostgreSQL LISTEN/NOTIFY event bus (`event_bus.py`)
- `backend/app/pipelines/` — Pipeline definitions with step handlers (briefs, ad_copy)
- `backend/app/integrations/` — Async API clients: OpenAI, FAL.ai, HeyGen, ElevenLabs
- `backend/app/seed/` — GlowVita seed data
- `backend/alembic/` — Database migrations
- `frontend/src/app/` — Next.js 15 app router pages
- `frontend/src/components/` — Sidebar + shadcn/ui components
- `frontend/src/lib/` — API client (`api.ts`), SSE hook (`use-sse.ts`), utils
- `frontend/src/types/` — TypeScript interfaces matching API contracts

## Commands

```bash
# Start all services
docker compose up --build

# Backend only (local dev)
cd backend && pip install -e . && uvicorn app.main:app --reload --port 8000

# Frontend only (local dev)
cd frontend && npm install && npm run dev

# Database migrations
cd backend && alembic upgrade head

# Type checking (frontend)
cd frontend && npx tsc --noEmit
```

## Deployment

- **Backend Coolify UUID:** `e8cwwkoogo0osss804ks8s8w`
- **Frontend Coolify UUID:** `vwk88w0g0s4woo4cgg44kwgs`
- **Backend URL:** `https://api-adforge.kliuiev.com`
- **Frontend URL:** `https://adforge.kliuiev.com`

## Code Patterns

### Backend (Python)

**Async everywhere.** All database queries use `AsyncSession`, all HTTP calls use `httpx.AsyncClient`, all I/O is non-blocking.

```python
# Dependency injection pattern for database sessions
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session

@router.get("/items")
async def list_items(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Item))
    return result.scalars().all()
```

**SQLAlchemy 2.0 declarative models** with `Mapped[]` type annotations:

```python
class Brand(Base):
    __tablename__ = "brands"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255))
    products: Mapped[list["Product"]] = relationship(back_populates="brand", cascade="all, delete-orphan")
```

**Pipeline step signature:**

```python
async def step_handler(
    *,
    job_id: UUID,
    config: dict[str, Any],
    prev_outputs: dict[str, dict[str, Any]],
    session: AsyncSession,
) -> dict[str, Any]:
    ...
```

Steps receive keyword-only args. `prev_outputs` maps step names to their return dicts (output chaining). Return value becomes input for next step.

**Auth:** Bearer token via `require_auth` dependency. Per-user API keys stored in database, managed via CLI (`python -m app.cli create-user`).

### Frontend (TypeScript/React)

**Next.js 15 App Router** with route groups:
- `(dashboard)/` group wraps authenticated pages with sidebar layout
- `login/` is outside the group (no sidebar)
- Root `/` redirects to `/dashboard`

**API client** (`lib/api.ts`): `ApiClient` class reads API key from cookie, adds `Authorization: Bearer` header to all requests.

**SSE hook** (`lib/use-sse.ts`): `useSSE()` connects to `EventSource`, parses JSON events, provides `events[]`, `connected`, `error` state.

**shadcn/ui** components in `components/ui/`. Use `components.json` config. Import as `@/components/ui/button`.

**Path alias:** `@/*` maps to `src/*`.

## Important Files

- `backend/app/models/base.py` — `Base` declarative base, `TimestampMixin`
- `backend/app/engine/pipeline_engine.py` — `create_job()`, pipeline registry
- `backend/app/engine/job_worker.py` — `execute_job()`, `worker_loop()`, `claim_job()` (FOR UPDATE SKIP LOCKED)
- `backend/app/engine/event_bus.py` — `notify_step_event()` (pg_notify), `listen_job_events()` (asyncpg listener)
- `backend/app/pipelines/__init__.py` — `PipelineDefinition`, `REGISTRY`, `register()`
- `frontend/src/types/index.ts` — All TypeScript interfaces for API models
- `frontend/src/lib/api.ts` — Centralized fetch wrapper with auth
- `docs/plans/2026-03-08-adforge-poc-design.md` — Full design document
