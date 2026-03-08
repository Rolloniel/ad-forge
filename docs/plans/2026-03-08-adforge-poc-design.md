# AdForge POC Design

AI-powered creative infrastructure that generates, tests, and iterates eCommerce ad creatives at scale.

## Context

Built as a proof-of-concept for an Upwork engagement seeking a production-grade AI Generative Creative Systems Engineer. The POC demonstrates all 6 core systems requested: video UGC, static ads, creative briefs, landing pages, ad copy, and performance feedback loops.

Ships with "GlowVita" — a fictional DTC premium skincare supplement brand — as seed data so the system is demo-ready on first deploy.

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
- Python/FastAPI monorepo with Next.js frontend in the same repo
- PostgreSQL for everything: job queue, event bus, metadata, analytics — no Redis, no Celery
- Job queue via `FOR UPDATE SKIP LOCKED` on a jobs table
- Real-time updates via PostgreSQL `LISTEN/NOTIFY` → SSE to frontend
- Generated files stored on local disk, paths tracked in PostgreSQL
- Single domain (`adforge.kliuiev.com`) with path-based routing: `/api/*` → backend, everything else → frontend

## Pipeline Engine

The core abstraction. Every generation task is a pipeline — a directed acyclic graph of steps.

**Step types:**
- **Linear** — one input, one output
- **Fan-out** — one input, N outputs (batch variations)
- **Fan-in** — N inputs, aggregated output

Each pipeline module defines its steps as async functions. The engine executes them respecting the dependency graph, tracking per-step status in the jobs table. Steps receive a context object with brand data, previous step outputs, and configuration.

**Job lifecycle:** `pending → running → completed/failed`

Workers run as async tasks inside the FastAPI process. Concurrency controlled by `WORKER_COUNT` env var. Workers claim jobs via `SELECT ... FOR UPDATE SKIP LOCKED`. After each step, the worker updates step state and fires `NOTIFY job_events` for real-time SSE.

## Pipeline Modules

### 1. Video UGC Engine

Generate performance-focused UGC video ads from product data.

**Flow:** Generate UGC script (hook → body → CTA) by creative angle → generate voiceover via ElevenLabs → generate avatar video via HeyGen OR background video via FAL/Kling → composite with captions, subtitles, brand elements, CTA cards → output batch variations (hooks × avatars × CTAs).

**Inputs:** Product, target audience, creative angle, video style (avatar/voiceover/text-overlay), variation count.
**Outputs:** MP4 files, script text, SRT captions.
**APIs:** OpenAI (script), ElevenLabs (voice), HeyGen (avatar), FAL/Kling (background video).

### 2. Static Ad Creative Engine

Generate ad-ready static images with copy overlays.

**Flow:** Generate creative angle matrix from product data → generate ad copy variations (headline, subhead, CTA) per angle → generate base images via FAL/Flux Pro → compose final ads with text overlay, brand colors → output in standard dimensions (1080x1080, 1080x1920, 1200x628).

**Inputs:** Product, angles, dimensions, variation count.
**Outputs:** PNG/JPG files in standard ad dimensions, copy text.
**APIs:** OpenAI (copy), FAL/Flux Pro (images).

### 3. Creative Brief Generator

Generate structured creative briefs for other pipelines or human designers.

**Flow:** Analyze product data, positioning, and past performance metrics → generate brief (target audience, key messages, creative direction, tone, visual references, offer structure) → output as structured document.

**Inputs:** Product, campaign goal, performance data (optional).
**Outputs:** Structured JSON brief, rendered markdown.
**APIs:** OpenAI.

### 4. Landing Page Generator

Generate high-converting landing page content with structured sections.

**Flow:** Generate page strategy from product + offer positioning → generate section content (hero, social proof, benefits, objection handling, CTA blocks, FAQ) → generate section variations for A/B testing → output structured JSON + pre-rendered HTML.

**Inputs:** Product, offer, target audience, page type (long-form sales / lead gen / product).
**Outputs:** Structured JSON page definition, HTML, preview screenshot.
**APIs:** OpenAI (copy), FAL (hero images).

### 5. Ad Copy & Deployment Engine

Generate structured ad copy and mock deployment payloads.

**Flow:** Generate ad copy variations (primary text, headline, description, CTA) → build testing matrix (angles × copy variants × audiences) → generate mock Meta/TikTok API payloads (campaign → ad set → ad structure) → output deployment-ready packages.

**Inputs:** Product, campaign objective, budget, target audiences, creative assets from other pipelines.
**Outputs:** Copy variations, testing matrix, mock API payloads (JSON).
**APIs:** OpenAI.

### 6. Performance Feedback Loop

Simulate ad performance and feed insights back into generation.

**Flow:** After a batch is "deployed" (mocked), generate simulated performance metrics (impressions, clicks, CTR, conversions, CPA, ROAS) with realistic distributions → analyze winning hooks and losing angles → generate optimization recommendations → feed winning patterns as context into future pipeline runs.

**Data:** Performance metrics table linked to outputs. Insights table accumulates learnings. Future pipeline runs query recent insights to bias generation toward winning patterns (e.g., "hooks mentioning '30-day guarantee' have 2.3x CTR").

**Inputs:** Batch of outputs to evaluate.
**Outputs:** Performance dashboard data, optimization insights, updated generation context.

## Frontend (Next.js)

### Pages

1. **Login** — Single input field for API key. Validates against backend, sets cookie, redirects to dashboard.
2. **Dashboard** — Overview of recent pipeline runs, output counts, key performance metrics, system status.
3. **Pipeline Runner** — Select pipeline (or chain multiple), configure inputs (product, audience, angles, variation count), launch jobs, watch progress via live step-by-step visualization.
4. **Output Gallery** — Browse generated assets filtered by pipeline/type/date. Preview images, play videos, read copy/briefs. Download individual or batch.
5. **Brand Manager** — CRUD for brands: products, audiences, brand voice, visual guidelines. GlowVita pre-loaded.
6. **Performance & Insights** — Simulated performance dashboards, winning/losing analysis charts, accumulated insights feeding back into generation.
7. **Deployment Preview** — Mock Meta/TikTok campaign structures, testing matrices, deployment-ready payloads.

**Real-time:** SSE connection for live pipeline progress. Steps light up as they complete, outputs appear in gallery as they're generated.

## API Contract

```
# Auth
POST   /api/auth/validate              → validate API key, return session token

# Pipelines
POST   /api/pipelines/{name}/run       → launch a job
GET    /api/jobs                        → list jobs (filtered, paginated)
GET    /api/jobs/{id}                   → job status + step states
GET    /api/jobs/{id}/events            → SSE stream

# Outputs
GET    /api/outputs                     → list outputs (filtered by pipeline, type, date)
GET    /api/outputs/{id}                → single output with metadata
GET    /api/outputs/{id}/file           → serve the actual file

# Brands
GET    /api/brands                      → list brands
POST   /api/brands                      → create brand
GET    /api/brands/{id}                 → brand details
PUT    /api/brands/{id}                 → update brand

# Performance
POST   /api/performance/simulate       → run simulation on a batch
GET    /api/performance/insights        → accumulated insights
GET    /api/performance/metrics         → dashboard metrics

# Deployment
POST   /api/deployment/preview          → generate mock deployment payload
GET    /api/deployment/matrices          → view testing matrices

# Health
GET    /health                          → {"status": "healthy"}
```

## Authentication

API key-based. A single `ADFORGE_API_KEY` env var on the backend. All API requests require `Authorization: Bearer <key>` header. Frontend stores the key in a cookie after the login page validates it. No user management, no OAuth — just a shared secret to prevent unauthorized API credit usage.

## External Integrations

| Service | Purpose | Env Var | Notes |
|---------|---------|---------|-------|
| OpenAI | All text generation | `OPENAI_API_KEY` | GPT-4o default, structured JSON outputs |
| FAL.ai | Image gen (Flux Pro) + video gen (Kling) | `FAL_KEY` | Async: submit job, poll for result |
| HeyGen | Avatar-based UGC video | `HEYGEN_API_KEY` | Avatar selection, script input, returns video URL |
| ElevenLabs | Text-to-speech voiceovers | `ELEVENLABS_API_KEY` | Stock voices, multiple for variation |

## Seed Data: GlowVita

Fictional DTC premium skincare supplement brand, loaded via database seed migration.

- **Products:** Vitamin C Brightening Serum ($49), Collagen Peptide Complex ($59), Hydration Boost Bundle ($89)
- **Target audiences:** Women 25-40 skincare enthusiasts, Women 40-55 anti-aging, Men 30-45 wellness
- **Brand voice:** Clean, confident, science-backed but approachable. No hype.
- **Offers:** "Buy 2 Get 1 Free", "30-Day Glow Guarantee", "Subscribe & Save 20%"
- **Creative angles:** Before/after transformation, ingredient science, social proof/testimonials, urgency/scarcity, routine integration

## Project Structure

```
ad-forge/
├── backend/
│   ├── Dockerfile
│   ├── pyproject.toml
│   ├── app/
│   │   ├── main.py                  # FastAPI app, health endpoint, CORS, middleware
│   │   ├── config.py                # Settings from env vars
│   │   ├── db.py                    # PostgreSQL connection, async engine
│   │   ├── models/                  # SQLAlchemy models
│   │   ├── routes/                  # API route modules
│   │   ├── engine/                  # Pipeline engine, job workers, event bus
│   │   ├── pipelines/               # The 6 pipeline modules
│   │   ├── integrations/            # API clients (OpenAI, FAL, HeyGen, ElevenLabs)
│   │   └── seed/                    # GlowVita seed data
│   └── tests/
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   ├── src/
│   │   ├── app/                     # Next.js app router pages
│   │   ├── components/              # Shared UI components
│   │   ├── lib/                     # API client, SSE hook, utils
│   │   └── types/                   # TypeScript types matching API contracts
├── docker-compose.yml               # Local dev: backend + frontend + postgres
├── CLAUDE.md                        # Project instructions for agents
└── docs/plans/
```

## Deployment

Single Coolify application at `adforge.kliuiev.com` with path-based routing:
- `/api/*` → FastAPI backend (port 8000)
- Everything else → Next.js frontend (port 3000)

**Backend Dockerfile:** Multi-stage, `python:3.12-slim`, port 8000, `GET /health` returning `{"status": "healthy"}`.
**Frontend Dockerfile:** Multi-stage, `node:22-alpine`, standalone output, port 3000.

Or a single `docker-compose.yml` with both services + nginx for routing, deployed as a Docker Compose resource in Coolify.

**Env vars (Coolify):**
- `DATABASE_URL` — PostgreSQL connection string
- `OPENAI_API_KEY`
- `FAL_KEY`
- `HEYGEN_API_KEY`
- `ELEVENLABS_API_KEY`
- `ADFORGE_API_KEY` — shared secret for auth
- `WORKER_COUNT` — number of concurrent job workers (default: 3)
