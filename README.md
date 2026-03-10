# AdForge

AI-powered creative infrastructure that generates, tests, and iterates eCommerce ad creatives at scale.

Built as a proof-of-concept demonstrating 6 core systems: video UGC, static ads, creative briefs, landing pages, ad copy, and performance feedback loops.

Ships with **GlowVita** — a fictional DTC premium skincare brand — as seed data so the system is demo-ready on first deploy.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Next.js Frontend (port 3000)                 │
│  Login │ Dashboard │ Pipeline Runner │ Gallery │ Analytics      │
└──────────────────────────┬──────────────────────────────────────┘
                           │ REST API + SSE
┌──────────────────────────┴──────────────────────────────────────┐
│                  FastAPI Backend (port 8000)                     │
│                                                                  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │ Pipeline  │ │  Job     │ │ Event    │ │ API      │           │
│  │ Engine    │ │ Workers  │ │ Bus      │ │ Routes   │           │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘           │
│                                                                  │
│  ┌────────────────────────────────────────────────────────┐     │
│  │              Pipeline Modules                          │     │
│  │  video_ugc │ static_ads │ briefs │ landing_pages      │     │
│  │  ad_copy   │ feedback_loop                             │     │
│  └────────────────────────────────────────────────────────┘     │
│                                                                  │
│  ┌────────────────────────────────────────────────────────┐     │
│  │              Integrations                              │     │
│  │  OpenAI │ FAL.ai │ HeyGen │ ElevenLabs               │     │
│  └────────────────────────────────────────────────────────┘     │
└──────────────────────────┬──────────────────────────────────────┘
                           │
              PostgreSQL (jobs, outputs, metrics, events, brands)
```

**Key decisions:**

- Python/FastAPI + Next.js monorepo
- PostgreSQL for everything: job queue, event bus, metadata, analytics — no Redis, no Celery
- Job queue via `SELECT ... FOR UPDATE SKIP LOCKED`
- Real-time updates via PostgreSQL `LISTEN/NOTIFY` → SSE to frontend
- Generated files stored on local disk, paths tracked in PostgreSQL

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | Next.js 15, React 19, TypeScript, Tailwind CSS v4, shadcn/ui, Recharts |
| Backend | FastAPI, Python 3.12, SQLAlchemy 2.0 (async), asyncpg, Pydantic |
| Database | PostgreSQL 16 |
| AI/ML | OpenAI GPT-4o, FAL.ai (Flux Pro, Kling), HeyGen, ElevenLabs |
| Infra | Docker, Docker Compose |

## Quick Start

```bash
# 1. Clone and configure
cp .env.example .env
# Edit .env with your API keys

# 2. Start everything
docker compose up --build

# 3. Open the app
# Frontend: http://localhost:3000
# Backend:  http://localhost:8000
# Health:   http://localhost:8000/health
```

Create a user and API key with the CLI, then log in with the generated key:

```bash
docker compose exec backend python -m app.cli create-user "Admin" --admin
```

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `POSTGRES_USER` | PostgreSQL username | Yes |
| `POSTGRES_PASSWORD` | PostgreSQL password | Yes |
| `DATABASE_URL` | PostgreSQL connection string | Yes |
| `OPENAI_API_KEY` | OpenAI API key (GPT-4o) | Yes |
| `FAL_KEY` | FAL.ai API key (image/video generation) | Yes |
| `HEYGEN_API_KEY` | HeyGen API key (avatar video) | Yes |
| `ELEVENLABS_API_KEY` | ElevenLabs API key (text-to-speech) | Yes |
| `WORKER_COUNT` | Number of concurrent pipeline workers | No (default: 3) |

## API Overview

```
# Auth
POST   /api/auth/validate              Validate API key

# Pipelines & Jobs
POST   /api/pipelines/{name}/run       Launch a pipeline job
GET    /api/jobs                        List jobs (filtered, paginated)
GET    /api/jobs/{id}                   Job status + step states
GET    /api/jobs/{id}/events            SSE stream of job events

# Outputs
GET    /api/outputs                     List outputs (filtered by pipeline, type, date)
GET    /api/outputs/{id}                Single output with metadata
GET    /api/outputs/{id}/file           Serve the generated file

# Brands
GET    /api/brands                      List brands
POST   /api/brands                      Create brand
GET    /api/brands/{id}                 Brand details
PUT    /api/brands/{id}                 Update brand

# Health
GET    /health                          Health check
```

## Project Structure

```
adforge/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI app, lifespan, CORS
│   │   ├── config.py               # Settings from env vars (pydantic-settings)
│   │   ├── db.py                   # Async SQLAlchemy engine + session
│   │   ├── models/                 # SQLAlchemy ORM models
│   │   ├── routes/                 # API route handlers
│   │   ├── engine/                 # Pipeline engine, job workers, event bus
│   │   ├── pipelines/              # Pipeline module definitions
│   │   ├── integrations/           # External API clients
│   │   └── seed/                   # GlowVita seed data
│   ├── alembic/                    # Database migrations
│   ├── Dockerfile
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── app/                    # Next.js app router pages
│   │   ├── components/             # UI components (sidebar, shadcn/ui)
│   │   ├── lib/                    # API client, SSE hook, utils
│   │   └── types/                  # TypeScript interfaces
│   ├── Dockerfile
│   └── package.json
├── docs/plans/                     # Design documents
├── docker-compose.yml
└── .env.example
```

## Pipeline Modules

| Pipeline | Description | Status |
|----------|-------------|--------|
| **Creative Briefs** | Structured briefs from product data + past performance | Implemented |
| **Ad Copy** | Copy variations + testing matrices + mock deployment payloads | Implemented |
| **Video UGC** | Avatar/voiceover UGC video ads | Integration clients ready |
| **Static Ads** | Ad-ready images with copy overlays | Integration clients ready |
| **Landing Pages** | High-converting landing page content | Integration clients ready |
| **Feedback Loop** | Simulated performance metrics + optimization insights | Planned |

## Deployment

Designed for single-domain deployment at `adforge.kliuiev.com` with path-based routing:

- `/api/*` → FastAPI backend (port 8000)
- Everything else → Next.js frontend (port 3000)

Both services have multi-stage Dockerfiles optimized for production. Deploy via Docker Compose or as individual containers behind a reverse proxy.
