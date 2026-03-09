# Verify-App Skill Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create an E2E testing skill (`/verify-app`) that validates AdForge's backend API, frontend UI, and AI pipelines against live or local environments.

**Architecture:** Claude Code skill with SKILL.md instructions + external YAML test case files. Four modes: smoke (quick), full (deep), ai (pipeline execution), improve (self-generate cases). Follows the proven pattern from french_real_estate_warehouses.

**Tech Stack:** Claude Code skills (SKILL.md), YAML test cases, curl (API checks), Playwright MCP (frontend checks)

---

### Task 1: Create Skill Directory Structure

**Files:**
- Create: `.claude/skills/verify-app/cases/.gitkeep`
- Create: `.claude/skills/verify-app/output/.gitkeep`
- Modify: `.gitignore` — allow `.claude/skills/` but ignore `output/history.yaml`

**Step 1: Create directories**

```bash
mkdir -p .claude/skills/verify-app/cases
mkdir -p .claude/skills/verify-app/output
touch .claude/skills/verify-app/cases/.gitkeep
touch .claude/skills/verify-app/output/.gitkeep
```

**Step 2: Update .gitignore**

Check current `.gitignore` for any `.claude` rules. Add rules to:
- Allow `.claude/skills/` to be tracked
- Ignore `.claude/skills/verify-app/output/history.yaml` (mutable runtime data)

If `.gitignore` has a blanket `.claude/` ignore rule, add an exception:
```
# Allow skills to be tracked
!.claude/skills/
.claude/skills/verify-app/output/history.yaml
```

If there's no `.claude/` ignore rule, just add:
```
.claude/skills/verify-app/output/history.yaml
```

**Step 3: Commit**

```bash
git add .claude/skills/ .gitignore
git commit -m "chore: scaffold verify-app skill directory structure"
```

---

### Task 2: Write Backend API Smoke Cases

**Files:**
- Create: `.claude/skills/verify-app/cases/smoke.yaml`

**Step 1: Write smoke.yaml**

All 15 API endpoints need one smoke case each. Auth-protected endpoints need `auth: true` flag so SKILL.md knows to add the Bearer header.

```yaml
# Smoke test cases — one hit per endpoint to verify the app is up and responding.
# Used by: /verify-app smoke (default mode)

- id: health-check
  phase: smoke
  method: GET
  path: /health
  assert:
    status: 200
    json_has_key: status

- id: auth-validate
  phase: smoke
  method: POST
  path: /api/auth/validate
  body: '{"api_key":"{{API_KEY}}"}'
  assert:
    status: 200
    json_has_key: valid

- id: brands-list
  phase: smoke
  method: GET
  path: /api/brands
  auth: true
  assert:
    status: 200
    json_has_key: items

- id: brand-detail
  phase: smoke
  method: GET
  path: /api/brands/{{first_brand_id}}
  auth: true
  depends_on: brands-list
  assert:
    status: 200
    json_has_key: products

- id: jobs-list
  phase: smoke
  method: GET
  path: /api/jobs
  auth: true
  assert:
    status: 200
    json_has_key: items

- id: job-detail
  phase: smoke
  method: GET
  path: /api/jobs/{{first_job_id}}
  auth: true
  depends_on: jobs-list
  assert:
    status: 200
    json_has_key: steps

- id: sse-events
  phase: smoke
  method: GET
  path: /api/jobs/{{first_job_id}}/events
  auth: true
  depends_on: jobs-list
  assert:
    status: 200

- id: outputs-list
  phase: smoke
  method: GET
  path: /api/outputs
  assert:
    status: 200
    json_has_key: items

- id: output-detail
  phase: smoke
  method: GET
  path: /api/outputs/{{first_output_id}}
  depends_on: outputs-list
  assert:
    status: 200
    json_has_key: output_type

- id: deployment-preview
  phase: smoke
  method: POST
  path: /api/deployment/preview
  body: '{"output_ids":[]}'
  assert:
    status: 201

- id: deployment-matrices
  phase: smoke
  method: GET
  path: /api/deployment/matrices
  assert:
    status: 200
    json_has_key: items

- id: performance-metrics
  phase: smoke
  method: GET
  path: /api/performance/metrics?brand_id={{first_brand_id}}
  auth: true
  depends_on: brands-list
  assert:
    status: 200
    json_has_key: items

- id: performance-insights
  phase: smoke
  method: GET
  path: /api/performance/insights?brand_id={{first_brand_id}}
  auth: true
  depends_on: brands-list
  assert:
    status: 200
    json_has_key: items

- id: performance-simulate
  phase: smoke
  method: POST
  path: /api/performance/simulate
  auth: true
  body: '{"brand_id":"{{first_brand_id}}"}'
  depends_on: brands-list
  assert:
    status: 201
    json_has_key: job_id
```

**Key conventions:**
- `{{API_KEY}}` — replaced at runtime with the environment's API key
- `{{first_brand_id}}` — resolved by taking the first item from `brands-list` response
- `{{first_job_id}}` — resolved from `jobs-list` response
- `{{first_output_id}}` — resolved from `outputs-list` response
- `depends_on` — if the dependency case failed, skip this case
- `auth: true` — add `Authorization: Bearer {{API_KEY}}` header

**Step 2: Verify file parses correctly**

```bash
python3 -c "import yaml; cases=yaml.safe_load(open('.claude/skills/verify-app/cases/smoke.yaml')); print(f'{len(cases)} cases loaded')"
```

Expected: `14 cases loaded`

**Step 3: Commit**

```bash
git add .claude/skills/verify-app/cases/smoke.yaml
git commit -m "test(e2e): add backend API smoke cases for verify-app"
```

---

### Task 3: Write Backend API Functional Cases

**Files:**
- Create: `.claude/skills/verify-app/cases/api-functional.yaml`

**Step 1: Write api-functional.yaml**

These test CRUD operations, filters, pagination, and error cases.

```yaml
# Functional API test cases — deeper endpoint validation.
# Used by: /verify-app full, /verify-app ai

- id: brand-create
  phase: functional
  method: POST
  path: /api/brands
  auth: true
  body: '{"name":"Verify Test Brand","voice":"Professional","products":[{"name":"Test Product","description":"A test product"}],"audiences":[{"name":"Test Audience","demographics":"18-35"}]}'
  assert:
    status: 201
    json_has_key: id

- id: brand-update
  phase: functional
  method: PUT
  path: /api/brands/{{created_brand_id}}
  auth: true
  depends_on: brand-create
  body: '{"name":"Verify Test Brand Updated"}'
  assert:
    status: 200
    body_contains: "Updated"

- id: brand-products-nested
  phase: functional
  method: GET
  path: /api/brands/{{created_brand_id}}
  auth: true
  depends_on: brand-create
  assert:
    status: 200
    json_array_not_empty: products

- id: brand-audiences-nested
  phase: functional
  method: GET
  path: /api/brands/{{created_brand_id}}
  auth: true
  depends_on: brand-create
  assert:
    status: 200
    json_array_not_empty: audiences

- id: jobs-filter-status
  phase: functional
  method: GET
  path: /api/jobs?status=completed
  auth: true
  assert:
    status: 200
    json_has_key: items

- id: jobs-filter-pipeline
  phase: functional
  method: GET
  path: /api/jobs?pipeline=briefs
  auth: true
  assert:
    status: 200
    json_has_key: items

- id: jobs-pagination
  phase: functional
  method: GET
  path: /api/jobs?page=1&page_size=2
  auth: true
  assert:
    status: 200
    json_has_key: items

- id: outputs-filter-type
  phase: functional
  method: GET
  path: /api/outputs?output_type=copy_variations
  assert:
    status: 200
    json_has_key: items

- id: outputs-filter-pipeline
  phase: functional
  method: GET
  path: /api/outputs?pipeline_name=briefs
  assert:
    status: 200
    json_has_key: items

- id: outputs-pagination
  phase: functional
  method: GET
  path: /api/outputs?page=1&page_size=2
  assert:
    status: 200
    json_has_key: items

- id: deployment-matrices-filter
  phase: functional
  method: GET
  path: /api/deployment/matrices?page_size=5
  assert:
    status: 200
    json_has_key: items

- id: auth-invalid-key
  phase: functional
  method: POST
  path: /api/auth/validate
  body: '{"api_key":"definitely-not-a-valid-key"}'
  assert:
    status: 200
    body_contains: "false"

- id: brand-not-found
  phase: functional
  method: GET
  path: /api/brands/00000000-0000-0000-0000-000000000000
  auth: true
  assert:
    status: 404

- id: job-not-found
  phase: functional
  method: GET
  path: /api/jobs/00000000-0000-0000-0000-000000000000
  auth: true
  assert:
    status: 404

- id: output-not-found
  phase: functional
  method: GET
  path: /api/outputs/00000000-0000-0000-0000-000000000000
  assert:
    status: 404
```

**Step 2: Verify file parses correctly**

```bash
python3 -c "import yaml; cases=yaml.safe_load(open('.claude/skills/verify-app/cases/api-functional.yaml')); print(f'{len(cases)} cases loaded')"
```

Expected: `15 cases loaded`

**Step 3: Commit**

```bash
git add .claude/skills/verify-app/cases/api-functional.yaml
git commit -m "test(e2e): add backend API functional cases for verify-app"
```

---

### Task 4: Write Frontend Test Cases

**Files:**
- Create: `.claude/skills/verify-app/cases/frontend.yaml`

**Step 1: Write frontend.yaml**

Smoke cases verify pages render. Functional cases test interactions. All authenticated pages require logging in first — the SKILL.md handles this, not individual cases.

```yaml
# Frontend test cases — page rendering and interactive UI checks.
# Smoke cases verify pages load. Functional cases test interactions.
# Used by: /verify-app smoke (smoke phase only), /verify-app full (all phases)

# --- Smoke: pages render ---

- id: login-renders
  phase: smoke
  description: "Navigate to login page, verify AdForge branding and login form"
  steps:
    - navigate to /login
    - wait for page to load
    - take a snapshot
  assert:
    snapshot_contains: ["AdForge", "API Key", "Sign In"]

- id: dashboard-renders
  phase: smoke
  description: "Navigate to dashboard, verify metric cards and status indicators"
  steps:
    - navigate to /dashboard
    - wait for page to load
    - take a snapshot
  assert:
    snapshot_contains: ["Dashboard", "Total Jobs", "Outputs Generated"]

- id: brands-renders
  phase: smoke
  description: "Navigate to brands page, verify header and brand management UI"
  steps:
    - navigate to /brands
    - wait for page to load
    - take a snapshot
  assert:
    snapshot_contains: ["Brands", "New Brand"]

- id: pipelines-renders
  phase: smoke
  description: "Navigate to pipelines page, verify pipeline cards are shown"
  steps:
    - navigate to /pipelines
    - wait for page to load
    - take a snapshot
  assert:
    snapshot_contains: ["Pipelines", "Video UGC", "Ad Copy"]

- id: gallery-renders
  phase: smoke
  description: "Navigate to gallery page, verify filter controls and output grid"
  steps:
    - navigate to /gallery
    - wait for page to load
    - take a snapshot
  assert:
    snapshot_contains: ["Gallery"]

- id: deployment-renders
  phase: smoke
  description: "Navigate to deployment preview page, verify tab structure"
  steps:
    - navigate to /deployment
    - wait for page to load
    - take a snapshot
  assert:
    snapshot_contains: ["Deployment Preview", "Campaign Structure"]

- id: performance-renders
  phase: smoke
  description: "Navigate to performance page, verify KPI cards"
  steps:
    - navigate to /performance
    - wait for page to load
    - take a snapshot
  assert:
    snapshot_contains: ["Performance", "Impressions", "ROAS"]

# --- Functional: interactions ---

- id: nav-sidebar-dashboard
  phase: functional
  description: "Click Dashboard in sidebar, verify navigation"
  steps:
    - navigate to /brands
    - wait for page to load
    - find and click "Dashboard" in the sidebar navigation
    - wait for page to load
    - take a snapshot
  assert:
    snapshot_contains: ["Dashboard", "Total Jobs"]

- id: nav-sidebar-pipelines
  phase: functional
  description: "Click Pipelines in sidebar, verify navigation"
  steps:
    - navigate to /dashboard
    - wait for page to load
    - find and click "Pipelines" in the sidebar navigation
    - wait for page to load
    - take a snapshot
  assert:
    snapshot_contains: ["Pipelines", "Video UGC"]

- id: brands-create-dialog
  phase: functional
  description: "Click New Brand button, verify create dialog opens"
  steps:
    - navigate to /brands
    - wait for page to load
    - find and click the "New Brand" button
    - wait for dialog to appear
    - take a snapshot
  assert:
    snapshot_contains: ["Brand Name", "Brand Voice", "Products", "Audiences"]

- id: pipelines-select-card
  phase: functional
  description: "Click a pipeline card, verify configuration phase loads"
  steps:
    - navigate to /pipelines
    - wait for page to load
    - find and click the "Creative Briefs" pipeline card
    - wait for configuration form to load
    - take a snapshot
  assert:
    snapshot_contains: ["Select a brand", "Launch Pipeline"]

- id: pipelines-brand-dropdown
  phase: functional
  description: "On pipeline config, verify brand dropdown has options"
  steps:
    - navigate to /pipelines
    - wait for page to load
    - click the "Creative Briefs" pipeline card
    - wait for configuration form to load
    - find and click the brand dropdown/select
    - take a snapshot
  assert:
    snapshot_contains: ["GlowVita"]

- id: gallery-filter-controls
  phase: functional
  description: "On gallery page, verify filter dropdowns are interactive"
  steps:
    - navigate to /gallery
    - wait for page to load
    - find the pipeline filter dropdown
    - click it to open options
    - take a snapshot
  assert:
    snapshot_contains: ["All Pipelines"]

- id: dark-mode-toggle
  phase: functional
  description: "Toggle dark mode from sidebar, verify theme changes"
  steps:
    - navigate to /dashboard
    - wait for page to load
    - find and click the theme toggle button in the sidebar
    - wait a moment for theme to apply
    - take a snapshot
  assert:
    snapshot_contains: ["Dashboard"]
```

**Step 2: Verify file parses correctly**

```bash
python3 -c "import yaml; cases=yaml.safe_load(open('.claude/skills/verify-app/cases/frontend.yaml')); smoke=[c for c in cases if c['phase']=='smoke']; func=[c for c in cases if c['phase']=='functional']; print(f'{len(cases)} total: {len(smoke)} smoke, {len(func)} functional')"
```

Expected: `14 total: 7 smoke, 7 functional`

**Step 3: Commit**

```bash
git add .claude/skills/verify-app/cases/frontend.yaml
git commit -m "test(e2e): add frontend smoke and functional cases for verify-app"
```

---

### Task 5: Write AI Pipeline Test Cases

**Files:**
- Create: `.claude/skills/verify-app/cases/ai-pipeline.yaml`

**Step 1: Write ai-pipeline.yaml**

These cases actually trigger AI pipelines and wait for completion. They cost money and take time (120s timeout). Only run in `ai` mode.

```yaml
# AI pipeline test cases — trigger real pipeline execution and verify outputs.
# These call external AI APIs (OpenAI, FAL, etc.) and cost money per run.
# Used by: /verify-app ai only
# Timeout: 120 seconds per case

- id: brief-pipeline-e2e
  phase: ai
  description: "Run the briefs pipeline end-to-end for GlowVita seed brand"
  auth: true
  steps:
    - resolve brand_id for GlowVita from GET /api/brands
    - POST /api/pipelines/briefs/run with body {"brand_id":"{{glowvita_brand_id}}"}
    - capture job_id from response
    - poll GET /api/jobs/{{job_id}} every 5 seconds until status is "completed" or "failed" (max 120s)
    - if completed, verify job has steps with output data
    - if failed, report the error from the job response
  assert:
    job_status: completed
    json_has_key: steps

- id: ad-copy-pipeline-e2e
  phase: ai
  description: "Run the ad_copy pipeline end-to-end for GlowVita seed brand"
  auth: true
  steps:
    - resolve brand_id for GlowVita from GET /api/brands
    - POST /api/pipelines/ad_copy/run with body {"brand_id":"{{glowvita_brand_id}}"}
    - capture job_id from response
    - poll GET /api/jobs/{{job_id}} every 5 seconds until status is "completed" or "failed" (max 120s)
    - if completed, verify outputs were generated via GET /api/outputs?pipeline_name=ad_copy
    - if failed, report the error
  assert:
    job_status: completed

- id: pipeline-sse-streams
  phase: ai
  description: "Verify SSE events fire during pipeline execution"
  auth: true
  steps:
    - resolve brand_id for GlowVita from GET /api/brands
    - POST /api/pipelines/briefs/run with body {"brand_id":"{{glowvita_brand_id}}"}
    - capture job_id from response
    - open SSE connection to /api/jobs/{{job_id}}/events using curl --max-time 30
    - verify at least one event containing "step" appears in the stream
    - if no events within 30s, mark as fail with timeout
  assert:
    has_sse_events: true
```

**Step 2: Verify file parses correctly**

```bash
python3 -c "import yaml; cases=yaml.safe_load(open('.claude/skills/verify-app/cases/ai-pipeline.yaml')); print(f'{len(cases)} cases loaded')"
```

Expected: `3 cases loaded`

**Step 3: Commit**

```bash
git add .claude/skills/verify-app/cases/ai-pipeline.yaml
git commit -m "test(e2e): add AI pipeline cases for verify-app"
```

---

### Task 6: Write SKILL.md

**Files:**
- Create: `.claude/skills/verify-app/SKILL.md`

**Step 1: Write SKILL.md**

This is the core skill definition. Must stay under 500 lines. Model it closely on the french_real_estate_warehouses SKILL.md, adapting for AdForge's domain (auth, 4 modes, AI phase).

The SKILL.md must cover:

1. **Frontmatter** — name, description, argument-hint, metadata
2. **Arguments** — mode parsing (smoke/full/ai/improve), environment parsing (live/local)
3. **Environment Setup** — live URLs (hardcoded), local auto-discovery
4. **Auth Setup** — how to get the API key per environment
5. **Loading Test Cases** — which YAML files per mode, phase filtering
6. **Phase 1: Backend API Checks** — curl execution, template variable resolution, assertion evaluation, `depends_on` handling
7. **Phase 2: Frontend Checks** — Playwright MCP tool loading, login flow for auth, step execution, snapshot assertions
8. **Phase 3: AI Pipeline Checks** — only in ai mode, 120s timeout, polling pattern
9. **Results Output** — exact format
10. **History Append** — YAML entry format
11. **Improve Mode** — codebase scanning, case proposal, user approval, commit
12. **Rules** — timeouts, no retries, browser_snapshot only, etc.

Full content for the SKILL.md:

```markdown
---
name: verify-app
description: >-
  E2E smoke, functional, and AI pipeline tests for AdForge.
  Validates backend API, frontend UI, and AI integrations against live or local.
  Supports smoke (quick), full (deep), ai (pipeline execution), and improve (self-improvement) modes.
argument-hint: "[smoke|full|ai|improve] [live|local]"
metadata:
  author: rolloniel
  version: 1.0.0
  category: testing
  tags: [e2e, smoke-test, functional-test, ai-test, verification]
---

# Verify-App: AdForge E2E Tests

Run e2e tests against the backend API, frontend UI, and optionally AI pipelines. Four modes: smoke (quick health check), full (all functional cases), ai (triggers real AI pipelines — costs money), improve (detect and propose new test cases).

## Arguments

- `/verify-app` — Defaults to `smoke live`
- `/verify-app smoke [live|local]` — Quick: health + one hit per endpoint + pages render
- `/verify-app full [live|local]` — Deep: all smoke + functional cases including frontend interactions
- `/verify-app ai [live|local]` — Everything + AI pipeline execution (slow, costs money)
- `/verify-app improve` — Scan codebase for uncovered functionality, propose new YAML cases

Parse arguments. First arg is mode (`smoke`, `full`, `ai`, or `improve`), second is environment (`live` or `local`). Both optional, defaults `smoke` and `live`. Arguments can appear in any order — if you see `live` or `local` as the first arg, treat it as environment with mode defaulting to `smoke`.

If mode is `improve`, skip to the **Improve Mode** section below.

## Environment Setup

**Live mode:**
```
BACKEND_URL = https://api-adforge.kliuiev.com
FRONTEND_URL = https://adforge.kliuiev.com
```

**Local mode:**
1. Try default ports: `http://localhost:8000` (backend) and `http://localhost:3000` (frontend)
2. Run `curl -s --max-time 2 http://localhost:8000/health` — if it fails, run discovery:
   a. Run `docker compose ps` in the project directory to find container port mappings
   b. If no containers, probe ports 8000-8010 for backend (`/health` endpoint) and 3000-3010 for frontend (HTTP 200)
   c. If nothing found, output "No local services detected" and stop
3. Use discovered URLs for the rest of the run

## Auth Setup

The API key is needed for authenticated endpoints (`auth: true` in YAML cases) and for frontend login.

**Live mode:** Read the API key from the backend's Coolify env vars:
```bash
source ~/projects/personal/.env
curl -s -H "Authorization: Bearer $COOLIFY_API_TOKEN" \
  https://coolify.kliuiev.com/api/v1/applications/e8cwwkoogo0osss804ks8s8w/envs
```
Find the `ADFORGE_API_KEY` value from the response.

**Local mode:** Read from the project's `.env` file or use `dev-key` as fallback.

Store the resolved key as `API_KEY` for use in test case template variables.

## Loading Test Cases

Read the YAML case files from `.claude/skills/verify-app/cases/`:

- **smoke mode:** `cases/smoke.yaml` + `cases/frontend.yaml` — only cases with `phase: smoke`
- **full mode:** `cases/smoke.yaml` + `cases/api-functional.yaml` + `cases/frontend.yaml` — all phases (`smoke` + `functional`)
- **ai mode:** ALL files including `cases/ai-pipeline.yaml` — all phases (`smoke` + `functional` + `ai`)

## Template Variables

Before executing each case, resolve template variables in `path` and `body` fields:

- `{{API_KEY}}` — the resolved API key
- `{{first_brand_id}}` — from the first item in `brands-list` response (`items[0].id`)
- `{{first_job_id}}` — from the first item in `jobs-list` response (`items[0].id`)
- `{{first_output_id}}` — from the first item in `outputs-list` response (`items[0].id`)
- `{{created_brand_id}}` — from the `brand-create` response (`id`)
- `{{glowvita_brand_id}}` — search `brands-list` items for name containing "GlowVita"

Variables are resolved lazily — only when a case needs them. Cache resolved values for reuse.

## Dependency Handling

Cases with `depends_on: <case-id>` are skipped if the dependency case failed. Mark as `[SKIP]` with reason "depends on {case-id}".

## Phase 1: Backend API Checks

For each API test case, run:

```bash
# Get status code
STATUS=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 \
  [-H "Authorization: Bearer ${API_KEY}"] \
  [-H "Content-Type: application/json" -d '${body}'] \
  [-X ${method}] \
  "${BACKEND_URL}${path}")

# Get response body
BODY=$(curl -s --max-time 5 \
  [-H "Authorization: Bearer ${API_KEY}"] \
  [-H "Content-Type: application/json" -d '${body}'] \
  [-X ${method}] \
  "${BACKEND_URL}${path}")
```

Add `-H "Authorization: Bearer ${API_KEY}"` only if `auth: true`.
Add `-H "Content-Type: application/json" -d '${body}'` only if `body` is present.
Add `-X ${method}` for POST/PUT methods.

Evaluate assertions:
- `status: N` — check HTTP status code matches
- `body_contains: "text"` — response body contains the string
- `json_has_key: key` — parse as JSON, check top-level key exists
- `json_array_not_empty: key` — parse as JSON, check key's value is a non-empty array
- `json_has_nested_key: "key.subkey"` — parse as JSON, traverse nested keys

Mark each case as `[PASS]` or `[FAIL]` (with reason).

**Early stopping:** If ALL Phase 1 cases fail, skip Phase 2 entirely. Output "Backend unreachable — skipping frontend checks."

## Phase 2: Frontend Checks

**IMPORTANT:** Load Playwright MCP tools before using them. Use ToolSearch with `select:` prefix:
- `select:mcp__playwright__browser_navigate`
- `select:mcp__playwright__browser_snapshot`
- `select:mcp__playwright__browser_click`
- `select:mcp__playwright__browser_fill_form`
- `select:mcp__playwright__browser_select_option`
- `select:mcp__playwright__browser_press_key`
- `select:mcp__playwright__browser_wait_for`
- `select:mcp__playwright__browser_close`

**Authentication flow (before running authenticated page cases):**
1. Navigate to `${FRONTEND_URL}/login`
2. Fill the API Key input with `${API_KEY}`
3. Click the "Sign In" button
4. Wait for redirect to /dashboard
5. Now the auth cookie is set — proceed with authenticated page checks

**For each frontend test case:**
1. Follow the natural-language `steps` using Playwright MCP tools
2. After completing steps, take a `browser_snapshot`
3. Check `snapshot_contains` — snapshot text must contain ALL listed strings
4. Mark as `[PASS]` or `[FAIL]` (with reason like "snapshot missing 'X'")

**Timeout:** 15 seconds per frontend case. If steps take longer, mark `[FAIL]` with timeout reason.

**When done:** Call `browser_close` to clean up.

## Phase 3: AI Pipeline Checks (ai mode only)

Only runs when mode is `ai`. These cases trigger real AI pipeline execution.

For each AI test case, follow the natural-language `steps`:
1. Resolve any needed IDs (brand_id for GlowVita)
2. Create the job via POST to the pipeline run endpoint
3. Poll job status every 5 seconds up to 120 seconds
4. Evaluate assertions based on final job state

**Timeout:** 120 seconds per AI case.

Mark as:
- `[PASS]` — job completed and assertions pass
- `[FAIL]` — job failed (include error message) or timeout

## Results Output

Output the report in this exact format:

```
VERIFY-APP: AdForge ({environment}, {mode})
═══════════════════════════════════════════════════════

Backend API
  [{STATUS}] {case.id}
  ...

Frontend
  [{STATUS}] {case.id}
  ...

AI Pipelines          ← only shown in ai mode
  [{STATUS}] {case.id}
  ...

Result: {passed}/{total} passed{, {failed} failed}{, {skipped} skipped}
```

Where `{STATUS}` is `PASS`, `FAIL`, or `SKIP`. For `FAIL`, append reason after ` — `. For local mode, add discovered URLs below the header.

## Append to History

After outputting results, append a run entry to `.claude/skills/verify-app/output/history.yaml`:

```yaml
- timestamp: {ISO 8601 now}
  mode: {smoke|full|ai}
  environment: {live|local}
  passed: {N}
  failed: {N}
  skipped: {N}
  failures:
    - id: {case.id}
      error: "{reason}"
```

Create the file if it doesn't exist. Read existing content first if file exists, then write the updated content.

---

## Improve Mode

When invoked with `/verify-app improve`, do NOT run any tests. Analyze the codebase to find uncovered functionality and propose new test cases.

### Step 1: Diff Analysis

Check what has changed recently:

```bash
# If on a feature branch:
git diff main...HEAD --name-only
# If on main:
git log --oneline -10
git diff HEAD~10 --name-only
```

Filter for files in:
- `backend/app/routes/*.py` — backend endpoint changes
- `backend/app/models/*.py` — new models/schemas
- `frontend/src/app/**` — new pages
- `frontend/src/components/**` — new/modified components

For each changed router file, read it and extract new/modified route decorators.

### Step 2: Coverage Scan

Read all existing case files from `.claude/skills/verify-app/cases/`:
- `smoke.yaml`, `api-functional.yaml`, `frontend.yaml`, `ai-pipeline.yaml`

Extract covered paths (API cases) and descriptions (frontend cases).

Scan the codebase for ALL routes:

**Backend:** Read `backend/app/routes/*.py`. Extract every `@router.get(...)`, `@router.post(...)`, `@router.put(...)` path. Cross-reference with existing case paths.

**Frontend:** Read `frontend/src/app/**/page.tsx` for all page routes. Cross-reference with existing frontend case descriptions.

Compute: `uncovered = all_routes - covered_routes`

### Step 3: Propose New Cases

For each uncovered route or component:
1. Generate a YAML test case following existing format
2. Assign `phase: functional` (new cases are always functional)
3. Choose sensible parameters based on endpoint signatures

Present in a table:

```
NEW CASES PROPOSED ({N}):
┌──────────────────────────┬──────────────────────┬────────────────────────┐
│ ID                       │ File                 │ Reason                 │
├──────────────────────────┼──────────────────────┼────────────────────────┤
│ {case-id}                │ {target-yaml-file}   │ {uncovered/new/changed}│
└──────────────────────────┴──────────────────────┴────────────────────────┘
```

Then show full YAML for each proposed case.

### Step 4: User Approval

Ask user to review. They can:
- **Approve all** — append all proposed cases
- **Approve some** — specify which cases by ID
- **Reject with feedback** — modify and re-propose

### Step 5: Commit

```bash
git add .claude/skills/verify-app/cases/
git commit -m "test(e2e): add cases for {brief summary}"
```

---

## Rules

- No retries — report honest current state
- 5-second timeout for curl, 15-second timeout for Playwright, 120-second timeout for AI pipelines
- Use `browser_snapshot` only — no screenshots
- Do NOT modify this SKILL.md in improve mode — only modify case YAML files
- Close the browser when done using `browser_close`
- If an unexpected error occurs, mark that check as `[FAIL]` with the error message and continue
- Clean up test data: if `brand-create` functional case created a test brand, no need to delete — it's harmless
```

**Step 2: Count lines to verify under 500**

```bash
wc -l .claude/skills/verify-app/SKILL.md
```

Expected: under 500 lines

**Step 3: Commit**

```bash
git add .claude/skills/verify-app/SKILL.md
git commit -m "feat: add verify-app skill definition for E2E testing"
```

---

### Task 7: Register Skill and Verify Setup

**Files:**
- Modify: `.claude/settings.json` or equivalent — ensure skill is discoverable

**Step 1: Check if .claude/settings.json exists and how skills are registered**

Look at the french_real_estate_warehouses project's `.claude/` directory for how skills are registered. Check if there's a `settings.json`, `settings.local.json`, or if skills in `.claude/skills/` are auto-discovered.

```bash
ls -la /home/rolloniel/projects/personal/side-projects/french_real_estate_warehouses/.claude/
cat /home/rolloniel/projects/personal/side-projects/french_real_estate_warehouses/.claude/settings.json 2>/dev/null || echo "no settings.json"
cat /home/rolloniel/projects/personal/side-projects/french_real_estate_warehouses/.claude/settings.local.json 2>/dev/null || echo "no settings.local.json"
```

If skills in `.claude/skills/` are auto-discovered (no explicit registration needed), just verify the skill loads. If registration is needed, add the skill to the appropriate config file.

**Step 2: Verify all files are in place**

```bash
find .claude/skills/verify-app/ -type f | sort
```

Expected:
```
.claude/skills/verify-app/SKILL.md
.claude/skills/verify-app/cases/.gitkeep
.claude/skills/verify-app/cases/ai-pipeline.yaml
.claude/skills/verify-app/cases/api-functional.yaml
.claude/skills/verify-app/cases/frontend.yaml
.claude/skills/verify-app/cases/smoke.yaml
.claude/skills/verify-app/output/.gitkeep
```

**Step 3: Verify all YAML files parse correctly**

```bash
python3 -c "
import yaml
files = {
    'smoke': '.claude/skills/verify-app/cases/smoke.yaml',
    'api-functional': '.claude/skills/verify-app/cases/api-functional.yaml',
    'frontend': '.claude/skills/verify-app/cases/frontend.yaml',
    'ai-pipeline': '.claude/skills/verify-app/cases/ai-pipeline.yaml',
}
total = 0
for name, path in files.items():
    cases = yaml.safe_load(open(path))
    print(f'  {name}: {len(cases)} cases')
    total += len(cases)
print(f'Total: {total} cases')
"
```

Expected output:
```
  smoke: 14 cases
  api-functional: 15 cases
  frontend: 14 cases
  ai-pipeline: 3 cases
Total: 46 cases
```

**Step 4: Commit any registration changes**

If registration was needed:
```bash
git add .claude/
git commit -m "chore: register verify-app skill"
```

---

### Task 8: Run Smoke Test Against Live to Validate Skill

**Step 1: Run `/verify-app smoke live`**

Invoke the skill: `/verify-app smoke live`

This validates:
- SKILL.md instructions are followable
- YAML cases parse and execute correctly
- Template variable resolution works
- Auth flow works
- Output format is correct
- History append works

**Step 2: Review results**

Check the output report. If any cases fail due to skill issues (not actual app issues), fix the relevant YAML or SKILL.md.

**Step 3: Review history file was created**

```bash
cat .claude/skills/verify-app/output/history.yaml
```

Should contain one entry with the run results.

**Step 4: Commit any fixes**

If fixes were needed:
```bash
git add .claude/skills/verify-app/
git commit -m "fix: adjust verify-app cases based on live smoke test"
```
