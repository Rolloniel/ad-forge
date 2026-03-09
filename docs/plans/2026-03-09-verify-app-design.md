# Verify-App Skill Design — AdForge

## Overview

E2E testing skill for validating AdForge deployment (backend API + frontend UI + AI pipelines). Ported from the french_real_estate_warehouses verify-app pattern, adapted for AdForge's domain.

## Skill Structure

```
.claude/skills/verify-app/
├── SKILL.md                  # LLM instructions (< 500 lines)
├── cases/
│   ├── smoke.yaml            # Phase: smoke — one hit per endpoint + page renders
│   ├── api-functional.yaml   # Phase: functional — CRUD, filters, pagination
│   ├── frontend.yaml         # Phase: functional — UI interactions
│   └── ai-pipeline.yaml      # Phase: ai — trigger pipeline, verify outputs
└── output/
    ├── .gitkeep
    └── history.yaml           # Append-only run log (gitignored)
```

## Invocation

```
/verify-app                    # Defaults to: smoke live
/verify-app smoke              # Quick health check against live
/verify-app full               # smoke + functional cases against live
/verify-app ai                 # smoke + functional + AI pipeline against live
/verify-app improve            # Scan codebase, propose new cases
/verify-app smoke local        # Against local docker-compose
/verify-app full local
/verify-app ai local
```

Arguments in any order. Environment defaults to `live`, mode defaults to `smoke`.

## Environment URLs

- **Live:** backend `https://api-adforge.kliuiev.com`, frontend `https://adforge.kliuiev.com`
- **Local:** auto-discover `localhost:8000` / `localhost:3000`, fallback to `docker compose ps`

## YAML Schema

### Backend API cases (curl, 5s timeout)

```yaml
- id: health-check
  phase: smoke
  method: GET
  path: /health
  assert:
    status: 200
    json_has_key: status
```

Assertion types:
- `status: N` — HTTP status code
- `body_contains: "text"` — substring match
- `json_has_key: key` — top-level key exists
- `json_array_not_empty: key` — array at key is non-empty
- `json_has_nested_key: "key.subkey"` — nested key exists

### Frontend cases (Playwright MCP, 15s timeout)

```yaml
- id: dashboard-renders
  phase: smoke
  description: "Dashboard page loads with key elements"
  steps:
    - navigate to /dashboard
    - wait for page to load
    - take a snapshot
  assert:
    snapshot_contains: ["Dashboard", "Recent Jobs"]
```

### AI pipeline cases (curl, 120s timeout)

```yaml
- id: brief-pipeline-e2e
  phase: ai
  description: "Run brief generation pipeline end-to-end"
  steps:
    - POST /api/jobs with pipeline config
    - poll job status until completed or failed (max 120s)
    - verify job has output steps
  assert:
    status: 200
    json_has_key: outputs
```

### Phase filtering by mode

- `smoke` → `phase: smoke`
- `full` → `phase: smoke` + `phase: functional`
- `ai` → `phase: smoke` + `phase: functional` + `phase: ai`

## Backend API Test Cases

### Smoke (11 cases)

| ID | Method | Path | Key Assertion |
|---|---|---|---|
| `health-check` | GET | `/health` | status 200, has `status` key |
| `auth-validate` | POST | `/api/auth/validate` | status 200 (with valid API key) |
| `brands-list` | GET | `/api/brands` | status 200, array not empty |
| `brand-detail` | GET | `/api/brands/{id}` | status 200, has `products` key |
| `jobs-list` | GET | `/api/jobs` | status 200 |
| `job-detail` | GET | `/api/jobs/{id}` | status 200, has `steps` key |
| `outputs-list` | GET | `/api/outputs` | status 200 |
| `outputs-by-job` | GET | `/api/outputs?job_id={id}` | status 200 |
| `deployment-preview` | GET | `/api/deployment/preview/{brand_id}` | status 200 |
| `performance-list` | GET | `/api/performance/metrics` | status 200 |
| `sse-events` | GET | `/api/jobs/{id}/events` | status 200, content-type text/event-stream |

Cases needing an existing ID resolve `{id}` by hitting the list endpoint first.

### Functional (13 cases)

| ID | Method | Path | What it tests |
|---|---|---|---|
| `brand-create` | POST | `/api/brands` | Create brand with products + audiences |
| `brand-update` | PUT | `/api/brands/{id}` | Update brand name |
| `brand-products` | GET | `/api/brands/{id}` | Verify products nested in response |
| `brand-audiences` | GET | `/api/brands/{id}` | Verify audiences nested in response |
| `jobs-filter-status` | GET | `/api/jobs?status=completed` | Filter by status |
| `jobs-filter-brand` | GET | `/api/jobs?brand_id={id}` | Filter by brand |
| `outputs-filter-type` | GET | `/api/outputs?type=text` | Filter by output type |
| `outputs-filter-job` | GET | `/api/outputs?job_id={id}` | Filter by job |
| `deployment-matrices` | GET | `/api/deployment/preview/{brand_id}` | Verify matrix structure |
| `auth-invalid-key` | POST | `/api/auth/validate` | Reject bad key (status 401/403) |
| `brand-not-found` | GET | `/api/brands/{bad-uuid}` | 404 response |
| `job-not-found` | GET | `/api/jobs/{bad-uuid}` | 404 response |
| `performance-by-output` | GET | `/api/performance/metrics?output_id={id}` | Filter metrics |

## Frontend Test Cases

### Smoke (6 cases — page renders only)

| ID | Page | Path | snapshot_contains |
|---|---|---|---|
| `login-renders` | Login | `/login` | `["AdForge", "API Key", "Sign In"]` |
| `dashboard-renders` | Dashboard | `/dashboard` | `["Dashboard"]` |
| `brands-renders` | Brands | `/brands` | `["Brand Manager"]` |
| `pipelines-renders` | Pipelines | `/pipelines` | `["Pipelines"]` |
| `gallery-renders` | Gallery | `/gallery` | `["Gallery"]` |
| `deployment-renders` | Deployment | `/deployment` | `["Deployment"]` |

Authenticated pages require setting auth cookie first: navigate to login, fill API key, submit, then proceed.

### Functional (7 cases)

| ID | Description | Key interaction |
|---|---|---|
| `nav-sidebar` | Click each sidebar link, verify page changes | Navigation between all pages |
| `brands-create-dialog` | Click "Add Brand" button, verify dialog opens | Dialog interaction |
| `brands-product-tab` | Navigate to brand detail, verify products tab | Tab switching |
| `pipelines-brand-select` | Open pipelines, verify brand selector present | Dropdown presence |
| `gallery-filter-type` | Open gallery, verify type filter controls | Filter controls present |
| `gallery-preview` | Click an output item, verify preview opens | Preview dialog |
| `dark-mode-toggle` | Toggle dark mode, verify theme changes | Theme switching |

## AI Pipeline Test Cases (3 cases, ai mode only)

| ID | Description | What it does |
|---|---|---|
| `brief-pipeline-e2e` | Run brief generation pipeline | POST create job with brief pipeline for GlowVita seed brand, poll until completed/failed (max 120s, 5s interval), verify outputs exist |
| `ad-copy-pipeline-e2e` | Run ad copy generation pipeline | Same pattern with ad_copy pipeline, verify text outputs generated |
| `pipeline-sse-streams` | Verify SSE events fire during execution | Create job, curl SSE endpoint with --max-time, verify step_started and step_completed events arrive |

Auth: `Authorization: Bearer {api_key}` header. Live reads from environment, local uses `dev-key`.

## Improve Mode

1. **Scan codebase** — parse `backend/app/routes/*.py` for route decorators, `frontend/src/app/**/page.tsx` for pages, compare against existing YAML cases
2. **Analyze recent changes** — `git diff main...HEAD` or `git log -10` for modified routes/pages without test coverage
3. **Propose cases** — generate YAML, present summary table + full YAML for review
4. **User approval** — approve/modify/reject each case, append to appropriate YAML file
5. **Commit** — `test(e2e): add cases for {summary}`

## Execution Flow

1. **Resolve environment** — hardcoded URLs for live, auto-discover for local
2. **Auth setup** — live reads API key from env, local uses `dev-key`
3. **Phase 1: Backend API** — curl cases matching mode's phases, 5s timeout
4. **Early stop** — if ALL backend cases fail, skip frontend ("Backend unreachable")
5. **Phase 2: Frontend** — Playwright MCP, authenticate via login page, 15s timeout, close browser when done
6. **Phase 3: AI pipelines** (ai mode only) — 120s timeout per case
7. **Results summary** — formatted output
8. **History append** — write to `output/history.yaml`

## Output Format

```
VERIFY-APP: AdForge (live, smoke)
═══════════════════════════════════════════════════════

Backend API
  [PASS] health-check
  [PASS] auth-validate
  [FAIL] brands-list — status 500 (expected 200)
  [SKIP] brand-detail — depends on brands-list

Frontend
  [PASS] login-renders
  [PASS] dashboard-renders

Result: 4/6 passed, 1 failed, 1 skipped
```

## History Entry

```yaml
- timestamp: 2026-03-09T14:30:00Z
  mode: smoke
  environment: live
  passed: 4
  failed: 1
  skipped: 1
  failures:
    - id: brands-list
      error: "status 500 (expected 200)"
```
